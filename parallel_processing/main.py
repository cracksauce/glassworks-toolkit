import asyncio
import os
import csv 
from parallel_processing.api_request_parallel_processor import process_api_requests_from_file
from parallel_processing.generate_requests import generate_chat_completion_requests
from parallel_processing.save_generated_data_to_csv import save_generated_data_to_csv
from parallel_processing.csv_to_array import convert_data_to_temp_file
from parallel_processing.prompts import placeholder_prompt
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(filename='parallel_processing.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_mcqs_from_temp_file(temp_file_path):
    mcqs = []
    try:
        with open(temp_file_path, 'r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                mcqs.append(row[0])
        return mcqs
    except Exception as e:
        logging.error(f"Error reading MCQs from temporary file: {e}")
        return None

async def process_data(requests_file_path, results_file_path, output_file_path, temp_data_file_path, system_message, user_prompt, model_name):
    try:
        # Read MCQs from the temporary CSV file
        data = read_mcqs_from_temp_file(temp_data_file_path)
        if not data:
            raise Exception("Failed to read MCQs from temporary file.")
        
        # Generate chat completion requests
        generate_chat_completion_requests(requests_file_path, data, system_message, user_prompt, model_name=model_name)

        # Process api requests
        await process_api_requests_from_file(
            requests_filepath=requests_file_path,
            save_filepath=results_file_path,
            request_url=os.getenv("API_REQUEST_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            max_requests_per_minute=float(os.getenv("MAX_REQUESTS_PER_MINUTE")),
            max_tokens_per_minute=float(os.getenv("MAX_TOKENS_PER_MINUTE")),
            token_encoding_name=os.getenv("TOKEN_ENCODING_NAME"),
            max_attempts=int(os.getenv("MAX_ATTEMPTS")),
            logging_level=int(os.getenv("LOGGING_LEVEL")),
        )
        # Save generated data to csv
        save_generated_data_to_csv(results_file_path, output_file_path)
        logging.info(f"Generation of API requests completed successfully for: {requests_file_path}")
    except Exception as e:
        logging.error(f"An error occurred during request generation: {e}")
        raise

def main(temp_data_file_path, combined_message, model_name, requests_file_path, results_file_path, output_file_path):
    system_message, user_prompt = combined_message.split('\n', 1)
    asyncio.run(process_data(requests_file_path, results_file_path, output_file_path, temp_data_file_path, system_message, user_prompt, model_name))

if __name__ == "__main__":
    pass