import sqlite3
import re
import logging
import pandas as pd
from typing import Dict, Any

DB_PATH = "crm.db"

LOCALITIES = [
    "Whitefield", "Hoodi", "Marathahalli", "Sarjapur Road",
    "Bellandur", "Brookefield", "Outer Ring Road", "KR Puram"
]

logger = logging.getLogger(__name__)


def normalise_phone(phone: str) -> str:
    """Normalise any Indian phone to E.164 (+91XXXXXXXXXX)."""
    digits = re.sub(r'\D', '', phone)       # strip non-digits
    if digits.startswith('0'):
        digits = digits[1:]                  # remove leading zero
    if len(digits) == 10:
        digits = '91' + digits              # add country code
    elif digits.startswith('91') and len(digits) == 12:
        pass                                # already correct
    else:
        digits = '91' + digits.lstrip('91')  # best-effort fix
    return '+' + digits


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Leads table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        email TEXT,
        source TEXT,
        profession TEXT,
        locality TEXT,
        budget_min INTEGER,
        budget_max INTEGER,
        intent_score INTEGER DEFAULT 0,
        category TEXT DEFAULT 'Cold',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migrate existing DB: add locality column if missing
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(leads)").fetchall()]
    if 'locality' not in existing_cols:
        cursor.execute("ALTER TABLE leads ADD COLUMN locality TEXT")
        logger.info("Migration: added locality column to leads table")

    # Conversations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    ''')

    # Site visits table — status lifecycle: Scheduled → Completed / No-show / Rescheduled
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS site_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        scheduled_time DATETIME,
        status TEXT DEFAULT 'Scheduled',
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    ''')

    # Migrate existing visits: Confirmed → Scheduled
    cursor.execute("UPDATE site_visits SET status='Scheduled' WHERE status='Confirmed'")

    # Score history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS score_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        score INTEGER,
        category TEXT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    ''')

    conn.commit()
    conn.close()


def save_lead(lead_data: Dict[str, Any]) -> int:
    # Normalise phone before any DB operation
    if lead_data.get('phone'):
        lead_data['phone'] = normalise_phone(str(lead_data['phone']))

    lead_data.setdefault('intent_score', 0)
    lead_data.setdefault('category', 'Cold')
    lead_data.setdefault('locality', None)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO leads (name, phone, email, source, profession, locality,
                           budget_min, budget_max, intent_score, category)
        VALUES (:name, :phone, :email, :source, :profession, :locality,
                :budget_min, :budget_max, :intent_score, :category)
        ''', lead_data)
        lead_id = cursor.lastrowid
        conn.commit()
        return lead_id
    except sqlite3.IntegrityError:
        # Lead already exists — return existing ID
        cursor.execute('SELECT id FROM leads WHERE phone = ?', (lead_data.get('phone'),))
        row = cursor.fetchone()
        return row[0] if row else -1
    finally:
        conn.close()


def record_score(lead_id: int, score: int, category: str):
    """Append a score snapshot to score_history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO score_history (lead_id, score, category) VALUES (?, ?, ?)",
        (lead_id, score, category)
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialised successfully.")
    # Quick normalisation test
    tests = ["9876543210", "09876543210", "+919876543210", "98-765-43210"]
    for t in tests:
        print(f"  {t!r:25} → {normalise_phone(t)}")
