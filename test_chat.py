import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq()
models = client.models.list()
model_ids = [m.id for m in models.data]

for model in model_ids:
    try:
        client.chat.completions.create(
            messages=[{"role": "user", "content": "hi"}],
            model=model
        )
        print(f"SUCCESS {model}")
    except Exception as e:
        print(f"FAILED {model}: {e}")
