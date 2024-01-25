import streamlit as st
import pandas as pd
import json
import tempfile
import os
import queue
import threading
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from parallel_processing.prompts import placeholder_system_message, placeholder_prompt
from parallel_processing.generate_requests import generate_chat_completion_requests
from parallel_processing.main import main as parallel_processing_main
from parallel_processing.main import process_data
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize logger for error tracking
logging.basicConfig(filename='app_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize a Queue to manage the batch runs
batch_run_queue = queue.Queue()

# Initialize session state variables for UI elements and data selections
if 'manual_load_clicked' not in st.session_state:
    st.session_state['manual_load_clicked'] = False
if 'auto_load_clicked' not in st.session_state:
    st.session_state['auto_load_clicked'] = False
if 'selected_data' not in st.session_state:
    st.session_state['selected_data'] = None
if 'manual_selection' not in st.session_state:
    st.session_state['manual_selection'] = False
if 'auto_selection' not in st.session_state:
    st.session_state['auto_selection'] = False
if 'selected_rows' not in st.session_state:
    st.session_state.selected_rows = []
if 'batch_status' not in st.session_state:
    st.session_state['batch_status'] = 'Not started'
if 'progress' not in st.session_state:
    st.session_state['progress'] = 0
if 'log_messages' not in st.session_state:
    st.session_state['log_messages'] = []

# Function to update the session state with selected rows
def update_selected_rows(selected_rows_data):
    st.session_state.selected_rows = selected_rows_data

# Function to normalize the dataframe structure
def normalize_df(df):
    try:
        # Check if the 'full_qa_with_qid' is in column B (manual selection)
        if 'full_qa_with_qid' in df.columns[1]:
            # Move 'full_qa_with_qid' to column A
            df = df[['full_qa_with_qid'] + [col for col in df if col != 'full_qa_with_qid']]
        return df
    except Exception as e:
        logging.error(f"Error in normalizing DataFrame: {e}")
        st.error(f"An error occurred: {e}")
        
def process_batch_runs():
    while True:
        batch_run = batch_run_queue.get()
        if batch_run is None:
            # If we get None, it means we are signaling the end of the queue
            break
        
        try:
            # Now we're sure batch_run is not None, we can unpack it
            selected_mcqs_list, formatted_system_message, formatted_prompt = batch_run
            
            # Using tempfile to manage temporary storage of data, requests, and results
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.py') as data_file, \
                tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.jsonl') as request_file, \
                tempfile.NamedTemporaryFile(delete=False, mode='r', suffix='.jsonl') as result_file, \
                tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.csv') as output_file:

                data_file.write(f"data = {selected_mcqs_list}")
                data_file_path = data_file.name
                requests_file_path = request_file.name
                results_file_path = result_file.name
                output_file_path = output_file.name
            
            # Initialize progress
            total_tasks = len(selected_mcqs_list)
            completed_tasks = 0
                
            for task in selected_mcqs_list:
                # Simulate task processing (e.g., calling an API, processing data)
                # ...
                # Update task progress
                completed_tasks += 1
                progress = int((completed_tasks / total_tasks) * 100)
                st.session_state['progress'] = progress
                st.session_state['progress_bar'].progress(progress)
                
                # Here, call the main processing function for each selected MCQ batch
                parallel_processing_main.main(
                    data=task,
                    prompt=formatted_system_message + formatted_prompt,
                    model_name=os.getenv('MODEL_NAME'),
                    data_file_path=data_file_path,
                    requests_file_path=requests_file_path,
                    results_file_path=results_file_path,
                    output_file_path=output_file_path
                )
                
                # Update log messages periodically or upon certain events
                log_message = f"Completed task {completed_tasks} of {total_tasks}"
                st.session_state['log_messages'].append(log_message)
                st.session_state['log_output'].text('\n'.join(st.session_state['log_messages']))
            
                # Update completion message and status
                completion_message = f"Batch run completed. Results saved."
                st.session_state['log_messages'].append(completion_message)
                st.session_state['log_output'].text('\n'.join(st.session_state['log_messages']))
                st.session_state['batch_status'] = 'Completed'
                        
        except Exception as e:
            error_message = f"Error occurred: {e}"
            st.session_state['log_messages'].append(error_message)
            st.session_state['log_output'].text('\n'.join(st.session_state['log_messages']))
            logging.error(error_message)
            st.session_state['batch_status'] = 'Failed'

        finally:
            batch_run_queue.task_done()

    # Indicate the batch run is complete
    if batch_run_is_complete:
        selected_mcqs_list, formatted_system_message, formatted_prompt = batch_run
        
        # Convert .jsonl results to DataFrame and save as .csv
        results_df = jsonl_to_dataframe(results_file_path)
        results_df.to_csv(output_file_path, index=False)
        st.session_state['batch_status'] = '🥳 Batch run completed! Saving results...'
        st.success('Batch run completed and results are saved!')
            
# Define button functionality to update session state
def manual_load():
    st.session_state['manual_load_clicked'] = True
    st.session_state['manual_selection'] = True
    st.session_state['auto_selection'] = False

def auto_load():
    st.session_state['auto_load_clicked'] = True
    st.session_state['auto_selection'] = True
    st.session_state['manual_selection'] = False

# Function to split the dataframe into chunks with specified ranges
def get_question_ranges(df_length):
    ranges = [
        (1, 50, 'Questions 1 to 50 (n=50)'),
        (51, 100, 'Questions 51-100 (n=50)'),
        (101, 150, 'Questions 101-150 (n=50)'),
        (151, 200, 'Questions 151-200 (n=50)'),
        (201, 240, 'Questions 201-240 (n=40)'),
        (241, 270, 'Questions 241-270 (n=30)'),
        (271, 290, 'Questions 271-290 (n=20)'),
        (291, 305, 'Questions 291-305 (n=15)'),
        (306, 315, 'Questions 306-315 (n=10)'),
    ]
    return [(start, end, label) for start, end, label in ranges if start < df_length + 1]

# Load the CSV file into a pandas DataFrame
@st.cache_data
def load_data(filename):
    data = pd.read_csv(filename)
    return data

# Define the path to your CSV file
csv_file_path = 'data/315q-medqa.csv'  

# The main function where we will build the app
def main():
    try:
        st.title("Consult Prompt Optimization")
        st.write("This toolkit allows for batch processing of MedQA multiple choice questions with customizable prompt inputs for optimization and performance analysis.")
        
        # Load the data
        df = load_data(csv_file_path)
        
        # Manual Selection of MCQs
        st.subheader("Manual Select MCQs")
        if st.checkbox('Show spreadsheet of 315-question subset of MedQA'):
            # Create an interactive table using AgGrid for manual selection
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection('multiple', use_checkbox=True)  # Enable checkbox for multiple selection
            grid_options = gb.build()

            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                height=300,
                width='100%',
                data_return_mode=DataReturnMode.AS_INPUT,
            )
            # Update the selected rows in the session state
            if grid_response['selected_rows']:
                update_selected_rows(grid_response['selected_rows'])

            # Check if any rows are selected
            if grid_response['selected_rows']:
                # Update session state with the selected data
                st.session_state['selected_data'] = pd.DataFrame(grid_response['selected_rows'])
                st.session_state['manual_selection'] = True  # Indicate manual selection is done
                st.session_state['auto_selection'] = False

        # Button to load manually selected questions
        if st.button('Load Manually Selected Questions'):
            manual_load()
            if st.session_state['manual_selection']:
                st.write("**😎 Your manual selection has been processed**")
            else:
                st.warning("**🙏🏼 Please select questions from the spreadsheet**")

        # Initialize indices
        start_index = None
        end_index = None
            
        # Auto Selection of MCQs
        st.subheader("Auto Select MCQs")
        question_ranges = get_question_ranges(len(df))
        option_labels = [label for _, _, label in question_ranges]
        selected_label = st.selectbox("Select question range", options=option_labels)
        selected_range = next((start, end) for start, end, label in question_ranges if label == selected_label)

        # Initialize indices outside the button click event
        start_index = None
        end_index = None

        # Button to load auto-selected questions
        if st.button('Load Auto Selected Questions'):
            auto_load()
            start_index = selected_range[0] - 1
            end_index = selected_range[1]
            if start_index is not None and end_index is not None:
                st.session_state['auto_selection'] = True
                st.session_state['selected_data'] = df.iloc[start_index:end_index]
                st.write("**😎 Your auto selection has been processed**")
            else:
                st.session_state['auto_selection'] = False
                st.warning("**🙏🏼 Please select a question range**")

        # Check if either manual or auto load has been clicked before showing the checkbox
        if st.session_state['manual_load_clicked'] or st.session_state['auto_load_clicked']:
            if st.checkbox('**🖨️ Show my selected MCQs**'):
                if st.session_state['manual_load_clicked']:
                    st.subheader("❓ Your manually selected MCQ data:")
                    st.write(st.session_state['selected_data'])
                elif st.session_state['auto_load_clicked']:
                    st.subheader("❓ Your auto selected MCQ data:")
                    st.write(st.session_state['selected_data'])

                # Text input for system message and prompt
                system_message = st.text_area("Your system message:")
                prompt_message = st.text_area("Your prompt:")

                # Formatting system message and prompt
                formatted_system_message = placeholder_system_message.format(user_system_message=system_message)
                formatted_prompt = placeholder_prompt.format(user_prompt=prompt_message)

                if st.button('Initiate batch run'):
                    normalized_df = normalize_df(st.session_state['selected_data'])
                    selected_mcqs_list = normalized_df['full_qa_with_qid'].tolist()
                        # UI for progress and logs
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**📊 Batch Progress:**")
                        progress_bar = st.progress(st.session_state['progress'])
                        
                    with col2:
                        st.write("**📜 Log Output:**")
                        log_output = st.empty()
                        
                    # Save references to progress bar and log output in session state
                    st.session_state['progress_bar'] = progress_bar
                    st.session_state['log_output'] = log_output

                    # Add the batch run data to the queue
                    batch_run_data = (selected_mcqs_list, formatted_system_message, formatted_prompt)
                    batch_run_queue.put(batch_run_data)

                    # Start a new thread to process batch runs
                    threading.Thread(target=process_batch_runs, daemon=True).start()

                    # Start another thread to update the UI
                    threading.Thread(target=update_ui, daemon=True).start()

                    # Initiate batch processing using the imported function
                    threading.Thread(
                        target=process_data,
                        args=(requests_file_path, results_file_path, output_file_path, selected_mcqs_list, os.getenv('MODEL_NAME'), os.getenv('OPENAI_API_KEY')),
                        daemon=True
                    ).start()
                    st.write("**🤓 Batch run initiated!**")
                    
        if st.session_state['batch_status'] == 'Completed':
            with open(output_file_path, "rb") as file:
                st.download_button(
                label="💻 Download Results as CSV",
                data=file,
                file_name="batch_results.csv",
                mime="text/csv",
            )         
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()