import streamlit as st
import pandas as pd
import os
import tempfile
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from parallel_processing.prompts import placeholder_system_message, placeholder_prompt
from parallel_processing.main import main as parallel_processing_main
from parallel_processing.csv_to_array import convert_data_to_temp_file
import logging
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


def main():
    initialize_session_state()
    st.title("Consult Prompt Optimization")
    st.write(
        "This toolkit allows for batch processing of MedQA multiple choice questions with customizable prompt inputs for optimization and performance analysis."
    )
    df = load_data("data/315q-medqa.csv")

    # Manual and Auto Selection of MCQs Code (No Changes)

    if st.session_state.get("manual_load_clicked") or st.session_state.get(
        "auto_load_clicked"
    ):
        if st.checkbox("**🖨️ Show my selected MCQs**"):
            st.subheader("❓ Your selected MCQ data:")
            st.write(st.session_state["selected_data"])

        system_message = st.text_area("Your system message:", key="system_message")
        prompt_message = st.text_area("Your prompt:", key="prompt_message")

        if st.button("Initiate batch run"):
            if st.session_state["selected_mcqs_list"]:
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
                        parallel_processing_main(
                            temp_data_file_path,
                            combined_message,
                            os.getenv("MODEL_NAME"),
                            requests_file_path,
                            results_file_path,
                            output_file_path,
                        )
                        st.session_state["batch_initiated"] = True
                    st.success("**🤓 Batch run initiated!**")
                else:
                    st.error("Failed to create temporary data file.")
            else:
                st.error(
                    "No MCQs selected. Please select MCQs before initiating the batch run."
                )

        if st.session_state["batch_initiated"]:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**📊 Batch Progress:**")
                st.progress(st.session_state["progress"])

            with col2:
                st.write("**📜 Log Output:**")
                st.text("\n".join(st.session_state["log_messages"]))

            if st.session_state.get("batch_status", "") == "Completed":
                if st.checkbox("View Results Dataframe"):
                    st.dataframe(pd.read_csv(output_file_path))

                with open(output_file_path, "rb") as file:
                    st.download_button(
                        label="💻 Download Results as CSV",
                        data=file,
                        file_name="batch_results.csv",
                        mime="text/csv",
                    )


if __name__ == "__main__":
    main()
