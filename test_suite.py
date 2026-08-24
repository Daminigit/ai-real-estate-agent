import sqlite3
from database import DB_PATH, save_lead, init_db
from data_parser import load_enquiries, get_insights_summary
from segmentation_agent import analyze_and_segment
from nurture_agent import chat_with_lead
from qualification_agent import extract_bant_and_score

print("Starting E2E Backend Tests...")

# 1. DB Init
init_db()
print("✅ Database initialized")

# 2 & 3. Save Lead & Deduplication
test_lead = {
    "name": "E2E Test User",
    "phone": "9998887776",
    "email": "test@test.com",
    "source": "Walk-in",
    "profession": "Software Engineer",
    "budget_min": 100,
    "budget_max": 120
}
lead_id_1 = save_lead(test_lead.copy())
lead_id_2 = save_lead(test_lead.copy())

if lead_id_1 == lead_id_2:
    print("✅ Lead deduplication working (same phone returns same ID)")
else:
    print("❌ Lead deduplication FAILED")

# 4. Defaults Check
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT intent_score, category FROM leads WHERE id = ?", (lead_id_1,))
row = cursor.fetchone()
conn.close()
if row and row[0] == 0 and row[1] == 'Cold':
    print("✅ Lead defaults (Score=0, Category=Cold) correctly applied")
else:
    print(f"❌ Lead defaults FAILED, got {row}")

# 5. Data Parser
df = load_enquiries()
if not df.empty:
    print("✅ CSV loaded successfully")
else:
    print("❌ CSV load FAILED")

summary = get_insights_summary(df)
if "Mean Budget" in summary:
    print("✅ Data Summary generated successfully")
else:
    print("❌ Data Summary FAILED")

# 6. LLM segmentation check (Requires GROQ API KEY)
try:
    print("⏳ Testing Groq API (Segmentation)...")
    res = analyze_and_segment(summary)
    if "Error" not in res and len(res) > 50:
        print("✅ Groq API segmentation working")
    else:
        print(f"❌ Groq API segmentation FAILED or returned Error: {res}")
except Exception as e:
    print(f"❌ Groq API segmentation Error: {e}")

# 7. LLM Nurture check
try:
    print("⏳ Testing Groq API (Nurturing)...")
    chat_res = chat_with_lead("What are the amenities?", [])
    if "Error" not in chat_res and len(chat_res) > 20:
        print("✅ Groq API nurturing chat working")
    else:
        print(f"❌ Groq API nurturing chat FAILED or returned Error: {chat_res}")
except Exception as e:
    print(f"❌ Groq API nurturing chat Error: {e}")

# 8. LLM BANT check
try:
    print("⏳ Testing Groq API (BANT Scoring)...")
    history = "user: I want to buy a 3BHK.\nassistant: Great, what is your budget?\nuser: 1.5 Cr, need to move in 3 months."
    bant = extract_bant_and_score(history)
    if bant.get('score') > 0 and 'budget' in bant:
        print("✅ Groq API BANT scoring working (Score > 0)")
    else:
        print(f"❌ Groq API BANT scoring FAILED or returned {bant}")
except Exception as e:
    print(f"❌ Groq API BANT scoring Error: {e}")

print("All tests completed.")
