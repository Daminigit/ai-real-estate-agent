import sqlite3
import pandas as pd
from typing import Dict, Any

DB_PATH = "crm.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Table for unified leads
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        email TEXT,
        source TEXT,
        profession TEXT,
        budget_min INTEGER,
        budget_max INTEGER,
        intent_score INTEGER DEFAULT 0,
        category TEXT DEFAULT 'Cold',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Table for conversation history
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
    # Table for visits
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS site_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        scheduled_time DATETIME,
        status TEXT DEFAULT 'Confirmed',
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    ''')
    conn.commit()
    conn.close()

def save_lead(lead_data: Dict[str, Any]) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure defaults are present if omitted
    lead_data.setdefault('intent_score', 0)
    lead_data.setdefault('category', 'Cold')
    
    try:
        cursor.execute('''
        INSERT INTO leads (name, phone, email, source, profession, budget_min, budget_max, intent_score, category)
        VALUES (:name, :phone, :email, :source, :profession, :budget_min, :budget_max, :intent_score, :category)
        ''', lead_data)
        lead_id = cursor.lastrowid
        conn.commit()
        return lead_id
    except sqlite3.IntegrityError:
        # Lead exists, return existing ID
        cursor.execute('SELECT id FROM leads WHERE phone = ?', (lead_data.get('phone'),))
        lead_id = cursor.fetchone()[0]
        return lead_id
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
