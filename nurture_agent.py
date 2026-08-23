import os
from llm_client import get_groq_completion

def load_brochure():
    brochure_path = "document/project_brochure.md"
    if os.path.exists(brochure_path):
        with open(brochure_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Brochure not found."

def chat_with_lead(user_input: str, chat_history: list):
    brochure_content = load_brochure()
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI sales agent for Aurelia Heights. Use the following project brochure to "
                "answer the user's questions. Be polite, concise, and helpful. Do not make up information. "
                f"\n\nBrochure Context:\n{brochure_content}"
            )
        }
    ]
    
    # Append history
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": user_input})
    
    response_text = get_groq_completion(messages)
    return response_text
