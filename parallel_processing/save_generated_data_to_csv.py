# save_generated_data_to_csv.py
import csv
import json
import os
from dotenv import load_dotenv

load_dotenv()


def save_generated_data_to_csv(input_filename, output_filename):
    responses = []

    # Read the input file and collect responses
    try:
        with open(input_filename, "r", encoding="utf-8") as file:
            for line in file:
                data = json.loads(line)
                responses.append(data)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    # Create a CSV file for writing
    try:
        with open(output_filename, "w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)

            # Write the header row
            csv_writer.writerow(
                [
                    "Model",
                    "Input Prompt",
                    "Output Answer",
                    "Prompt Tokens",
                    "Completion Tokens",
                ]
            )

            # Iterate through the responses and write data to the CSV
            for response in responses:
                try:
                    # Extract the required data from the response
                    model = response[0].get("model", "")
                    system_message = response[0]["messages"][0].get("content", "")
                    user_message = response[0]["messages"][1].get("content", "")
                    input_prompt = f"System message: {system_message}\n\n{user_message}"
                    output_answer = response[1]["choices"][0]["message"].get(
                        "content", ""
                    )
                    prompt_tokens = response[1]["usage"].get("prompt_tokens", 0)
                    completion_tokens = response[1]["usage"].get("completion_tokens", 0)

                    # Write data to the CSV file
                    csv_writer.writerow(
                        [
                            model,
                            input_prompt,
                            output_answer,
                            prompt_tokens,
                            completion_tokens,
                        ]
                    )
                except Exception as e:
                    print(f"Error processing response: {e}")
                    print(f"Problematic response: {response}")

        print(f"CSV file created successfully at {output_filename}.")
    except Exception as e:
        print(f"Error writing data to CSV file: {e}")


if __name__ == "__main__":
    input_filename = os.getenv(
        "REQUESTS_FILE_PATH", "requests_to_chat_completion.jsonl"
    )
    output_filename = os.getenv("OUTPUT_FILE_PATH", "output.csv")
    save_generated_data_to_csv(input_filename, output_filename)
