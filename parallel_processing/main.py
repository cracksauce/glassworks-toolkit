# main.py
import asyncio
import os
from api_request_parallel_processor import process_api_requests_from_file
from generate_requests import generate_chat_completion_requests
from save_generated_data_to_csv import save_generated_data_to_csv
from csv_to_array import convert_csv_to_array
from parallel_processing.prompts import placeholder_prompt
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(filename='parallel_processing.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_data(requests_file_path, results_file_path, output_file_path, data, prompt, model_name):
    try:
        # Generate chat completion requests
        generate_chat_completion_requests(request_file_path, data, model_name=model_name)

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
        save_generated_data_to_csv(result_file_path, output_file_path)
        logging.info(f"Generation of API requests completed successfully for: {request_file_path}")
    except Exception as e:
        logging.error(f"An error occurred during request generation: {e}")
        raise

def main(data, prompt, model_name, data_file_path, requests_file_path, results_file_path, output_file_path):
    asyncio.run(process_data(requests_file_path, results_file_path, output_file_path, data, prompt, model_name))

if __name__ == "__main__":
    pass