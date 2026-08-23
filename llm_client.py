import os
# pyrefly: ignore [missing-import]
from groq import Groq, AuthenticationError
# pyrefly: ignore [missing-import]
from tenacity import retry, wait_random_exponential, stop_after_attempt
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def get_groq_completion(messages, model="openai/gpt-oss-120b", temperature=0.7) -> str:
    """Wrapper to call Groq API with rate limit retries."""
    # Ensure latest env vars are loaded dynamically
    load_dotenv(override=True)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "your_groq" in api_key:
        return "Error: Invalid or missing GROQ_API_KEY in .env file."
        
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        return f"Error: Groq client not initialized. {e}"
        
    try:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except AuthenticationError as e:
        # Auth errors surface immediately, no retry
        print(f"Groq Auth Error: {e}")
        return f"Authentication Error: {e}"
    except Exception as e:
        # Re-raise API/rate-limit errors so tenacity can retry them
        print(f"Groq API Error: {e}")
        raise e
