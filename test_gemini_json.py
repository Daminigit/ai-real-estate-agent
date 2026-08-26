import os
import json
from dotenv import load_dotenv
from llm_client_gemini import get_gemini_completion
load_dotenv(override=True)
messages = [
    {"role": "system", "content": "You are a JSON generator."},
    {"role": "user", "content": "Output {'greeting': 'hello'}"}
]
res = get_gemini_completion(messages, response_format={"type": "json_object"})
print("RAW:")
print(res)
try:
    print("PARSED:")
    print(json.loads(res))
except Exception as e:
    print(f"FAILED TO PARSE: {e}")
