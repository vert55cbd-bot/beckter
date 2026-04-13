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


IDF_DEPTS = ("75", "77", "78", "91", "92", "93", "94", "95")


def _region_filter(region: str) -> str:
    """Return SQL WHERE clause for region filtering."""
    if region == "IDF":
        clauses = " OR ".join(f"code_postal LIKE '{d}%'" for d in IDF_DEPTS)
        return f"({clauses})"
    elif region == "HORS_IDF":
        clauses = " AND ".join(f"code_postal NOT LIKE '{d}%'" for d in IDF_DEPTS)
        return f"({clauses} AND code_postal != '')"
    return "1=1"


ARABIC_PREFIXES = (
    "ABD", "ABDUL", "ABDEL", "ABDOU", "ABOU", "ABU", "ACHOUR", "ADEL", "AHMED",
    "AISSA", "AKHTAR", "ALI", "AMINE", "AMIR", "AMIRA", "AMMAR", "ANAS", "ANISSA",
    "ASMA", "AYOUB", "AZIZ", "BACHIR", "BADR", "BAHA", "BAKR", "BARAK", "BELAID",
    "BELKACEM", "BELLAH", "BEN", "BENA", "BENI", "BENM", "BENN", "BENZ", "BILAL",
    "BOUAB", "BOUAL", "BOUAZ", "BOUCH", "BOUD", "BOUDF", "BOUDI", "BOUFR", "BOUH",
    "BOUKH", "BOUL", "BOUM", "BOUN", "BOUR", "BOUS", "BOUT", "BOUZ",
    "CHAKIB", "CHERIF", "DAOUD", "DJAM", "DJEB", "DJEL", "DJEM",
    "EL ", "ESSAID", "FADEL", "FAHD", "FAIZ", "FARID", "FARIDA", "FATHI", "FATIH",
    "FATIMA", "FATIHA", "FAYC", "FOUD", "GHANI", "GHAZ", "HABIB", "HACEN", "HACH",
    "HADA", "HADJ", "HAFID", "HAKIM", "HALIM", "HAMADI", "HAMID", "HAMZA", "HANA",
    "HASAN", "HASNA", "HASSAN", "HICHAM", "HOCINE", "HOUDA", "HOUSSA", "HUSSEIN",
    "IBRAH", "IDRISS", "ILHAM", "ILYAS", "IMAD", "IMAN", "ISMAIL", "JAMAL", "JAMIL",
    "KADER", "KADIR", "KAMAL", "KAMEL", "KARIM", "KARIMA", "KENZA", "KHADIJA",
    "KHALED", "KHALID", "KHALIL", "KHEIR", "LAARBI", "LAHC", "LAHM", "LAKD",
    "LAKHD", "LAMIA", "LARBI", "LATIF", "LEILA", "LYES",
    "MAAMAR", "MABROUK", "MADANI", "MAHDI", "MAHM", "MALIK", "MALIKA", "MANEL",
    "MANSOUR", "MAOUCH", "MARIAM", "MAROU", "MBAREK", "MEBARK", "MEKKI", "MERAD",
    "MESSAOUD", "MILOUD", "MOHAM", "MOKHTAR", "MOSTAFA", "MOUHA", "MOUNI", "MOUSS",
    "MOURAD", "MOUSTAFA", "MUSTAPHA",
    "NABIL", "NADIA", "NADIM", "NADIR", "NAIMA", "NAJIB", "NASSER", "NASSIM",
    "NAWEL", "NIZAR", "NORA", "NOURD", "NOURE",
    "OMAR", "OTHMAN", "OUALI", "OUMAY", "RACHID", "RACHIDA", "RADIA", "RAHIM",
    "SAID", "SAIDA", "SALAH", "SALIM", "SALIMA", "SAMIR", "SAMIRA", "SEDDIK",
    "SLIMAN", "SOFIAN", "SOUHAIL", "SOUHA", "TAHAR", "TAHER", "TAREK", "TOUFIK",
    "WAHID", "WALID", "YACIN", "YAHIA", "YAMIN", "YASSER", "YASSIN", "YOUCEF",
    "YOUNES", "YOUSS", "ZAHRA", "ZAID", "ZAKARI", "ZHOR", "ZIAD", "ZINEB", "ZOHRA",
    "ZOUAOUI", "ZOULIKHA",
)


def _name_filter(name_type: str) -> str:
    """Return SQL WHERE clause for name type filtering."""
    if name_type == "ARABE":
        clauses = " OR ".join(
            f"UPPER(nom) LIKE '{p}%' OR UPPER(prenom) LIKE '{p}%'"
            for p in ARABIC_PREFIXES
        )
        return f"({clauses})"
    elif name_type == "FRANCAIS":
        clauses = " AND ".join(
            f"UPPER(nom) NOT LIKE '{p}%' AND UPPER(prenom) NOT LIKE '{p}%'"
            for p in ARABIC_PREFIXES
        )
        return f"({clauses})"
    return "1=1"


def get_leads_count(region: str = "ALL", name_type: str = "ALL") -> int:
    conn = get_connection()
    where = f"{_region_filter(region)} AND {_name_filter(name_type)}"
    cursor = conn.execute(f"SELECT COUNT(*) FROM clients WHERE {where}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_leads(region: str = "ALL", batch_size: int = 100, name_type: str = "ALL") -> list:
    conn = get_connection()
    where = f"{_region_filter(region)} AND {_name_filter(name_type)}"
    cursor = conn.execute(
        f"SELECT * FROM clients WHERE {where} ORDER BY nom, prenom LIMIT ?",
        (batch_size,)
    )
    results = cursor.fetchall()
    conn.close()
    return results


def clear_db():
    conn = get_connection()
    conn.execute("DELETE FROM clients")
    conn.commit()
    conn.close()
