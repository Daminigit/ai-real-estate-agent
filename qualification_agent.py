import json
from llm_client import get_groq_completion

def extract_bant_and_score(conversation_history: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert lead qualifier. Read the following conversation and extract BANT details (Budget, Authority, Need, Timeline). "
                "Also provide a score from 0 to 100 based on their intent to buy. "
                "Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', 'timeline', 'score' (integer), 'category' (Hot/Warm/Cold). "
                "Do not include markdown blocks like ```json."
            )
        },
        {
            "role": "user",
            "content": conversation_history
        }
    ]
    response_text = get_groq_completion(messages)
    try:
        content = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"BANT Extraction Error: {e}, Response: {response_text}")
        return {"score": 0, "category": "Cold"}
