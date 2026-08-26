import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello"}],
        model="llama3-70b-8192", # test with a valid model
        max_tokens=4096
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("FAILED valid model:", e)

try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello"}],
        model="openai/gpt-oss-120b", # test with the user's default model
        max_tokens=4096
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("FAILED user model:", e)
