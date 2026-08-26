from llm_client import get_groq_completion
print("Testing LLM...")
try:
    res = get_groq_completion([{"role": "user", "content": "Hello"}])
    print("Success:", res)
except Exception as e:
    print("FAILED:", type(e), e)
