import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from data_parser import load_enquiries, get_insights_summary
from segmentation_agent import analyze_and_segment
from database import DB_PATH, save_lead, init_db
from nurture_agent import chat_with_lead
from qualification_agent import extract_bant_and_score

# Initialize DB
init_db()

st.set_page_config(page_title="Real Estate AI Agent", layout="wide")
st.title("🏡 AI-Powered Real Estate Agent")

tab1, tab2, tab3, tab4 = st.tabs([
    "Insights & Segments", 
    "Campaign & Capture", 
    "Qualify & Nurture", 
    "Site Visits"
])

def get_all_leads():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    return df

def get_chat_history(lead_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT role, content FROM conversations WHERE lead_id = ? ORDER BY timestamp ASC", conn, params=(lead_id,))
    conn.close()
    return df.to_dict('records')

def save_chat_message(lead_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (lead_id, role, content) VALUES (?, ?, ?)", (lead_id, role, content))
    conn.commit()
    conn.close()

def update_lead_score(lead_id, score, category):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET intent_score = ?, category = ? WHERE id = ?", (score, category, lead_id))
    conn.commit()
    conn.close()

# --- TAB 1: Insights & Segments ---
with tab1:
    st.header("Catchment Analysis & Persona Generation")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Historical Data Summary")
        df_enq = load_enquiries()
        st.dataframe(df_enq.head())
        summary = get_insights_summary(df_enq)
        st.text(summary)
        
    with col2:
        st.subheader("AI Segmentation")
        if st.button("Generate Personas & Ad Copy (Groq)"):
            with st.spinner("Analyzing data and generating insights..."):
                report = analyze_and_segment(summary)
                st.markdown(report)

# --- TAB 2: Campaign & Capture ---
with tab2:
    st.header("Simulated Lead Capture Form")
    st.markdown("Fill this out to simulate a lead coming in from Facebook/Google Ads.")
    
    with st.form("lead_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email")
        source = st.selectbox("Source", ["Facebook Ad", "Google Search", "LinkedIn", "Walk-in"])
        profession = st.text_input("Profession")
        budget = st.slider("Budget Estimate (Lakhs)", 50, 200, (80, 120))
        
        submitted = st.form_submit_button("Submit Lead")
        
        if submitted:
            if not phone:
                st.error("Phone number is required for deduplication.")
            else:
                lead_data = {
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "source": source,
                    "profession": profession,
                    "budget_min": budget[0],
                    "budget_max": budget[1],
                    "intent_score": 0,
                    "category": "Cold"
                }
                lead_id = save_lead(lead_data)
                st.success(f"Lead saved successfully! (Lead ID: {lead_id})")

# --- TAB 3: Qualify & Nurture ---
with tab3:
    st.header("Conversational Nurturing & BANT Scoring")
    leads_df = get_all_leads()
    
    if leads_df.empty:
        st.warning("No leads found. Go capture some leads in Tab 2!")
    else:
        selected_lead_id = st.selectbox("Select a Lead to Nurture", leads_df['id'].tolist(), format_func=lambda x: f"{x}: {leads_df[leads_df['id']==x]['name'].values[0]} ({leads_df[leads_df['id']==x]['phone'].values[0]})")
        
        # Display Live Score
        lead_row = leads_df[leads_df['id'] == selected_lead_id].iloc[0]
        st.metric(label="Live Intent Score (BANT)", value=f"{lead_row['intent_score']} / 100", delta=lead_row['category'])
        
        st.subheader("Chat Interface")
        
        # Initialize chat history in session state
        chat_key = f"chat_{selected_lead_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = get_chat_history(selected_lead_id)
            
        for msg in st.session_state[chat_key]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.markdown(msg["content"])
                
        if prompt := st.chat_input("Message the AI Agent..."):
            # Display user msg
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state[chat_key].append({"role": "user", "content": prompt})
            save_chat_message(selected_lead_id, "user", prompt)
            
            # AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_with_lead(prompt, st.session_state[chat_key][:-1])
                    st.markdown(response)
            
            st.session_state[chat_key].append({"role": "assistant", "content": response})
            save_chat_message(selected_lead_id, "assistant", response)
            
            # Background BANT qualification update
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state[chat_key]])
            with st.spinner("Updating Qualification Score..."):
                bant = extract_bant_and_score(history_text)
                update_lead_score(selected_lead_id, bant.get("score", 0), bant.get("category", "Cold"))
                st.rerun()

# --- TAB 4: Site Visits ---
with tab4:
    st.header("Site Visit Scheduling")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Book a Slot")
        leads_df = get_all_leads()
        if not leads_df.empty:
            visit_lead_id = st.selectbox("Select Lead", leads_df['id'].tolist(), format_func=lambda x: f"{x}: {leads_df[leads_df['id']==x]['name'].values[0]}")
            visit_date = st.date_input("Date")
            visit_time = st.time_input("Time")
            
            if st.button("Confirm Site Visit"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                dt_str = f"{visit_date} {visit_time}"
                c.execute("INSERT INTO site_visits (lead_id, scheduled_time, status) VALUES (?, ?, ?)", (visit_lead_id, dt_str, 'Confirmed'))
                conn.commit()
                conn.close()
                st.success("Visit Booked!")
    
    with col2:
        st.subheader("Confirmed Visits")
        conn = sqlite3.connect(DB_PATH)
        visits_df = pd.read_sql_query("""
            SELECT v.id, l.name, l.phone, v.scheduled_time, v.status 
            FROM site_visits v 
            JOIN leads l ON v.lead_id = l.id
            ORDER BY v.scheduled_time ASC
        """, conn)
        conn.close()
        st.dataframe(visits_df, use_container_width=True)
