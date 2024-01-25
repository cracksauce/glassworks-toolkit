import json
import os
from parallel_processing.prompts import placeholder_prompt, placeholder_system_message
from dotenv import load_dotenv

load_dotenv()

# Load additional configuration from environment variables
frequency_penalty = float(os.getenv("FREQUENCY_PENALTY", "0"))
max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
presence_penalty = float(os.getenv("PRESENCE_PENALTY", "0"))
temperature = float(os.getenv("TEMPERATURE", "0"))
top_p = float(os.getenv("TOP_P", "0"))
n = int(os.getenv("N", "1"))

def generate_chat_completion_requests(
    filename,
    data,
    system_message,
    user_prompt,
    model_name=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
):
    with open(filename, "w") as f:
        for x in data:
            # Concatenate metaprompt and mcq data for each request
            user_message = f"{user_prompt}\n'{x}'"

            # Construct the request body with additional parameters
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
                "n": n
                # Add other parameters as needed
            }

            # Write the request body to the JSONL file
            json_string = json.dumps(request_body)
            f.write(json_string + "\n")
