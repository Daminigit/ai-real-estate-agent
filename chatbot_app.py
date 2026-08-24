import json
import sqlite3
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from database import DB_PATH, save_lead
from rag_engine import get_rag_chain
from dotenv import load_dotenv

load_dotenv()

def extract_bant_and_score(conversation_history: str) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert lead qualifier. Read the following conversation and extract BANT details (Budget, Authority, Need, Timeline). "
                   "Also provide a score from 0 to 100 based on their intent to buy. "
                   "Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', 'timeline', 'score', 'category' (Hot/Warm/Cold)."),
        ("user", "{history}")
    ])
    try:
        chain = prompt | llm
        response = chain.invoke({"history": conversation_history})
        
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"BANT Extraction Error: {e}")
        return {"score": 0, "category": "Cold"}

def book_site_visit(lead_id: int, time_slot: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO site_visits (lead_id, scheduled_time, status) VALUES (?, ?, ?)",
                   (lead_id, time_slot, "Confirmed"))
    conn.commit()
    conn.close()
    return True

def chat_loop():
    print("Welcome to Aurelia Heights! I am your AI assistant. How can I help you today?")
    print("(Type 'quit' to exit)\n")
    
    try:
        rag_chain = get_rag_chain()
    except Exception as e:
        print(f"RAG not initialized properly. Run rag_engine.py first. Error: {e}")
        return
        
    chat_history = []
    
    lead_data = {
        "name": "Test User",
        "phone": "+919876543210",
        "email": "test@example.com",
        "source": "Chatbot",
        "profession": "Unknown",
        "budget_min": 0,
        "budget_max": 0,
        "intent_score": 0,
        "category": "Cold"
    }
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            break
            
        chat_history.append(f"User: {user_input}")
        
        # 1. Answer Question using RAG
        response = rag_chain.invoke({"input": user_input})
        ai_response = response["answer"]
        print(f"\nAI: {ai_response}\n")
        chat_history.append(f"AI: {ai_response}")
        
        # 2. Check for site visit intent
        if any(word in user_input.lower() for word in ['visit', 'see', 'tour', 'book', 'schedule']):
            print("AI: Excellent! I can schedule a site visit for you. When would you like to come? (e.g. 'This Saturday 10 AM')")
            time_input = input("You (Time Slot): ")
            chat_history.append(f"User: {time_input}")
            
            lead_id = save_lead(lead_data)
            book_site_visit(lead_id, time_input)
            
            print("AI: Great! Your site visit is confirmed for " + time_input + ". Our team will contact you shortly.")
            chat_history.append(f"AI: Visit confirmed for {time_input}")
            break
            
    print("\n--- Session Ended. Qualifying Lead ---")
    history_text = "\n".join(chat_history)
    bant_data = extract_bant_and_score(history_text)
    print("BANT Qualification:", json.dumps(bant_data, indent=2))
    
    lead_data["intent_score"] = bant_data.get("score", 0)
    lead_data["category"] = bant_data.get("category", "Cold")
    save_lead(lead_data)
    print("Lead Profile Updated in CRM.")

if __name__ == "__main__":
    chat_loop()
