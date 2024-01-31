import streamlit as st
import pandas as pd
import asyncio
import os
import tempfile
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from parallel_processing.prompts import placeholder_system_message, placeholder_prompt
from parallel_processing.api_request_parallel_processor import (
    process_api_requests_from_file,
)
from parallel_processing.generate_requests import generate_chat_completion_requests
from parallel_processing.save_generated_data_to_csv import save_generated_data_to_csv
from parallel_processing.main import main as parallel_processing_main
from parallel_processing.main import process_data
from parallel_processing.csv_to_array import convert_data_to_temp_file
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    filename="app_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    keys_with_defaults = {
        "manual_load_clicked": False,
        "auto_load_clicked": False,
        "batch_initiated": False,
        "selected_data": None,
        "manual_selection": False,
        "auto_selection": False,
        "selected_rows": [],
        "batch_status": "Not started",
        "progress": 0,
        "log_messages": [],
        "selected_mcqs_list": [],
        "formatted_system_message": "",
        "formatted_prompt": "",
        "batch_run_is_complete": False,
    }
    for key, default in keys_with_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def create_temp_file(prefix, suffix):
    """Create a temporary file and return its path."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=suffix)
    return temp_file.name


# Initialize file paths with temporary files
data_file_path = create_temp_file("data_", ".csv")  # Placeholder, adjust as needed
requests_file_path = create_temp_file("requests_", ".jsonl")
results_file_path = create_temp_file("results_", ".csv")
output_file_path = create_temp_file("output_", ".csv")


def load_data(filename):
    """Load the CSV file into a pandas DataFrame."""
    return pd.read_csv(filename)


# Function to update the session state with selected rows
def update_selected_rows(selected_rows_data):
    st.session_state.selected_rows = selected_rows_data


# Function to normalize the dataframe structure
def normalize_df(df):
    try:
        # Check if the 'full_qa_with_qid' is in column B (manual selection)
        if "full_qa_with_qid" in df.columns[1]:
            # Move 'full_qa_with_qid' to column A
            df = df[
                ["full_qa_with_qid"] + [col for col in df if col != "full_qa_with_qid"]
            ]
        return df
    except Exception as e:
        logging.error(f"Error in normalizing DataFrame: {e}")
        st.error(f"An error occurred: {e}")


# This function should update the state when manual questions are loaded
def manual_load():
    st.session_state["manual_load_clicked"] = True
    st.session_state["auto_load_clicked"] = False


# This function should update the state when auto questions are loaded
def auto_load():
    st.session_state["auto_load_clicked"] = True
    st.session_state["manual_load_clicked"] = False


# Function to split the dataframe into chunks with specified ranges
def get_question_ranges(df_length):
    ranges = [
        (1, 50, "Questions 1 to 50 (n=50)"),
        (51, 100, "Questions 51-100 (n=50)"),
        (101, 150, "Questions 101-150 (n=50)"),
        (151, 200, "Questions 151-200 (n=50)"),
        (201, 240, "Questions 201-240 (n=40)"),
        (241, 270, "Questions 241-270 (n=30)"),
        (271, 290, "Questions 271-290 (n=20)"),
        (291, 305, "Questions 291-305 (n=15)"),
        (306, 315, "Questions 306-315 (n=10)"),
    ]
    return [
        (start, end, label) for start, end, label in ranges if start < df_length + 1
    ]


# Load the CSV file into a pandas DataFrame
@st.cache_data
def load_data(filename):
    data = pd.read_csv(filename)
    return data


# Define the path to your CSV file
csv_file_path = "data/315q-medqa.csv"


async def process_data(
    requests_file_path,
    output_file_path,
    temp_data_file_path,
    system_message,
    user_prompt,
    model_name,
):
    pass


def main():
    initialize_session_state()
    st.title("Consult Prompt Optimization")
    st.write(
        "This toolkit allows for batch processing of MedQA multiple choice questions with customizable prompt inputs for optimization and performance analysis."
    )
    df = load_data("data/315q-medqa.csv")

    # Initialize the variable at the start of your main function
    selected_mcqs_list = []

    # Manual Selection of MCQs
    st.subheader("Manual Select MCQs")
    if st.checkbox("Show spreadsheet of 315-question subset of MedQA"):
        # Create an interactive table using AgGrid for manual selection
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection(
            "multiple", use_checkbox=True
        )  # Enable checkbox for multiple selection
        grid_options = gb.build()

        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            height=300,
            width="100%",
            data_return_mode=DataReturnMode.AS_INPUT,
        )
        # Update the selected rows in the session state
        if grid_response["selected_rows"]:
            update_selected_rows(grid_response["selected_rows"])

        # Check if any rows are selected
        if grid_response["selected_rows"]:
            # Update session state with the selected data
            st.session_state["selected_data"] = pd.DataFrame(
                grid_response["selected_rows"]
            )
            st.session_state[
                "manual_selection"
            ] = True  # Indicate manual selection is done
            st.session_state["auto_selection"] = False

    # Initialize indices
    start_index = None
    end_index = None

    # Button to load manually selected questions
    if st.button("Load Manually Selected Questions"):
        manual_load()
        if st.session_state["manual_selection"]:
            st.session_state["manual_load_clicked"] = True
            st.write("**😎 Your manual selection has been processed**")
            normalized_df = normalize_df(st.session_state["selected_data"])
            st.session_state["selected_mcqs_list"] = normalized_df[
                "full_qa_with_qid"
            ].tolist()

    # Auto Selection of MCQs
    st.subheader("Auto Select MCQs")
    question_ranges = get_question_ranges(len(df))
    option_labels = [label for _, _, label in question_ranges]
    selected_label = st.selectbox("Select question range", options=option_labels)
    selected_range = next(
        (start, end) for start, end, label in question_ranges if label == selected_label
    )

    # Button to load auto-selected questions
    if st.button("Load Auto Selected Questions"):
        auto_load()
        start_index = selected_range[0] - 1
        end_index = selected_range[1]
        if start_index is not None and end_index is not None:
            st.session_state["auto_selection"] = True
            st.session_state["auto_load_clicked"] = True  # Ensure this is set here
            st.session_state["selected_data"] = df.iloc[start_index:end_index]
            st.write("**😎 Your auto selection has been processed**")
            # Populate the selected_mcqs_list here after auto selection is processed
            normalized_df = normalize_df(st.session_state["selected_data"])
            st.session_state["selected_mcqs_list"] = normalized_df[
                "full_qa_with_qid"
            ].tolist()

    if st.session_state.get("manual_load_clicked") or st.session_state.get(
        "auto_load_clicked"
    ):
        if st.checkbox("**🖨️ Show my selected MCQs**"):
            st.subheader("❓ Your selected MCQ data:")
            st.write(st.session_state["selected_data"])

        # The system message and prompt input should only be available after questions are loaded.
        system_message = st.text_area("Your system message:", key="system_message")
        prompt_message = st.text_area("Your prompt:", key="prompt_message")

        # The 'Initiate batch run' button should only be available after system message and prompt have been entered.
        if system_message and prompt_message:
            # Update session state with the formatted messages
            st.session_state[
                "formatted_system_message"
            ] = placeholder_system_message.format(user_system_message=system_message)
            st.session_state["formatted_prompt"] = placeholder_prompt.format(
                user_prompt=prompt_message
            )

        # The portion where you initiate batch processing
        if st.button("Initiate batch run"):
            if st.session_state.get("selected_mcqs_list"):
                temp_data_file_path = convert_data_to_temp_file(
                    st.session_state["selected_mcqs_list"]
                )
                if temp_data_file_path:
                    combined_message = (
                        st.session_state["formatted_system_message"]
                        + "\n"
                        + st.session_state["formatted_prompt"]
                    )
                    with st.spinner("Processing, please wait..."):
                        # Create temp files for request and results
                        with tempfile.NamedTemporaryFile(
                            delete=False, mode="w+", suffix=".jsonl"
                        ) as requests_temp_file, tempfile.NamedTemporaryFile(
                            delete=False, mode="w+", suffix=".csv"
                        ) as results_temp_file, tempfile.NamedTemporaryFile(
                            delete=False, mode="w+", suffix=".csv"
                        ) as output_temp_file:
                            requests_file_path = requests_temp_file.name
                            results_file_path = results_temp_file.name
                            output_file_path = output_temp_file.name

                            # Adapted to call async code in a sync context correctly
                            process_data(
                                requests_file_path,
                                output_file_path,
                                temp_data_file_path,
                                st.session_state["formatted_system_message"],
                                st.session_state["formatted_prompt"],
                                os.getenv("MODEL_NAME"),
                            )

                        st.session_state["batch_initiated"] = True
                    st.success("**🥳 Batch run completed!**")
                else:
                    st.error("Failed to create temporary data file.")
            else:
                st.error(
                    "No MCQs selected. Please select MCQs before initiating the batch run."
                )

            if st.session_state.get("batch_initiated"):
                # Display results dataframe and download button if the batch run was initiated
                try:
                    # Use st.cache to only reload the data when needed
                    @st.cache
                    def load_results(file_path):
                        return pd.read_csv(file_path)

                    results_df = load_results(output_file_path)

                    if st.checkbox("View Results Dataframe"):
                        st.dataframe(results_df)

                    with open(output_file_path, "rb") as file:
                        st.download_button(
                            label="💻 Download Results as CSV",
                            data=file,
                            file_name="batch_results.csv",
                            mime="text/csv",
                        )
                except Exception as e:
                    st.error(f"An error occurred while loading the results: {str(e)}")


if __name__ == "__main__":
    main()
