# 🏡 AI-Powered Real Estate Agent

An AI-driven real estate CRM and conversational agent built with Streamlit and Groq. The system acts as a virtual real estate assistant capable of automatically qualifying leads, nurturing them via conversational AI, scoring their intent (using the BANT framework), and scheduling site visits.

## ✨ Features
- **Lead Capture & Segmentation**: Catchment analysis, persona generation, and capturing leads from customized ad deep-links.
- **AI Conversational Nurturing**: Context-aware chat agent that answers property queries using RAG (Retrieval-Augmented Generation).
- **Automated Qualification**: Real-time BANT (Budget, Authority, Need, Timeline) intent scoring based on conversation history.
- **Site Visit Scheduling**: Integrated booking system and tracking dashboard (Scheduled, Completed, No-show).
- **CRM Dashboard**: High-level insights, lead segments, chat history review, and outcome analytics.

## 🛠 Tech Stack
- **Frontend/UI**: Streamlit
- **LLM / AI**: Groq API
- **Database**: SQLite (`crm.db`)
- **Environment**: Python 3

## 🚀 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Daminigit/ai-real-estate-agent.git
   cd ai-real-estate-agent
   ```

2. **Set up a Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you generate a `requirements.txt` if you add new packages)*

4. **Environment Variables**
   Create a `.env` file in the root directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Run the Application**
   There are two main Streamlit entry points:
   - **Main CRM Dashboard**: 
     ```bash
     streamlit run app.py
     ```
   - **Landing Page (Lead Capture & Deep-links)**:
     ```bash
     streamlit run landing.py --server.port 8503
     ```

## 📂 Project Structure
- `app.py`: Main Streamlit app containing CRM insights, nurture chat, site visit tracker, and analytics.
- `landing.py`: Ad landing page where leads land and interact with the AI assistant.
- `database.py`: SQLite database schema, initialization, and data interaction functions.
- `nurture_agent.py` / `qualification_agent.py`: AI agents responsible for interacting with leads and scoring them.
- `segmentation_agent.py`: Analyzes catchment data and generates personas for ad campaigns.
- `rag_engine.py`: Handles RAG functionality for fetching property details and amenities.
- `llm_client.py`: Wrapper for making API calls to Groq.
- `test_suite.py` & `eval_suite.py`: Evaluation scripts and testing modules for the agents.

## 📜 License
MIT License
