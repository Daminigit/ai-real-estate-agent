import os
from dotenv import load_dotenv
from llm_client_gemini import get_gemini_completion
load_dotenv(override=True)
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say hello world!"}
]
print(get_gemini_completion(messages))
