"""
Landing page for ad deep-links.
Run:  venv/bin/streamlit run landing.py --server.port 8503
Access via: http://localhost:8503/?source=google&persona=it_professional
"""

# pyrefly: ignore [missing-import]
import streamlit as st
import sqlite3
import re
import uuid
import logging

from database import DB_PATH, save_lead, record_score, LOCALITIES, init_db
from nurture_agent import chat_with_lead
from qualification_agent import extract_bant_and_score

logging.basicConfig(level=logging.INFO)
init_db()

st.set_page_config(
    page_title="Aurelia Heights — Talk to Our AI Agent",
    page_icon="🏡",
    layout="centered"
)

# ── Read URL params ────────────────────────────────────────────────────────────
params = st.query_params
url_source = params.get("source", "Ad Link").replace("_", " ").title()
url_persona = params.get("persona", "")

# ── Helpers ───────────────────────────────────────────────────────────────────


def save_chat_message(lead_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (lead_id, role, content) VALUES (?, ?, ?)",
        (lead_id, role, content)
    )
    conn.commit()
    conn.close()


def update_lead_field(lead_id, field, value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"UPDATE leads SET {field} = ? WHERE id = ?", (value, lead_id))
    conn.commit()
    conn.close()


def update_lead_score(lead_id, score, category):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE leads SET intent_score = ?, category = ? WHERE id = ?", (score, category, lead_id))
    conn.commit()
    conn.close()


def get_lead_row(lead_id):
    conn = sqlite3.connect(DB_PATH)
    import pandas as pd
    df = pd.read_sql_query("SELECT * FROM leads WHERE id = ?", conn, params=(lead_id,))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else {}


# ── Create skeleton lead on first load ────────────────────────────────────────
if "landing_lead_id" not in st.session_state:
    # Anonymous token so phone UNIQUE constraint doesn't collide
    anon_token = f"anon_{uuid.uuid4().hex[:8]}"
    lead_data = {
        "name": "Web Visitor",
        "phone": anon_token,
        "email": "",
        "source": url_source,
        "profession": "",
        "locality": None,
        "budget_min": 0,
        "budget_max": 0,
        "intent_score": 0,
        "category": "Cold"
    }
    lead_id = save_lead(lead_data)
    st.session_state["landing_lead_id"] = lead_id
    st.session_state["qual_step"] = "locality"   # qualifying state machine: locality -> budget -> phone -> done
    st.session_state["landing_chat"] = []
    st.session_state["qual_done"] = False
    st.session_state["chosen_budget_label"] = ""

lead_id = st.session_state["landing_lead_id"]

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main > div { max-width: 720px; margin: auto; }
    .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🏡 Aurelia Heights")
st.caption(f"*You arrived via {url_source}* · AI Assistant")
st.divider()

# ── Initialise chat with injected first user message ──────────────────────────
INJECTED_OPENING = "Hi, I want to know more about this project"

if not st.session_state["landing_chat"]:
    # Inject the first user message (simulates the click-from-ad context)
    st.session_state["landing_chat"].append({"role": "user", "content": INJECTED_OPENING})
    save_chat_message(lead_id, "user", INJECTED_OPENING)

    # Bot immediately asks for locality (qualifying step 1)
    bot_q1 = (
        "👋 Welcome to Aurelia Heights! I'm your AI property assistant.\n\n"
        "To help you find the perfect home, let me ask you two quick questions.\n\n"
        "**Which locality are you currently living in or looking at?**"
    )
    st.session_state["landing_chat"].append({"role": "assistant", "content": bot_q1})
    save_chat_message(lead_id, "assistant", bot_q1)

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state["landing_chat"]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])

# ── Qualifying Step: LOCALITY ─────────────────────────────────────────────────
if st.session_state["qual_step"] == "locality":
    st.markdown("**Select your locality:**")
    loc_cols = st.columns(4)
    for i, loc in enumerate(LOCALITIES):
        if loc_cols[i % 4].button(loc, key=f"loc_{loc}"):
            # Record user's choice
            with st.chat_message("user"):
                st.markdown(loc)
            st.session_state["landing_chat"].append({"role": "user", "content": loc})
            save_chat_message(lead_id, "user", loc)

            # Update lead profile
            update_lead_field(lead_id, "locality", loc)

            # Bot asks budget (qualifying step 2)
            bot_q2 = f"Great, **{loc}** it is! 🏙️\n\n**What's your approximate budget for this home?**"
            st.session_state["landing_chat"].append({"role": "assistant", "content": bot_q2})
            save_chat_message(lead_id, "assistant", bot_q2)

            st.session_state["qual_step"] = "budget"
            st.rerun()

    if prompt := st.chat_input("Or type your locality here..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["landing_chat"].append({"role": "user", "content": prompt})
        save_chat_message(lead_id, "user", prompt)

        update_lead_field(lead_id, "locality", prompt)

        bot_q2 = f"Great, **{prompt}** it is! 🏙️\n\n**What's your approximate budget for this home?**"
        st.session_state["landing_chat"].append({"role": "assistant", "content": bot_q2})
        save_chat_message(lead_id, "assistant", bot_q2)

        st.session_state["qual_step"] = "budget"
        st.rerun()

# ── Qualifying Step: BUDGET ───────────────────────────────────────────────────
elif st.session_state["qual_step"] == "budget":
    budget_options = {
        "Below ₹90 Lakhs": (60, 90),
        "₹90L – ₹1.2 Crore": (90, 120),
        "Above ₹1.2 Crore": (120, 200),
    }
    st.markdown("**Select your budget range:**")
    b_cols = st.columns(3)
    for i, (label, (bmin, bmax)) in enumerate(budget_options.items()):
        if b_cols[i].button(label, key=f"bgt_{label}"):
            # Record user's choice
            with st.chat_message("user"):
                st.markdown(label)
            st.session_state["landing_chat"].append({"role": "user", "content": label})
            save_chat_message(lead_id, "user", label)

            # Update lead profile with budget
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE leads SET budget_min = ?, budget_max = ? WHERE id = ?", (bmin, bmax, lead_id))
            conn.commit()
            conn.close()

            # Run BANT score now that we have locality + budget
            lead_info = get_lead_row(lead_id)
            real_history = [
                m for m in st.session_state["landing_chat"]
                if not (m["role"] == "assistant" and "two quick questions" in m["content"])
            ]
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in real_history])
            bant = extract_bant_and_score(history_text, lead_info=lead_info)
            score = bant.get("score", 0)
            category = bant.get("category", "Cold")
            update_lead_score(lead_id, score, category)
            record_score(lead_id, score, category)

            # Bot asks for phone number (qualifying step 3)
            chat_id = lead_info.get("phone", "Unknown")
            bot_intro = (
                f"Great choice! 💰 **{label}** noted. Your unique Chat ID is **{chat_id}**.\n\n"
                f"Aurelia Heights offers beautifully crafted 2BHK and 3BHK apartments in the Whitefield–Hoodi belt "
                f"of Bengaluru — just **1.8 km from Hoodi Metro Station**.\n\n"
                f"I can suggest the best configurations for you. "
                f"Feel free to ask me anything — pricing, amenities, floor plans, or to book a site visit! 🏡"
            )
            st.session_state["landing_chat"].append({"role": "assistant", "content": bot_intro})
            save_chat_message(lead_id, "assistant", bot_intro)
            st.session_state["chosen_budget_label"] = label
            st.session_state["qual_step"] = "done"
            st.session_state["qual_done"] = True
            st.rerun()

    if prompt := st.chat_input("Or type your budget here..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["landing_chat"].append({"role": "user", "content": prompt})
        save_chat_message(lead_id, "user", prompt)

        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE leads SET budget_min = ?, budget_max = ? WHERE id = ?", (0, 0, lead_id))
        conn.commit()
        conn.close()

        lead_info = get_lead_row(lead_id)
        real_history = [
            m for m in st.session_state["landing_chat"]
            if not (m["role"] == "assistant" and "two quick questions" in m["content"])
        ]
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in real_history])
        bant = extract_bant_and_score(history_text, lead_info=lead_info)
        score = bant.get("score", 0)
        category = bant.get("category", "Cold")
        update_lead_score(lead_id, score, category)
        record_score(lead_id, score, category)

        chat_id = lead_info.get("phone", "Unknown")
        bot_intro = (
            f"Great choice! 💰 **{prompt}** noted. Your unique Chat ID is **{chat_id}**.\n\n"
            f"Aurelia Heights offers beautifully crafted 2BHK and 3BHK apartments in the Whitefield–Hoodi belt "
            f"of Bengaluru — just **1.8 km from Hoodi Metro Station**.\n\n"
            f"I can suggest the best configurations for you. "
            f"Feel free to ask me anything — pricing, amenities, floor plans, or to book a site visit! 🏡"
        )
        st.session_state["landing_chat"].append({"role": "assistant", "content": bot_intro})
        save_chat_message(lead_id, "assistant", bot_intro)
        st.session_state["chosen_budget_label"] = prompt
        st.session_state["qual_step"] = "done"
        st.session_state["qual_done"] = True
        st.rerun()

# ── Free-form Chat (after qualifying is done) ─────────────────────────────────
elif st.session_state["qual_step"] == "done":
    if prompt := st.chat_input("Ask me anything about Aurelia Heights..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["landing_chat"].append({"role": "user", "content": prompt})
        save_chat_message(lead_id, "user", prompt)

        lead_info = get_lead_row(lead_id)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat_with_lead(prompt, st.session_state["landing_chat"][:-1], lead_info=lead_info)

                # Intercept site visit booking tag
                match = re.search(r'(?:\[BOOK_VISIT:\s*(.*?)]|<<BOOK_VISIT:\s*(.*?)>>)', response)
                if match:
                    dt_str = match.group(1) or match.group(2)
                    dt_str = dt_str.strip()
                    response = re.sub(r'\[BOOK_VISIT:.*?\]|<<BOOK_VISIT:.*?>>', '', response).strip()
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "INSERT INTO site_visits (lead_id, scheduled_time, status) VALUES (?, ?, ?)",
                        (lead_id, dt_str, 'Scheduled')
                    )
                    conn.commit()
                    conn.close()
                    update_lead_score(lead_id, 100, "Hot")
                    record_score(lead_id, 100, "Hot")
                    st.toast(f"✅ Site visit booked for {dt_str}!", icon="📅")

                st.markdown(response)

        st.session_state["landing_chat"].append({"role": "assistant", "content": response})
        save_chat_message(lead_id, "assistant", response)

        # Live BANT update (Ensure site visits are permanently Hot)
        conn = sqlite3.connect(DB_PATH)
        visit = conn.execute("SELECT id FROM site_visits WHERE lead_id = ? AND status = 'Scheduled'", (lead_id,)).fetchone()
        conn.close()

        lead_info = get_lead_row(lead_id)
        if visit:
            score, category = 100, "Hot"
        else:
            real_history = [m for m in st.session_state["landing_chat"]]
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in real_history])
            bant = extract_bant_and_score(history_text, lead_info=lead_info)
            score = bant.get("score", 0)
            category = bant.get("category", "Cold")

        update_lead_score(lead_id, score, category)
        record_score(lead_id, score, category)

        st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "RERA Reg: PRM/KA/RERA/1251/446/PR/2026/007841 | "
    "[rera.karnataka.gov.in](https://rera.karnataka.gov.in) | "
    "Sunrise Estates Pvt. Ltd."
)
