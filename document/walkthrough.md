# Real Estate AI Agent: Implementation Walkthrough (Streamlit + Groq)

I have successfully re-architected the agentic workflow to use the **Groq API** with custom Python orchestration (removing LangChain) and built a comprehensive **Streamlit UI** to manage the entire lead journey.

## Changes Made

### 1. Project Infrastructure & UI
* **Streamlit App (`app.py`)**: A modern, interactive dashboard with exactly four tabs representing the funnel.
* **Database (`database.py`)**: SQLite CRM (`crm.db`) to store unified lead records, conversational history, live intent scores, and scheduled site visits. Duplicate phone numbers are automatically deduplicated.
* **API Client (`llm_client.py`)**: A wrapper around the Groq Python SDK using `tenacity` for rate-limit retries.

### 2. Custom AI Agents (No LangChain)
* **Analytics Agent (`segmentation_agent.py`)**: Analyzes the parsed `catchment_enquiries.csv` using `llama-3.3-70b-versatile` to generate buyer personas and ad copy on demand.
* **Nurture Agent (`nurture_agent.py`)**: Powers the live chat. Instead of a Vector DB, it loads `project_brochure.md` directly into the system prompt for lightning-fast, highly accurate conversational responses.
* **Qualification Agent (`qualification_agent.py`)**: Analyzes the chat history in the background after every message to extract BANT details and update the lead's Intent Score (0-100) and Category (Hot/Warm/Cold).

---

## How to Run & Verify the System

> [!IMPORTANT]
> The application is powered by Groq. You must set your API key in the environment for the LLM to function.

### 1. Setup API Key
Ensure your `.env` file in the workspace directory (`/Users/darshan/Documents/Potential buyer/`) has your Groq API key:
```env
GROQ_API_KEY="your_groq_api_key_here"
```

### 2. Activate Environment & Run Streamlit
In your terminal, start the Streamlit application:
```bash
source venv/bin/activate
streamlit run app.py
```

### 3. Testing the 4 Funnel Tabs
1. **Insights & Segments**: View the historical catchment data summary and click "Generate Personas & Ad Copy" to trigger the Groq LLM.
2. **Campaign & Capture**: Fill out the simulated ad lead form. Try submitting the exact same phone number twice to verify the deduplication logic in the database.
3. **Qualify & Nurture**: 
   - Select the lead you just created. 
   - Ask questions about the project (e.g., "What are the amenities?").
   - Watch the **Live Intent Score (BANT)** metric automatically update at the top of the tab as you chat and express intent!
4. **Site Visits**: Once a lead expresses intent to visit, head to this tab to select the lead, pick a date and time slot, and confirm the booking. It will instantly appear in the "Confirmed Visits" table.
