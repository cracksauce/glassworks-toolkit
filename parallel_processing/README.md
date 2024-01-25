# Consult Prompt Optimization Initiative
## Parallel processing API calls for batch runs

Adapted parallel processing [from OpenAI cookbook example](https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py), originally written for the embeddings model. Adapted to work for the Chat Completion models.

## Getting started

1. Clone the repo
2. Replace 'input.csv' with your own data in column A (default is 315q expanded MedQA test set)
3. Add or use one of the system messages and one of the prompts in `prompts.py`
5. Replace the prompt and system message references in `main.py` and `generate_requests.py` to match the title of each per `prompts.py`
6. Set your environment configs, model choice, and API key in a `.env` using `example.env`
7. Install dependencies via `pip install -r requirements.txt`
8. Run program with `python main.py`
9. By default, `output.csv` will be found in the outputs folder but can be configured in `.env`

## What happens when you run the program
When you run the program, four files are generated:
- `data.py` turns the values in the first column of the `input.csv` into an array. It's saved to a file so you don't have to generate them all each time.
- `requests_to_chat_completion.jsonl`, is a list of requests that are sent to the OpenAI API.
- `results_of_chat_completion.jsonl`, the entire request including the API response.
- `output.csv` is a spreadsheet containing the original prompt, the model's output, and additional information.