# Real Estate AI Agent — Walkthrough & Change Log

## Current State

The application is a fully functional, 5-tab Streamlit dashboard powered by the Groq API (`groq/compound-mini`) with a local SQLite CRM. All 7 review fixes have been implemented.

---

## How to Run

> [!IMPORTANT]
> The application is powered by Groq. You must set your API key in `.env` for the LLM to function.

```bash
# 1. Set your API key
echo 'GROQ_API_KEY=gsk_your_key_here' > .env

# 2. Activate virtual environment
source venv/bin/activate

# 3. Start the dashboard
streamlit run app.py
# Opens at http://localhost:8501

# 4. Run the BANT evaluation harness (optional)
python eval_suite.py
```

---

## Tab-by-Tab Guide

### Tab 1 — Insights & Segments
1. The historical data summary is auto-loaded from `data/catchment_enquiries.csv`
2. Click **"Generate Personas & Ad Copy (Groq)"** to trigger the segmentation agent
3. The LLM will return 3–5 buyer personas with Meta/LinkedIn/Google targeting parameters and ad copy

### Tab 2 — Campaign & Capture
1. Fill in the simulated lead form (name, phone, email, source, profession, **locality**, budget)
2. The **Locality** field is a fixed selectbox with 8 catchment options — data arrives pre-normalised
3. Phone is automatically normalised to E.164 before saving — `9876543210`, `09876543210`, `+919876543210` all map to the same lead row
4. Submitting the same phone number twice returns the existing Lead ID (no duplicate)

### Tab 3 — Qualify & Nurture
1. Select a lead — the selector shows name, phone, and locality
2. The **Live Intent Score (BANT)** metric and locality are shown side by side
3. A **Score Trajectory** line chart appears once 2+ scoring events exist
4. Chat with the AI agent — it knows all Aurelia Heights details (prices, amenities, location) from the brochure
5. BANT qualification runs **every 3rd user message** to reduce cost and score jitter
6. **Chat-based site visit booking:** Tell the agent *"I'd like to book a visit"* → it will ask for your preferred date and time → confirm → a `📅` toast will appear and the visit is automatically saved in `site_visits` as `Scheduled`, with the lead upgraded to Hot

### Tab 4 — Site Visits
1. **Book a Slot** (left): Select lead, pick date/time, click Confirm → inserts as `Scheduled`
2. **Status Summary Metrics**: Real-time count of Scheduled / Completed / No-show / Rescheduled visits
3. **Inline Status Updater**: Select any visit and change its status to Completed, No-show, or Rescheduled
4. Full visits table with locality column for geographic analysis

### Tab 5 — Outcomes
1. Automatically reads all leads and visits and computes a funnel: Leads → Visits Booked → Completed → No-shows
2. Broken down by **Source** (Facebook Ad, Google, etc.) and **Locality** (Whitefield, Hoodi, etc.)
3. Computes Booking Rate % and Completion Rate % per group
4. Bar charts visualise which sources and localities convert best
5. This directly validates whether the catchment targeting personas from Tab 1 are working

---

## Change Log

### v1.0 — Initial Implementation
- 4-tab Streamlit dashboard (Insights, Capture, Nurture, Site Visits)
- Groq LLM integration with tenacity retries
- SQLite CRM with 3 tables (leads, conversations, site_visits)
- Phone-based deduplication

### v1.1 — Bug Fixes
- Fixed `nurture_agent.py` brochure path from root to `document/project_brochure.md`
- Fixed `data_parser.py` CSV path from root to `data/catchment_enquiries.csv`
- Fixed lead score not updating when visit booked via Tab 4
- Retroactively upgraded all existing site-visit leads to Hot

### v1.2 — Chat-Based Site Visit Booking
- Updated nurture agent system prompt to proactively collect visit date/time
- Added `[BOOK_VISIT: YYYY-MM-DD HH:MM]` tag interception in `app.py`
- Visit automatically inserted into `site_visits` and lead upgraded to Hot via chat

### v1.3 — All 7 Review Fixes
| Fix | What Changed |
|-----|-------------|
| **Locality field** | `locality TEXT` added to `leads` table with DB migration; Tab 2 form uses `st.selectbox` with 8 fixed catchment options |
| **E.164 phone normalisation** | `normalise_phone()` in `database.py` — 4 phone formats → same row |
| **Pydantic BANT validation** | `BANTResult` model validates output; score clamped 0–100; `logging.warning()` on every parse failure with raw response |
| **json_object response format** | `llm_client.py` accepts `response_format` parameter with graceful fallback |
| **Visit status lifecycle** | Default changed from `Confirmed` → `Scheduled`; Completed / No-show / Rescheduled states; inline updater in Tab 4 |
| **Score throttle + history** | BANT runs every 3rd user message; each score written to `score_history`; line chart in Tab 3 |
| **Outcomes tab (Tab 5)** | Pandas `groupby` funnel by source and locality; booking rate and completion rate; bar charts |
| **Eval harness** | `eval_suite.py` — 20 hand-labelled transcripts, category accuracy + score MAE, exits 1 if <70% |

---

## Verification

```bash
# Database migration (safe on existing crm.db)
python database.py
# Expected output:
# Database initialised successfully.
# '9876543210'    → +919876543210
# '09876543210'   → +919876543210
# '+919876543210' → +919876543210
# '98-765-43210'  → +919876543210

# BANT evaluation harness
python eval_suite.py
# Expected: ≥ 17/20 correct category, MAE < 20 points
```
