# Project Task Log

## v1.3 — Review Fixes (Completed)
- [x] Fix 1: Add `locality` field to DB schema + lead capture form
- [x] Fix 2: Phone E.164 normalisation in `save_lead()`
- [x] Fix 3: Pydantic BANT validation + structured logging on parse failures
- [x] Fix 4: `json_object` response format in `llm_client.py`
- [x] Fix 5: Site visit status lifecycle (Scheduled → Completed / No-show / Rescheduled)
- [x] Fix 6: Score every 3rd message + `score_history` table + trajectory chart
- [x] Fix 7: Tab 5 Outcomes (funnel by source & locality)
- [x] Fix 8: Eval harness (`eval_suite.py`, 20 transcripts, accuracy + MAE)
- [x] Update all documentation

## v1.2 — Chat-Based Site Visit Booking (Completed)
- [x] Update `nurture_agent.py` system prompt for visit scheduling
- [x] Add `[BOOK_VISIT: YYYY-MM-DD HH:MM]` tag interception in `app.py`
- [x] Insert booking into database and upgrade lead score
- [x] Hide booking tag from UI chat bubble
- [x] Retroactively upgrade existing site-visit leads to Hot

## v1.1 — Bug Fixes (Completed)
- [x] Fix brochure path: root → `document/project_brochure.md`
- [x] Fix CSV path: root → `data/catchment_enquiries.csv`
- [x] Fix lead score not updating after manual Tab 4 booking

## v1.0 — Initial Implementation (Completed)
- [x] Phase 1: Virtual environment + dependencies
- [x] Phase 2: `database.py` — SQLite schema + `save_lead()`
- [x] Phase 3: `llm_client.py` — Groq wrapper + tenacity retries
- [x] Phase 4: `data_parser.py` — Pandas statistics engine
- [x] Phase 5: Agent modules (segmentation, nurture, qualification)
- [x] Phase 6: `app.py` — 4-tab Streamlit dashboard
- [x] Phase 7: `test_suite.py` — backend test harness
- [x] GitHub: initialised repo, pushed to Daminigit/ai-real-estate-agent

## Remaining (Future)
- [ ] Conversation history windowing (last N messages to prevent context overflow)
- [ ] Validate visit date ≥ today and time within 10 AM – 7 PM
- [ ] Distinguish new vs. duplicate lead in success message
- [ ] Add `max_tokens` to LLM calls
- [ ] SQLite WAL mode for concurrent writes
