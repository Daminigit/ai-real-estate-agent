# pyrefly: ignore [missing-import]
import streamlit as st
import sqlite3
import pandas as pd
import re
import logging
from datetime import datetime
from data_parser import load_enquiries, get_insights_summary
from segmentation_agent import analyze_and_segment
from database import DB_PATH, save_lead, init_db, record_score, LOCALITIES
from nurture_agent import chat_with_lead
from qualification_agent import extract_bant_and_score

logging.basicConfig(level=logging.INFO)

# Initialize DB (handles migrations automatically)
init_db()

st.set_page_config(page_title="Real Estate AI Agent", layout="wide")
st.title("🏡 AI-Powered Real Estate Agent")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Insights & Segments",
    "Campaign & Capture",
    "Qualify & Nurture",
    "Site Visits",
    "📊 Outcomes"
])

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_all_leads():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    return df

def get_chat_history(lead_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT role, content FROM conversations WHERE lead_id = ? ORDER BY timestamp ASC",
        conn, params=(lead_id,)
    )
    conn.close()
    return df.to_dict('records')

def save_chat_message(lead_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (lead_id, role, content) VALUES (?, ?, ?)",
        (lead_id, role, content)
    )
    conn.commit()
    conn.close()

def update_lead_score(lead_id, score, category):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET intent_score = ?, category = ? WHERE id = ?",
        (score, category, lead_id)
    )
    conn.commit()
    conn.close()

def get_score_history(lead_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT score, category, recorded_at FROM score_history WHERE lead_id = ? ORDER BY recorded_at ASC",
        conn, params=(lead_id,)
    )
    conn.close()
    return df

# ── TAB 1: Insights & Segments ───────────────────────────────────────────────
with tab1:
    st.header("Catchment Analysis & Persona Generation")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Historical Data Summary")
        df_enq = load_enquiries("data/catchment_enquiries.csv")
        st.dataframe(df_enq.head())
        summary = get_insights_summary(df_enq)
        st.text(summary)

    with col2:
        st.subheader("AI Segmentation")
        if st.button("Generate Personas & Ad Copy (Groq)"):
            with st.spinner("Analyzing data and generating insights..."):
                report = analyze_and_segment(summary)
                st.markdown(report)

# ── TAB 2: Campaign & Capture ─────────────────────────────────────────────────
with tab2:
    st.header("Simulated Lead Capture Form")
    st.markdown("Fill this out to simulate a lead coming in from Facebook/Google Ads.")

    with st.form("lead_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email")
        source = st.selectbox("Source", ["Facebook Ad", "Google Search", "LinkedIn", "Instagram Ad", "Walk-in", "Referral", "Property Portal", "Hoarding"])
        profession = st.text_input("Profession")
        locality = st.selectbox("Locality (Where do you live?)", LOCALITIES)
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
                    "locality": locality,
                    "budget_min": budget[0],
                    "budget_max": budget[1],
                    "intent_score": 0,
                    "category": "Cold"
                }
                lead_id = save_lead(lead_data)
                st.success(f"Lead saved successfully! (Lead ID: {lead_id})")

# ── TAB 3: Qualify & Nurture ──────────────────────────────────────────────────
with tab3:
    st.header("Conversational Nurturing & BANT Scoring")
    leads_df = get_all_leads()

    if leads_df.empty:
        st.warning("No leads found. Go capture some leads in Tab 2!")
    else:
        selected_lead_id = st.selectbox(
            "Select a Lead to Nurture",
            leads_df['id'].tolist(),
            format_func=lambda x: (
                f"{x}: {leads_df[leads_df['id']==x]['name'].values[0]} "
                f"({leads_df[leads_df['id']==x]['phone'].values[0]}) "
                f"— {leads_df[leads_df['id']==x]['locality'].values[0] or 'Locality unknown'}"
            )
        )

        lead_row = leads_df[leads_df['id'] == selected_lead_id].iloc[0]
        col_score, col_cat = st.columns(2)
        with col_score:
            st.metric(label="Live Intent Score (BANT)", value=f"{lead_row['intent_score']} / 100", delta=lead_row['category'])
        with col_cat:
            st.metric(label="Locality", value=lead_row['locality'] or "—")

        # Score history chart
        score_hist = get_score_history(selected_lead_id)
        if not score_hist.empty and len(score_hist) > 1:
            st.subheader("Score Trajectory")
            st.line_chart(score_hist.set_index('recorded_at')['score'])

        st.subheader("Chat Interface")

        chat_key = f"chat_{selected_lead_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = get_chat_history(selected_lead_id)

        for msg in st.session_state[chat_key]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Message the AI Agent..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state[chat_key].append({"role": "user", "content": prompt})
            save_chat_message(selected_lead_id, "user", prompt)

            # AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_with_lead(prompt, st.session_state[chat_key][:-1])

                    # Intercept booking tags
                    match = re.search(r'\[BOOK_VISIT:\s*(.*?)\]', response)
                    if match:
                        dt_str = match.group(1).strip()
                        response = re.sub(r'\[BOOK_VISIT:.*?\]', '', response).strip()

                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO site_visits (lead_id, scheduled_time, status) VALUES (?, ?, ?)",
                            (selected_lead_id, dt_str, 'Scheduled')
                        )
                        conn.commit()
                        conn.close()

                        update_lead_score(selected_lead_id, 100, "Hot")
                        record_score(selected_lead_id, 100, "Hot")
                        st.toast(f"✅ Site visit scheduled for {dt_str}!", icon="📅")

                    st.markdown(response)

            st.session_state[chat_key].append({"role": "assistant", "content": response})
            save_chat_message(selected_lead_id, "assistant", response)

            # BANT qualification — run every 3rd message to reduce LLM calls & jitter
            msg_count = len([m for m in st.session_state[chat_key] if m['role'] == 'user'])
            if msg_count % 3 == 0:
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state[chat_key]])
                with st.spinner("Updating Qualification Score..."):
                    bant = extract_bant_and_score(history_text)
                    score = bant.get("score", 0)
                    category = bant.get("category", "Cold")
                    update_lead_score(selected_lead_id, score, category)
                    record_score(selected_lead_id, score, category)

            st.rerun()

# ── TAB 4: Site Visits ────────────────────────────────────────────────────────
with tab4:
    st.header("Site Visit Scheduling")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Book a Slot")
        leads_df = get_all_leads()
        if not leads_df.empty:
            visit_lead_id = st.selectbox(
                "Select Lead",
                leads_df['id'].tolist(),
                format_func=lambda x: f"{x}: {leads_df[leads_df['id']==x]['name'].values[0]}"
            )
            visit_date = st.date_input("Date")
            visit_time = st.time_input("Time")

            if st.button("Confirm Site Visit"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                dt_str = f"{visit_date} {visit_time}"
                c.execute(
                    "INSERT INTO site_visits (lead_id, scheduled_time, status) VALUES (?, ?, ?)",
                    (visit_lead_id, dt_str, 'Scheduled')
                )
                conn.commit()
                conn.close()

                update_lead_score(visit_lead_id, 100, "Hot")
                record_score(visit_lead_id, 100, "Hot")
                st.success("Visit Scheduled! Lead status upgraded to Hot.")

    with col2:
        st.subheader("All Visits")
        conn = sqlite3.connect(DB_PATH)
        visits_df = pd.read_sql_query("""
            SELECT v.id, l.name, l.phone, l.locality, v.scheduled_time, v.status
            FROM site_visits v
            JOIN leads l ON v.lead_id = l.id
            ORDER BY v.scheduled_time ASC
        """, conn)
        conn.close()

        if not visits_df.empty:
            # Status summary metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📅 Scheduled", int((visits_df['status'] == 'Scheduled').sum()))
            m2.metric("✅ Completed", int((visits_df['status'] == 'Completed').sum()))
            m3.metric("❌ No-show", int((visits_df['status'] == 'No-show').sum()))
            m4.metric("🔄 Rescheduled", int((visits_df['status'] == 'Rescheduled').sum()))

            # Inline status updater
            st.subheader("Update Visit Status")
            visit_to_update = st.selectbox(
                "Select Visit",
                visits_df['id'].tolist(),
                format_func=lambda x: f"#{x} — {visits_df[visits_df['id']==x]['name'].values[0]} @ {visits_df[visits_df['id']==x]['scheduled_time'].values[0]}"
            )
            new_status = st.selectbox("New Status", ["Scheduled", "Completed", "No-show", "Rescheduled"])
            if st.button("Update Status"):
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE site_visits SET status = ? WHERE id = ?", (new_status, visit_to_update))
                conn.commit()
                conn.close()
                st.success(f"Visit #{visit_to_update} marked as {new_status}.")
                st.rerun()

            st.dataframe(visits_df, use_container_width=True)
        else:
            st.info("No visits booked yet.")

# ── TAB 5: Outcomes ───────────────────────────────────────────────────────────
with tab5:
    st.header("📊 Outcomes — Closing the Loop")
    st.markdown("Site-visit rates by **source** and **locality** — directly testing whether our catchment targeting is working.")

    conn = sqlite3.connect(DB_PATH)
    leads_all = pd.read_sql_query("SELECT id, source, locality FROM leads", conn)
    visits_all = pd.read_sql_query("SELECT lead_id, status FROM site_visits", conn)
    conn.close()

    if leads_all.empty:
        st.info("No leads in the system yet. Capture some leads first.")
    else:
        # Merge: one row per lead, with visit flags
        leads_all['has_visit'] = leads_all['id'].isin(visits_all['lead_id'])
        leads_all['completed'] = leads_all['id'].isin(
            visits_all[visits_all['status'] == 'Completed']['lead_id']
        )
        leads_all['no_show'] = leads_all['id'].isin(
            visits_all[visits_all['status'] == 'No-show']['lead_id']
        )

        def build_funnel(df, group_col):
            grouped = df.groupby(group_col).agg(
                Leads=('id', 'count'),
                Visits_Booked=('has_visit', 'sum'),
                Completed=('completed', 'sum'),
                No_shows=('no_show', 'sum')
            ).reset_index()
            grouped['Booking_Rate_%'] = (grouped['Visits_Booked'] / grouped['Leads'] * 100).round(1)
            grouped['Completion_Rate_%'] = (grouped['Completed'] / grouped['Leads'] * 100).round(1)
            grouped['No_show_Rate_%'] = (grouped['No_shows'] / grouped['Visits_Booked'].replace(0, 1) * 100).round(1)
            return grouped

        col_s, col_l = st.columns(2)

        with col_s:
            st.subheader("By Source")
            source_funnel = build_funnel(leads_all, 'source')
            st.dataframe(source_funnel, use_container_width=True)
            st.bar_chart(source_funnel.set_index('source')[['Visits_Booked', 'Completed']])

        with col_l:
            st.subheader("By Locality")
            loc_data = leads_all.dropna(subset=['locality'])
            if loc_data.empty:
                st.info("No locality data yet — ensure leads are captured with the locality field.")
            else:
                locality_funnel = build_funnel(loc_data, 'locality')
                st.dataframe(locality_funnel, use_container_width=True)
                st.bar_chart(locality_funnel.set_index('locality')[['Visits_Booked', 'Completed']])
