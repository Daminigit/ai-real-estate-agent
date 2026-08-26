import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

models_to_test = ["llama3-8b-8192", "mixtral-8x7b-32768", "openai/gpt-oss-120b"]

for m in models_to_test:
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say 'test'"}],
            model=m,
            max_tokens=10
        )
        print(f"Success for {m}")
    except Exception as e:
        print(f"FAILED for {m}: {e}")
