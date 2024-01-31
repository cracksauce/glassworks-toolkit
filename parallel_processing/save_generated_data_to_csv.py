# save_generated_data_to_csv.py
import csv
import json
import tempfile


def save_generated_data_to_csv(input_filename):
    responses = []

    # Read the input file and collect responses
    try:
        with open(input_filename, "r", encoding="utf-8") as file:
            for line in file:
                data = json.loads(line)
                responses.append(data)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

    # Create a temporary CSV file for writing
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".csv"
    ) as temp_output_file:
        output_filename = temp_output_file.name
        csv_writer = csv.writer(temp_output_file)

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
                output_answer = response[1]["choices"][0]["message"].get("content", "")
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
    return output_filename


if __name__ == "__main__":
    # Example of how this function would be called
    input_filename = "path_to_your_input.jsonl"
    output_csv_path = save_generated_data_to_csv(input_filename)
    if output_csv_path:
        print(f"Generated CSV available at: {output_csv_path}")
    else:
        print("Failed to generate CSV.")
