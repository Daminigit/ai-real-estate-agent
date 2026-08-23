# Implementation Tasks (Groq & Streamlit Refactor)

- `[x]` **Phase 1: Environment & Tooling**
  - `[x]` Install `groq`, `streamlit`, `tenacity`.
  - `[x]` Implement `llm_client.py` for Groq API with retries.
  - `[x]` Clean up previous LangChain/Chroma dependencies from code.
- `[x]` **Phase 2: Custom Agents (No LangChain)**
  - `[x]` Update `segmentation_agent.py` to use `llm_client`.
  - `[x]` Create `qualification_agent.py` for BANT scoring.
  - `[x]` Create `nurture_agent.py` that loads `project_brochure.md` into the system prompt.
- `[x]` **Phase 3: Streamlit UI (`app.py`)**
  - `[x]` Tab 1: Insights & Segments (Trigger segmentation).
  - `[x]` Tab 2: Campaign & Capture (Mock Lead form, dedupe to SQLite).
  - `[x]` Tab 3: Qualify & Nurture (Live chat with `nurture_agent`, live BANT updating).
  - `[x]` Tab 4: Site Visits (Slot booking UI, leads table).
- `[x]` **Phase 4: Verification & Walkthrough**
  - `[x]` Verify all tabs work and state is maintained.
  - `[x]` Update `walkthrough.md` artifact.
