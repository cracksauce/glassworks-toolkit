import aiohttp  # for making API calls concurrently
import asyncio  # for running API calls concurrently
import json  # for saving results to a jsonl file
import logging  # for logging rate limit warnings and other messages
import os  # for reading API key
import re  # for matching endpoint from request URL
import tiktoken  # for counting tokens
import time  # for sleeping after rate limit is hit
import tempfile
from dataclasses import (
    dataclass,
    field,
)  # for storing API inputs, outputs, and metadata
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Fetching configuration from environment variables
request_url = os.getenv("API_REQUEST_URL", "https://api.openai.com/v1/chat/completions")
api_key = os.getenv("OPENAI_API_KEY")
max_requests_per_minute = float(os.getenv("MAX_REQUESTS_PER_MINUTE", "500"))
max_tokens_per_minute = float(os.getenv("MAX_TOKENS_PER_MINUTE", "60000"))
token_encoding_name = os.getenv("TOKEN_ENCODING_NAME", "cl100k_base")
max_attempts = int(os.getenv("MAX_ATTEMPTS", "5"))
logging_level = int(os.getenv("LOGGING_LEVEL", "20"))

# Constants
seconds_to_pause_after_rate_limit_error = 15
seconds_to_sleep_each_loop = (
    0.001  # 1 ms limits max throughput to 1,000 requests per second
)
# Configure logging
logging.basicConfig(
    filename="parallel_processing.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def process_api_requests_from_file(
    requests_filepath,  # Passed as a parameter
    request_url,
    api_key,
    max_requests_per_minute,
    max_tokens_per_minute,
    token_encoding_name,
    max_attempts,
    logging_level,
    save_filepath,
):
    # Create a temporary file for saving the responses
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".jsonl")
    save_filepath = temp_file.name  # Get the name of the temporary file created
    temp_file.close()  # Close the file as it will be opened again later

    # Set up an HTTP session
    async with aiohttp.ClientSession() as session:
        # Open the file with the requests
        with open(requests_filepath, "r") as file:
            # Read each line (each request) from the file
            for line in file:
                request_data = json.loads(line)

                # Construct the headers for the request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                }

                # Make the API request and get the response
                async with session.post(
                    request_url, headers=headers, json=request_data
                ) as response:
                    if response.status == 200:
                        # If the request was successful, parse the response and save it
                        response_data = await response.json()
                        with open(save_filepath, "a") as output_file:
                            json.dump(response_data, output_file)
                            output_file.write("\n")
                    else:
                        # If the request was not successful, log detailed error information
                        try:
                            error_response_data = (
                                await response.json()
                            )  # Attempt to parse the error response
                            error_message = error_response_data.get("error", {}).get(
                                "message", "No error message provided"
                            )
                            logging.error(
                                f"Failed request with status code: {response.status}. Error message: {error_message}"
                            )
                        except json.JSONDecodeError:
                            # If parsing the error response fails, log the status code and mention that the error response was not JSON
                            logging.error(
                                f"Failed request with status code: {response.status}. The error response was not in JSON format."
                            )

    """Processes API requests in parallel, throttling to stay under rate limits."""
    # constants
    seconds_to_pause_after_rate_limit_error = 15
    seconds_to_sleep_each_loop = (
        0.001  # 1 ms limits max throughput to 1,000 requests per second
    )
    # infer API endpoint and construct request header
    api_endpoint = api_endpoint_from_url(request_url)
    request_header = {"Authorization": f"Bearer {api_key}"}
    # use api-key header for Azure deployments
    if "/deployments" in request_url:
        request_header = {"api-key": f"{api_key}"}

    # initialize trackers
    queue_of_requests_to_retry = asyncio.Queue()
    task_id_generator = count(start=1)  # Start from 1 or any initial task ID
    status_tracker = (
        StatusTracker()
    )  # single instance to track a collection of variables
    next_request = None  # variable to hold the next request to call

    # initialize available capacity counts
    available_request_capacity = max_requests_per_minute
    available_token_capacity = max_tokens_per_minute
    last_update_time = time.time()

    # initialize flags
    file_not_finished = True  # after file is empty, we'll skip reading it
    logging.debug(f"Initialization complete.")

    # initialize file reading
    with open(requests_filepath, "r") as file:
        for line in file:
            request_data = json.loads(line)
        # `requests` will provide requests one at a time
        requests = file.readlines()
        logging.debug(f"File opened. Entering main loop")
        async with aiohttp.ClientSession() as session:  # Initialize ClientSession here
            while True:
                # get next request (if one is not already waiting for capacity)
                if next_request is None:
                    if not queue_of_requests_to_retry.empty():
                        next_request = queue_of_requests_to_retry.get_nowait()
                        logging.debug(
                            f"Retrying request {next_request.task_id}: {next_request}"
                        )
                    elif file_not_finished:
                        try:
                            # get new request
                            request_json = json.loads(next(requests))
                            next_request = APIRequest(
                                task_id=next(task_id_generator),
                                request_json=request_json,
                                token_consumption=num_tokens_consumed_from_request(
                                    request_json, api_endpoint, token_encoding_name
                                ),
                                attempts_left=max_attempts,
                                metadata=request_json.pop("metadata", None),
                            )
                            status_tracker.num_tasks_started += 1
                            status_tracker.num_tasks_in_progress += 1
                            logging.debug(
                                f"Reading request {next_request.task_id}: {next_request}"
                            )
                        except StopIteration:
                            # if file runs out, set flag to stop reading it
                            logging.debug("Read file exhausted")
                            file_not_finished = False

                # update available capacity
                current_time = time.time()
                seconds_since_update = current_time - last_update_time
                available_request_capacity = min(
                    available_request_capacity
                    + max_requests_per_minute * seconds_since_update / 60.0,
                    max_requests_per_minute,
                )
                available_token_capacity = min(
                    available_token_capacity
                    + max_tokens_per_minute * seconds_since_update / 60.0,
                    max_tokens_per_minute,
                )
                last_update_time = current_time

                # if enough capacity available, call API
                if next_request:
                    next_request_tokens = next_request.token_consumption
                    if (
                        available_request_capacity >= 1
                        and available_token_capacity >= next_request_tokens
                    ):
                        # update counters
                        available_request_capacity -= 1
                        available_token_capacity -= next_request_tokens
                        next_request.attempts_left -= 1

                        # call API
                        tasks = [
                            next_request.call_api(...)
                            for _ in range(concurrent_requests)
                        ]
                        await asyncio.gather(*tasks)
                        next_request = None  # reset next_request to empty

                # if all tasks are finished, break
                if status_tracker.num_tasks_in_progress == 0:
                    break

                # main loop sleeps briefly so concurrent tasks can run
                await asyncio.sleep(seconds_to_sleep_each_loop)

                # if a rate limit error was hit recently, pause to cool down
                seconds_since_rate_limit_error = (
                    time.time() - status_tracker.time_of_last_rate_limit_error
                )
                if (
                    seconds_since_rate_limit_error
                    < seconds_to_pause_after_rate_limit_error
                ):
                    await asyncio.sleep(
                        seconds_to_pause_after_rate_limit_error
                        - seconds_since_rate_limit_error
                    )
                    # ^e.g., if pause is 15 seconds and final limit was hit 5 seconds ago
                    logging.warn(
                        f"Pausing to cool down until {time.ctime(status_tracker.time_of_last_rate_limit_error + seconds_to_pause_after_rate_limit_error)}"
                    )

        # after finishing, log final status
        logging.info(
            f"""Parallel processing complete. Results saved to {save_filepath}"""
        )
        if status_tracker.num_tasks_failed > 0:
            logging.warning(
                f"{status_tracker.num_tasks_failed} / {status_tracker.num_tasks_started} requests failed. Errors logged to {save_filepath}."
            )
        if status_tracker.num_rate_limit_errors > 0:
            logging.warning(
                f"{status_tracker.num_rate_limit_errors} rate limit errors received. Consider running at a lower rate."
            )


@dataclass
class StatusTracker:
    """Stores metadata about the script's progress. Only one instance is created."""

    num_tasks_started: int = 0
    num_tasks_in_progress: int = 0  # script ends when this reaches 0
    num_tasks_succeeded: int = 0
    num_tasks_failed: int = 0
    num_rate_limit_errors: int = 0
    num_api_errors: int = 0  # excluding rate limit errors, counted above
    num_other_errors: int = 0
    time_of_last_rate_limit_error: int = 0  # used to cool off after hitting rate limits


@dataclass
class APIRequest:
    task_id: int
    request_json: dict
    token_consumption: int
    attempts_left: int
    metadata: dict = field(default_factory=dict)
    temp_filepath: str = None  # This will store the temporary file path

    async def call_api(
        self,
        session: aiohttp.ClientSession,
        request_url: str,
        request_header: dict,
        retry_queue: asyncio.Queue,
        status_tracker: object,
    ):
        logging.info(f"Starting request #{self.task_id}")
        try:
            async with session.post(
                url=request_url, headers=request_header, json=self.request_json
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    # Write the successful response to a temporary .jsonl file
                    with open(self.temp_filepath, "a") as output_file:
                        json.dump(response_data, output_file)
                        output_file.write("\n")  # New line for next record in JSONL
                    logging.info(
                        f"Request {self.task_id} saved to {self.temp_filepath}"
                    )
                    status_tracker.num_tasks_succeeded += 1
                else:
                    error_detail = await response.text()
                    logging.error(
                        f"Request {self.task_id} failed with status {response.status}: {error_detail}"
                    )
                    status_tracker.num_tasks_failed += 1
                    if self.attempts_left > 0:
                        self.attempts_left -= 1
                        retry_queue.put_nowait(
                            self
                        )  # Put it back in the queue to retry
        except Exception as e:
            logging.error(f"Request {self.task_id} failed with exception: {str(e)}")
            status_tracker.num_tasks_failed += 1
        finally:
            status_tracker.num_tasks_in_progress -= 1


def api_endpoint_from_url(request_url):
    """Extract the API endpoint from the request URL."""
    match = re.search("^https://[^/]+/v\\d+/(.+)$", request_url)
    if match is None:
        # for Azure OpenAI deployment urls
        match = re.search(
            r"^https://[^/]+/openai/deployments/[^/]+/(.+?)(\?|$)", request_url
        )
    return match[1]


# Correct and optimize jsonl appending function
def append_to_jsonl(data, filename: str) -> None:
    """Append a json payload to the end of a jsonl file."""
    with open(filename, "a") as f:
        for item in data:
            json_string = json.dumps(item)
            f.write(json_string + "\n")


def num_tokens_consumed_from_request(
    request_json: dict,
    api_endpoint: str,
    token_encoding_name: str,
):
    """Count the number of tokens in the request. Only supports completion and embedding requests."""
    encoding = tiktoken.get_encoding(token_encoding_name)
    # if completions request, tokens = prompt + n * max_tokens
    if api_endpoint.endswith("completions"):
        max_tokens = request_json.get("max_tokens", 15)
        n = request_json.get("n", 1)
        completion_tokens = n * max_tokens

        # chat completions
        if api_endpoint.startswith("chat/"):
            num_tokens = 0
            for message in request_json["messages"]:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens -= 1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens + completion_tokens
        # normal completions
        else:
            prompt = request_json["prompt"]
            if isinstance(prompt, str):  # single prompt
                prompt_tokens = len(encoding.encode(prompt))
                num_tokens = prompt_tokens + completion_tokens
                return num_tokens
            elif isinstance(prompt, list):  # multiple prompts
                prompt_tokens = sum([len(encoding.encode(p)) for p in prompt])
                num_tokens = prompt_tokens + completion_tokens * len(prompt)
                return num_tokens
            else:
                raise TypeError(
                    'Expecting either string or list of strings for "prompt" field in completion request'
                )
    # if embeddings request, tokens = input tokens
    elif api_endpoint == "embeddings":
        input = request_json["input"]
        if isinstance(input, str):  # single input
            num_tokens = len(encoding.encode(input))
            return num_tokens
        elif isinstance(input, list):  # multiple inputs
            num_tokens = sum([len(encoding.encode(i)) for i in input])
            return num_tokens
        else:
            raise TypeError(
                'Expecting either string or list of strings for "inputs" field in embedding request'
            )
    # more logic needed to support other API calls (e.g., edits, inserts, DALL-E)
    else:
        raise NotImplementedError(
            f'API endpoint "{api_endpoint}" not implemented in this script'
        )


def task_id_generator_function():
    """Generate integers 0, 1, 2, and so on."""
    task_id = 0
    while True:
        yield task_id
        task_id += 1


if __name__ == "__main__":
    asyncio.run(
        process_api_requests_from_file(
            requests_filepath=requests_filepath,
            request_url=request_url,
            api_key=api_key,
            max_requests_per_minute=max_requests_per_minute,
            max_tokens_per_minute=max_tokens_per_minute,
            token_encoding_name=token_encoding_name,
            max_attempts=max_attempts,
            logging_level=logging_level,
        )
    )
