import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load additional configuration from environment variables
frequency_penalty = float(os.getenv("FREQUENCY_PENALTY", "0"))
max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
presence_penalty = float(os.getenv("PRESENCE_PENALTY", "0"))
temperature = float(os.getenv("TEMPERATURE", "0"))
top_p = float(os.getenv("TOP_P", "0"))
n = int(os.getenv("N", "1"))

def generate_chat_completion_requests(requests_file_path, data, system_message, user_prompt, model_name):
    # Ensure the 'requests_file_path' is the temporary file path passed from the Streamlit app
    with open(requests_file_path, "w") as f:
        for item in data:
            # Concatenate the system message and user prompt with the item data
            user_message = f"{user_prompt}\n\nConsult Question:\n'{item}'"

            # Construct the request body with additional parameters from .env
            request_body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                "frequency_penalty": frequency_penalty,
                "max_tokens": max_tokens,
                "presence_penalty": presence_penalty,
                "temperature": temperature,
                "top_p": top_p,
                "n": n,
                # Additional parameters can be included here if needed
            }

            # Write the request body to the temporary .jsonl file
            json_string = json.dumps(request_body)
            f.write(json_string + "\n")
