# Implementation Plan: AI-Powered Real Estate Lead Generation & Site Visit Conversion Agent

## Goal

Build an agentic AI workflow for **Aurelia Heights** (a fictional residential project in Whitefield–Hoodi, Bengaluru) that manages the complete lead journey — from analyzing historical catchment data to converting qualified leads into confirmed site visits and measuring outcomes by source and locality.

**Technical Constraints:**
* **LLM:** Groq API → model `openai/gpt-oss-120b`, via `groq` Python SDK, API key from `.env`, retry on rate limits
* **UI:** Streamlit dashboard with 5 tabs: Insights & Segments / Campaign & Capture / Qualify & Nurture / Site Visits / Outcomes
* **Knowledge Base:** No Vector DB — load `document/project_brochure.md` directly into the system prompt
* **Orchestration:** Custom Python modules (one per agent), simple orchestrator — no LangChain / LlamaIndex
* **Validation:** Pydantic v2 for BANT output schema

---

## Phase 1: Environment & Setup

### 1.1 Python Virtual Environment
```bash
python -m venv venv
source venv/bin/activate
```

### 1.2 Install Dependencies
```bash
pip install groq streamlit pandas python-dotenv tenacity pydantic
```

### 1.3 Create `.env` File
```env
GROQ_API_KEY=gsk_your_actual_key_here
```

### 1.4 Files Created in This Phase
| File | Purpose |
|------|---------|
| `.env` | Stores `GROQ_API_KEY` securely outside code |
| `venv/` | Isolated Python environment |

---

## Phase 2: Database Layer (`database.py`)

### 2.1 Purpose
Central CRM store using SQLite (`crm.db`) for leads, conversations, site visits, and score history.

### 2.2 Phone Normalisation

All phones are normalised to E.164 (`+91XXXXXXXXXX`) before any DB operation via `normalise_phone()`:
```python
def normalise_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('0'): digits = digits[1:]
    if len(digits) == 10: digits = '91' + digits
    return '+' + digits
```
This ensures `9876543210`, `09876543210`, `+919876543210`, `98-765-43210` all resolve to the same DB row.

### 2.3 Schema Design

**Table: `leads`**
| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique lead identifier |
| `name` | TEXT | — | Lead's full name |
| `phone` | TEXT | **UNIQUE** (E.164) | Normalised phone for deduplication |
| `email` | TEXT | — | Email address |
| `source` | TEXT | — | Lead source (Facebook Ad, Google Search, etc.) |
| `profession` | TEXT | — | Lead's profession |
| `locality` | TEXT | — | Where the buyer lives — 8 fixed catchment options |
| `budget_min` | INTEGER | — | Lower bound of budget in Lakhs |
| `budget_max` | INTEGER | — | Upper bound of budget in Lakhs |
| `intent_score` | INTEGER | DEFAULT 0 | BANT score 0–100 |
| `category` | TEXT | DEFAULT 'Cold' | Hot / Warm / Cold |
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
| `status` | TEXT | DEFAULT **'Scheduled'** | Lifecycle: Scheduled → Completed / No-show / Rescheduled |

**Table: `score_history`**
| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Entry identifier |
| `lead_id` | INTEGER | FOREIGN KEY → `leads.id` | Links score to a lead |
| `score` | INTEGER | — | BANT score snapshot |
| `category` | TEXT | — | Hot / Warm / Cold at that moment |
| `recorded_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp of score snapshot |

### 2.4 Migration Safety
`init_db()` uses `ALTER TABLE ... ADD COLUMN` with a `PRAGMA table_info()` check — existing DBs gain new columns without data loss.

### 2.5 Key Functions
| Function | Purpose |
|----------|---------|
| `normalise_phone(phone)` | E.164 normalisation |
| `init_db()` | Creates all tables + runs migrations |
| `save_lead(lead_data)` | Inserts lead (normalises phone first); returns existing ID on duplicate |
| `record_score(lead_id, score, category)` | Appends snapshot to `score_history` |

---

## Phase 3: LLM Client (`llm_client.py`)

### 3.1 Purpose
Single wrapper function for all Groq API calls. Centralises model selection, key management, retry logic, and optional structured output mode.

### 3.2 Function Signature
```python
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def get_groq_completion(messages, model="openai/gpt-oss-120b",
                        temperature=0.7, response_format=None) -> str:
```
* `response_format={"type": "json_object"}` is passed by the qualification agent for structured output
* Falls back gracefully if the model doesn't support json_object mode (catches the error and retries without it)

---

## Phase 4: Data Parser (`data_parser.py`)

### 4.1 Purpose
Load `data/catchment_enquiries.csv` (200 records) and compute all statistics in Pandas before passing to the LLM.

### 4.2 Statistics Computed
| Statistic | Method |
|-----------|--------|
| Profession % split | `value_counts() / total * 100` |
| Budget mean & median | midpoint of min/max, then `.mean()` / `.median()` |
| Budget buckets | `pd.cut()` — `<90L`, `90–115L`, `115L+` |
| Config % split | `value_counts() / total * 100` |
| Timeline % split | `value_counts() / total * 100` |
| Source % split | `value_counts() / total * 100` |

---

## Phase 5: Agent Modules

### 5.1 Segmentation Agent (`segmentation_agent.py`)
* Receives pre-computed stats string → calls Groq → returns 3–5 personas with Meta/LinkedIn/Google targeting and ad copy
* System prompt explicitly forbids inventing or recalculating statistics

### 5.2 Nurture Agent (`nurture_agent.py`)
* Loads `document/project_brochure.md` into system prompt at runtime
* **Site Visit Booking:** Instructed to append `[BOOK_VISIT: YYYY-MM-DD HH:MM]` when user confirms a date/time
* `app.py` intercepts this tag, strips it before display, inserts into `site_visits`, and upgrades lead to Hot

### 5.3 Qualification Agent (`qualification_agent.py`)
* Receives full conversation history → extracts BANT via Groq
* Output validated by `BANTResult` Pydantic model:
  ```python
  class BANTResult(BaseModel):
      budget: str = "Unknown"
      authority: str = "Unknown"
      need: str = "Unknown"
      timeline: str = "Unknown"
      score: int = 0       # clamped 0–100 by field_validator
      category: Literal["Hot", "Warm", "Cold"] = "Cold"
  ```
* Parse failures logged via `logging.warning()` with raw response — never silent
* Called every **3rd user message** (not every message) to reduce LLM calls and score jitter

---

## Phase 6: Streamlit UI (`app.py`)

### 6.1 Tab 1 — Insights & Segments
Two columns: historical data summary + on-demand persona/ad copy generation via Groq.

### 6.2 Tab 2 — Campaign & Capture
Lead capture form fields:
| Field | Widget | Notes |
|-------|--------|-------|
| Name | `st.text_input` | |
| Phone | `st.text_input` | Required; normalised to E.164 before save |
| Email | `st.text_input` | |
| Source | `st.selectbox` | 8 options including Instagram Ad, Referral, Hoarding |
| Profession | `st.text_input` | |
| **Locality** | `st.selectbox` | 8 fixed catchment options: Whitefield, Hoodi, Marathahalli, Sarjapur Road, Bellandur, Brookefield, Outer Ring Road, KR Puram |
| Budget | `st.slider` | 50–200 Lakhs range |

### 6.3 Tab 3 — Qualify & Nurture
* Lead selector shows: `ID: Name (Phone) — Locality`
* Live score metric + locality metric side by side
* **Score trajectory line chart** from `score_history` table
* BANT qualification runs every 3rd user message
* Chat-based visit booking via `[BOOK_VISIT: ...]` tag interception

### 6.4 Tab 4 — Site Visits
* Booking form (lead, date, time) → inserts with `status='Scheduled'`
* Status summary metrics (Scheduled / Completed / No-show / Rescheduled)
* **Inline status updater** — select visit + new status → updates DB instantly
* Full visits table with locality column

### 6.5 Tab 5 — Outcomes
* Reads `leads` + `site_visits` tables via Pandas
* Builds funnel: Leads → Visits Booked → Completed → No-shows
* `groupby` on both `source` and `locality`
* Computes Booking Rate % and Completion Rate % per group
* Bar charts for visual comparison

---

## Phase 7: Evaluation Harness (`eval_suite.py`)

### 7.1 Purpose
Answer the demo question: *"How do you know the BANT score is right?"*

### 7.2 Structure
* 20 fixed conversation transcripts with hand-labelled `expected_category` (Hot/Warm/Cold) and `expected_score`
* Balanced across: 5 Hot, 5 Warm, 5 Cold, 5 edge cases (NRI, investment buyer, budget mismatch, etc.)

### 7.3 Metrics
| Metric | Definition |
|--------|-----------|
| **Category Accuracy** | % of transcripts where predicted category matches label |
| **Score MAE** | Mean Absolute Error between predicted and expected score |

### 7.4 Running
```bash
python eval_suite.py
```
Exits with code 1 if accuracy < 70%.

---

## Phase 8: Verification & Testing

### 8.1 Start the Application
```bash
source venv/bin/activate
streamlit run app.py
```
Open `http://localhost:8501`.

### 8.2 Test Checklist

| # | Test | Tab | Expected Result |
|---|------|-----|----------------|
| 1 | App starts without errors | — | All 5 tabs visible, no tracebacks |
| 2 | CSV data loads correctly | Tab 1 | First 5 rows + pre-computed stats |
| 3 | LLM generates personas | Tab 1 | 3–5 personas with targeting params |
| 4 | Submit a new lead with locality | Tab 2 | Success with Lead ID, locality stored |
| 5 | Phone deduplication | Tab 2 | `9876543210` and `+919876543210` → same ID |
| 6 | Chat responds from brochure | Tab 3 | Amenities, pricing answered from brochure |
| 7 | BANT scores every 3rd message | Tab 3 | Score only updates at msg 3, 6, 9... |
| 8 | Score trajectory chart appears | Tab 3 | Line chart visible after 2+ scoring events |
| 9 | Chat-based visit booking | Tab 3 | Say "book visit for tomorrow 3pm" → toast appears, visit in Tab 4 |
| 10 | Manual visit booking | Tab 4 | Select lead, date, time → appears in table as Scheduled |
| 11 | Visit status update | Tab 4 | Change Scheduled → Completed → metrics update |
| 12 | Outcomes tab populates | Tab 5 | Funnel data by source and locality |
| 13 | BANT eval harness passes | CLI | `python eval_suite.py` → ≥70% accuracy |
| 14 | Data persists across restarts | All | Stop/restart Streamlit → data still in `crm.db` |

---

## Summary: File → Phase Mapping

| File | Phase | Funnel Stage |
|------|-------|-------------|
| `.env` | Phase 1 | Setup |
| `database.py` | Phase 2 | Capture (CRM) + Normalisation + History |
| `llm_client.py` | Phase 3 | All (LLM access) |
| `data_parser.py` | Phase 4 | Understand |
| `segmentation_agent.py` | Phase 5.1 | Understand + Identify |
| `nurture_agent.py` | Phase 5.2 | Nurture + Convert |
| `qualification_agent.py` | Phase 5.3 | Qualify |
| `app.py` | Phase 6 | All (UI) |
| `eval_suite.py` | Phase 7 | Evaluate |
