# Implementation Plan: AI-Powered Real Estate Lead Generation & Site Visit Conversion Agent

## Goal

Build an agentic AI workflow for **Aurelia Heights** (a fictional residential project in Whitefield–Hoodi, Bengaluru) that manages the complete lead journey — from analyzing historical catchment data to converting qualified leads into confirmed site visits.

**Technical Constraints:**
* **LLM:** Groq API → model `openai/gpt-oss-120b`, via `groq` Python SDK, API key from `.env`, retry on rate limits
* **UI:** Streamlit dashboard with 4 tabs: Insights & Segments / Campaign & Capture / Qualify & Nurture / Site Visits
* **Knowledge Base:** No Vector DB — load `project_brochure.md` directly into the system prompt
* **Orchestration:** Custom Python modules (one per agent), simple orchestrator — no LangChain / LlamaIndex

---

## Phase 1: Environment & Setup

### 1.1 Python Virtual Environment
* Create a virtual environment: `python -m venv venv`
* Activate: `source venv/bin/activate`

### 1.2 Install Dependencies
```bash
pip install groq streamlit pandas python-dotenv tenacity
```
* `groq` — Python SDK for the Groq cloud inference API
* `streamlit` — interactive dashboard framework
* `pandas` — data loading and statistical computation
* `python-dotenv` — load `GROQ_API_KEY` from `.env` file
* `tenacity` — retry decorator for rate-limit handling

### 1.3 Remove Old Dependencies (if migrating)
```bash
pip uninstall langchain langchain-openai chromadb -y
```

### 1.4 Create `.env` File
```env
GROQ_API_KEY=gsk_your_actual_key_here
```

### 1.5 Files Created in This Phase
| File | Purpose |
|------|---------|
| `.env` | Stores `GROQ_API_KEY` securely outside code |
| `venv/` | Isolated Python environment |

---

## Phase 2: Database Layer (`database.py`)

### 2.1 Purpose
Central CRM store using SQLite (`crm.db`) for leads, conversations, and site visits.

### 2.2 Schema Design

**Table: `leads`**
| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique lead identifier |
| `name` | TEXT | — | Lead's full name |
| `phone` | TEXT | **UNIQUE** | Phone number (used for deduplication) |
| `email` | TEXT | — | Email address |
| `source` | TEXT | — | Where the lead came from (Facebook Ad, Google Search, LinkedIn, Walk-in) |
| `profession` | TEXT | — | Lead's profession |
| `budget_min` | INTEGER | — | Lower bound of budget in Lakhs |
| `budget_max` | INTEGER | — | Upper bound of budget in Lakhs |
| `intent_score` | INTEGER | DEFAULT 0 | BANT score from 0 to 100 |
| `category` | TEXT | DEFAULT 'Cold' | Hot / Warm / Cold classification |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the lead was captured |

**Table: `conversations`**
| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Message identifier |
| `lead_id` | INTEGER | FOREIGN KEY → `leads.id` | Links message to a lead |
| `role` | TEXT | — | `user` or `assistant` |
| `content` | TEXT | — | The message text |
| `timestamp` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the message was sent |

**Table: `site_visits`**
| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Visit identifier |
| `lead_id` | INTEGER | FOREIGN KEY → `leads.id` | Links visit to a lead |
| `scheduled_time` | DATETIME | — | Date and time of the visit |
| `status` | TEXT | DEFAULT 'Confirmed' | Visit status (Confirmed / Rescheduled / No-show) |

### 2.3 Key Functions
* `init_db()` — Creates all three tables if they don't exist
* `save_lead(lead_data)` — Inserts a new lead; if phone already exists (duplicate), returns the existing lead's ID instead of creating a new record

### 2.4 Files Created in This Phase
| File | Purpose |
|------|---------|
| `database.py` | SQLite schema definition, `init_db()`, `save_lead()` |
| `crm.db` | SQLite database file (created at runtime) |

---

## Phase 3: LLM Client (`llm_client.py`)

### 3.1 Purpose
A single wrapper function that all agent modules call to interact with the Groq API. Centralizes model selection, API key management, and retry logic.

### 3.2 Implementation Details
* **SDK:** `groq` Python SDK — `Groq(api_key=...)` client
* **Model:** `openai/gpt-oss-120b` (default, configurable per call)
* **Temperature:** `0.7` (default, configurable per call)
* **API Key:** Loaded dynamically from `.env` using `load_dotenv(override=True)` on every call to handle key updates without restarting the server
* **Retry Strategy:** `tenacity` decorator with:
  * `wait_random_exponential(min=1, max=10)` — randomized backoff between 1–10 seconds
  * `stop_after_attempt(5)` — give up after 5 failed attempts
* **Error Handling:** API errors (rate limits, server errors) are re-raised so `tenacity` can retry them; auth errors surface immediately

### 3.3 Function Signature
```python
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def get_groq_completion(messages, model="openai/gpt-oss-120b", temperature=0.7) -> str:
```
* **Input:** `messages` — list of `{"role": ..., "content": ...}` dicts (OpenAI-compatible format)
* **Output:** The LLM's response text as a string

### 3.4 Files Created in This Phase
| File | Purpose |
|------|---------|
| `llm_client.py` | `get_groq_completion()` — single entry point for all LLM calls |

---

## Phase 4: Data Parser (`data_parser.py`)

### 4.1 Purpose
Load `catchment_enquiries.csv` (200 historical records) and compute **all statistics in Pandas** before passing them to the LLM. The LLM is explicitly forbidden from doing math.

### 4.2 Statistics Computed

| Statistic | Method | Example Output |
|-----------|--------|----------------|
| **Profession % split** | `value_counts() / total * 100` | `{'IT Professional': '28.5%', 'Doctor': '15.0%', ...}` |
| **Budget mean** | `(budget_min + budget_max) / 2` → `.mean()` | `Mean Budget: 97.3L` |
| **Budget median** | `(budget_min + budget_max) / 2` → `.median()` | `Median Budget: 95.0L` |
| **Budget buckets** | `pd.cut()` into 3 bins: `<90L`, `90–115L`, `115L+` | `{'<90L': '35.0%', '90-115L': '45.5%', '115L+': '19.5%'}` |
| **Config % split** | `value_counts() / total * 100` | `{'2 BHK': '55.0%', '3 BHK': '45.0%'}` |
| **Timeline % split** | `value_counts() / total * 100` | `{'Immediate': '20.0%', '3–6 months': '40.0%', ...}` |
| **Source % split** | `value_counts() / total * 100` | `{'Facebook': '30.0%', 'Google': '25.0%', ...}` |

### 4.3 Key Functions
* `load_enquiries(filepath)` — Reads CSV into a DataFrame
* `get_insights_summary(df)` — Computes all 7 statistics and returns a formatted string ready for the LLM prompt

### 4.4 Files Created in This Phase
| File | Purpose |
|------|---------|
| `data_parser.py` | `load_enquiries()`, `get_insights_summary()` |

---

## Phase 5: Agent Modules (Custom Python Orchestration)

### 5.1 Segmentation Agent (`segmentation_agent.py`)

**Funnel Stage:** Understand + Identify & Target

**What It Does:**
1. Receives the pre-computed statistics string from `data_parser.py`
2. Constructs a system prompt + user prompt
3. Calls `get_groq_completion()` to generate output

**System Prompt:**
> "You are an expert Real Estate Marketing AI Agent. Your goal is to analyze historical enquiry data for a new residential project in Catchment A, generate 3-5 concrete buyer personas, and provide platform-specific targeting parameters (Meta, LinkedIn, Google) and ad copy for each. **Use ONLY the numbers provided. Do not calculate, convert, or invent any statistics. Your job is interpretation and marketing implications, not math.**"

**User Prompt:**
> "Here is the summary of historical enquiries: [pre-computed stats]. Please provide: 1. Key Demand Insights 2. 3-5 Buyer Personas 3. Targeting Parameters & Ad Copy for Meta, LinkedIn, and Google."

**Output:** Markdown-formatted report with personas, targeting parameters, and ad copy.

---

### 5.2 Nurture Agent (`nurture_agent.py`)

**Funnel Stage:** Nurture (Continuous Engagement)

**What It Does:**
1. Reads `project_brochure.md` from disk at runtime using `open()`
2. Injects the **full brochure text** (~4 KB) into the system prompt
3. Appends the conversation history and the user's latest message
4. Calls `get_groq_completion()` to generate a response

**System Prompt:**
> "You are an AI sales agent for Aurelia Heights. Use the following project brochure to answer the user's questions. Be polite, concise, and helpful. Do not make up information.
> 
> Brochure Context: [full project_brochure.md content — configurations, pricing ₹82L–₹1.52 Cr, payment plan, amenities, location advantages, FAQs, contact details]"

**Knowledge Available to the Agent:**
* 4 unit types: 2 BHK Compact (₹82–88L), 2 BHK Premium (₹94L–₹1.02 Cr), 3 BHK Classic (₹1.18–₹1.28 Cr), 3 BHK Grande (₹1.38–₹1.52 Cr)
* Payment plan: ₹2L booking → 10% on agreement → 75% construction-linked → 15% on possession
* 28,000 sq ft clubhouse, 78% open space, Hoodi Metro 1.8 km away
* Home loan approved by SBI, HDFC, ICICI, Axis, LIC HFL
* Site visit: Experience Centre open 7 days, 10 AM – 7 PM, free pick-up within 15 km

**Output:** Conversational response grounded strictly in brochure facts.

---

### 5.3 Qualification Agent (`qualification_agent.py`)

**Funnel Stage:** Qualify (Intent Scoring)

**What It Does:**
1. Receives the full conversation history as a single text string
2. Constructs a system prompt asking for BANT extraction
3. Calls `get_groq_completion()` and parses the JSON response

**System Prompt:**
> "Read the following conversation and extract BANT details (Budget, Authority, Need, Timeline). Also provide a score from 0 to 100 based on their intent to buy. Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', 'timeline', 'score' (integer), 'category' (Hot/Warm/Cold). Do not include markdown blocks."

**Output:** Parsed Python dict:
```python
{
    "budget": "90L–1 Cr",
    "authority": "Decision maker",
    "need": "2 BHK for self-use",
    "timeline": "3 months",
    "score": 75,
    "category": "Hot"
}
```

**Error Handling:** If the LLM returns malformed JSON, falls back to `{"score": 0, "category": "Cold"}`.

### 5.4 Files Created in This Phase
| File | Purpose |
|------|---------|
| `segmentation_agent.py` | `analyze_and_segment()` — personas + ad copy |
| `nurture_agent.py` | `chat_with_lead()` — brochure-powered chat |
| `qualification_agent.py` | `extract_bant_and_score()` — BANT JSON extraction |

---

## Phase 6: Streamlit UI (`app.py`)

### 6.1 App Configuration
* `st.set_page_config(page_title="Real Estate AI Agent", layout="wide")`
* Title: "🏡 AI-Powered Real Estate Agent"
* Database initialized on startup: `init_db()`

### 6.2 Tab 1 — Insights & Segments

**Layout:** Two columns side by side

| Left Column | Right Column |
|-------------|-------------|
| Shows first 5 rows of `catchment_enquiries.csv` as a dataframe | "Generate Personas & Ad Copy (Groq)" button |
| Displays the pre-computed statistics summary (profession %, budget buckets, etc.) | On click → calls `analyze_and_segment(summary)` → renders LLM output as markdown |

### 6.3 Tab 2 — Campaign & Capture

**Layout:** A Streamlit form simulating a lead capture from Facebook/Google/LinkedIn ads

| Form Field | Widget | Details |
|-----------|--------|---------|
| Name | `st.text_input` | Lead's full name |
| Phone Number | `st.text_input` | **Required** — used for deduplication |
| Email | `st.text_input` | Optional |
| Source | `st.selectbox` | Facebook Ad / Google Search / LinkedIn / Walk-in |
| Profession | `st.text_input` | Free text |
| Budget Estimate | `st.slider` | Range 50–200 Lakhs, returns tuple `(min, max)` |

**On Submit:**
1. Validates that phone is not empty
2. Calls `save_lead(lead_data)` — if phone already exists in SQLite, returns existing ID (deduplication)
3. New leads start with `intent_score=0` and `category='Cold'`
4. Displays success message with the lead ID

### 6.4 Tab 3 — Qualify & Nurture

**Layout:** Lead selector → Live Score metric → Chat interface

**Components:**
1. **Lead Dropdown:** `st.selectbox` showing all leads as `"ID: Name (Phone)"`
2. **Live Intent Score:** `st.metric` displaying `"75 / 100"` with delta showing `"Hot"` / `"Warm"` / `"Cold"`
3. **Chat History:** Loaded from SQLite `conversations` table on first render, cached in `st.session_state`
4. **Chat Input:** `st.chat_input("Message the AI Agent...")`

**Message Flow (on each user message):**
1. Display user message in chat bubble → save to `conversations` table
2. Call `chat_with_lead(prompt, history)` → display AI response → save to `conversations` table
3. **Background BANT update:** Concatenate full conversation history → call `extract_bant_and_score(history_text)` → update `intent_score` and `category` in `leads` table → `st.rerun()` to refresh the metric

### 6.5 Tab 4 — Site Visits

**Layout:** Two columns — booking form (left) + confirmed visits table (right)

| Left Column (Book a Slot) | Right Column (Confirmed Visits) |
|--------------------------|--------------------------------|
| Lead dropdown | Dataframe showing: Visit ID, Lead Name, Phone, Scheduled Time, Status |
| Date picker (`st.date_input`) | Data joined from `site_visits` + `leads` tables |
| Time picker (`st.time_input`) | Ordered by scheduled time ascending |
| "Confirm Site Visit" button | |

**On Confirm:** Inserts a row into `site_visits` with `status='Confirmed'` and the selected date/time.

### 6.6 Files Created in This Phase
| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application — 4-tab dashboard |

---

## Phase 7: Verification & Testing

### 7.1 Start the Application
```bash
source venv/bin/activate
streamlit run app.py
```
Open `http://localhost:8501` in the browser.

### 7.2 Test Checklist

| # | Test | Tab | Expected Result |
|---|------|-----|----------------|
| 1 | App starts without errors | — | All 4 tabs visible, no Python tracebacks |
| 2 | CSV data loads correctly | Tab 1 | First 5 rows of `catchment_enquiries.csv` displayed + pre-computed percentage splits shown |
| 3 | LLM generates personas | Tab 1 | Click button → Groq returns 3–5 personas with targeting params and ad copy |
| 4 | Submit a new lead | Tab 2 | Fill form → success message with Lead ID |
| 5 | Phone deduplication works | Tab 2 | Submit same phone number again → returns the same Lead ID (no duplicate row) |
| 6 | Chat responds from brochure | Tab 3 | Ask "What are the amenities?" → response mentions 28,000 sq ft clubhouse, swimming pool, etc. |
| 7 | BANT score updates live | Tab 3 | After a few messages expressing intent → score increases from 0, category changes from Cold to Warm/Hot |
| 8 | Book a site visit | Tab 4 | Select lead, pick date/time, click Confirm → visit appears in the table |
| 9 | Data persists across restarts | All | Stop and restart Streamlit → leads, conversations, and visits are still in `crm.db` |

---

## Summary: File → Phase Mapping

| File | Phase | Funnel Stage |
|------|-------|-------------|
| `.env` | Phase 1 | Setup |
| `database.py` | Phase 2 | Capture (CRM) |
| `llm_client.py` | Phase 3 | All (LLM access) |
| `data_parser.py` | Phase 4 | Understand |
| `segmentation_agent.py` | Phase 5.1 | Understand + Identify |
| `nurture_agent.py` | Phase 5.2 | Nurture |
| `qualification_agent.py` | Phase 5.3 | Qualify |
| `app.py` | Phase 6 | All (UI) |
