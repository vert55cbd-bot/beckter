import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "clients.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            date_naissance TEXT,
            age INTEGER,
            email TEXT,
            telephone TEXT,
            adresse TEXT,
            code_postal TEXT,
            ville TEXT,
            iban TEXT,
            bic TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_telephone ON clients(telephone)")
    conn.commit()
    conn.close()


def normalize_phone(phone: str) -> str:
    """Normalize phone number: remove spaces, dots, dashes. Convert +33 to 0."""
    phone = phone.strip().replace(" ", "").replace(".", "").replace("-", "")
    if phone.startswith("+33"):
        phone = "0" + phone[3:]
    elif phone.startswith("33") and len(phone) == 11:
        phone = "0" + phone[2:]
    return phone


def search_by_phone(phone: str):
    phone = normalize_phone(phone)
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM clients WHERE telephone = ?", (phone,)
    )
    results = cursor.fetchall()
    conn.close()
    return results


def insert_client(data: dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO clients (nom, prenom, date_naissance, age, email, telephone, adresse, code_postal, ville, iban, bic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("nom", ""),
        data.get("prenom", ""),
        data.get("date_naissance", ""),
        data.get("age", 0),
        data.get("email", ""),
        normalize_phone(data.get("telephone", "")),
        data.get("adresse", ""),
        data.get("code_postal", ""),
        data.get("ville", ""),
        data.get("iban", ""),
        data.get("bic", ""),
    ))
    conn.commit()
    conn.close()


def get_client_count():
    conn = get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM clients")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def clear_db():
    conn = get_connection()
    conn.execute("DELETE FROM clients")
    conn.commit()
    conn.close()
