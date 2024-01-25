# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st

# Define main app logic
def main():
    st.set_page_config(page_title="Prompt Optimization", page_icon="🔬")

    # Sidebar navigation
with st.sidebar:
    st.sidebar.success("Select an application above.")

def run():
    st.title("Glass Health Prompt Optimization")
    
    st.markdown(
        """### Project Overview

The Streamlit app serves as a platform for:

- Batch running Consult prompts to GPT-4 Turbo to assess performance on Clinical Knowledge Multiple Choice Questions (MCQs) from MedQA and NBME self-assessments and practice shelf exams.
- Dynamic input handling for customizable inputs and prompts.
- Option to download Outputs and analyze on the shared Google Sheet.
### Project Roadmap

- [ ]  Expand datasets for DDx, A&P, and clinical reference question testing
- [ ]  Implement automated evaluation tools for metrics
- [ ]  Develop real-time visualization of evaluation processes.
- [ ]  Automate result exporting to separately hosted database for easy process logging."""
    )

if __name__ == "__main__":
    run()
