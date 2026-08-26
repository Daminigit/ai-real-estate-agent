import os
from llm_client import get_groq_completion

def load_brochure():
    brochure_path = "document/project_brochure.md"
    if os.path.exists(brochure_path):
        with open(brochure_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Brochure not found."

def chat_with_lead(user_input: str, chat_history: list, lead_info: dict = None):
    brochure_content = load_brochure()
    
    lead_context = ""
    if lead_info:
        lead_context = (
            f"\n\nLead Profile:\n"
            f"- Name: {lead_info.get('name', 'Unknown')}\n"
            f"- Budget: ₹{lead_info.get('budget_min')}L - ₹{lead_info.get('budget_max')}L\n"
            f"- Locality: {lead_info.get('locality', 'Unknown')}\n"
            f"- Profession: {lead_info.get('profession', 'Unknown')}\n"
        )
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI sales agent for Aurelia Heights. Use the following project brochure to "
                "answer the user's questions. Be polite, concise, and helpful. Do not make up information. "
                "If the user expresses interest in a site visit, proactively ask for their preferred date and time. "
                "Once they provide a date and time, confirm the booking and append the exact string [BOOK_VISIT: YYYY-MM-DD HH:MM] "
                "at the very end of your response. Ensure the date is in YYYY-MM-DD format and time is in HH:MM (24-hour) format. "
                "Example: [BOOK_VISIT: 2026-08-25 14:30]"
                f"{lead_context}"
                f"\n\nBrochure Context:\n{brochure_content}"
            )
        }
    ]
    
    # Append history
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": user_input})
    
    response_text = get_groq_completion(messages, max_tokens=500)
    return response_text
