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
            bic TEXT,
            banque TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_telephone ON clients(telephone)")
    # Migration: add banque column if missing
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN banque TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.execute("CREATE INDEX IF NOT EXISTS idx_banque ON clients(banque)")
    # Migration: add name_type column if missing
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN name_type TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_type ON clients(name_type)")
    # Migration: add used column if missing
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN used INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_used ON clients(used)")
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
        INSERT INTO clients (nom, prenom, date_naissance, age, email, telephone, adresse, code_postal, ville, iban, bic, banque)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        data.get("banque", ""),
    ))
    conn.commit()
    conn.close()


def bulk_insert_clients(clients: list):
    """Insert many clients in a single transaction for performance."""
    conn = get_connection()
    conn.executemany("""
        INSERT INTO clients (nom, prenom, date_naissance, age, email, telephone, adresse, code_postal, ville, iban, bic, banque)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            c.get("nom", ""), c.get("prenom", ""), c.get("date_naissance", ""),
            c.get("age", 0), c.get("email", ""), normalize_phone(c.get("telephone", "")),
            c.get("adresse", ""), c.get("code_postal", ""), c.get("ville", ""),
            c.get("iban", ""), c.get("bic", ""), c.get("banque", ""),
        ) for c in clients
    ])
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
    if name_type in ("ARABE", "FRANCAIS"):
        return f"name_type = '{name_type}'"
    return "1=1"


def classify_name(nom: str, prenom: str) -> str:
    """Classify a name as ARABE or FRANCAIS."""
    # Clean and uppercase
    nom_clean = "".join(c for c in nom.upper() if c.isalpha() or c == " ").strip()
    prenom_clean = "".join(c for c in prenom.upper() if c.isalpha() or c == " ").strip()

    for name in (nom_clean, prenom_clean):
        if not name:
            continue
        for prefix in ARABIC_PREFIXES:
            if name.startswith(prefix):
                return "ARABE"
    return "FRANCAIS"


AGE_TRANCHES = {
    "1930-1960": ("1930", "1960"),
    "1960-1980": ("1960", "1980"),
    "1980-2000": ("1980", "2000"),
    "2000+": ("2000", "2026"),
}


def _age_filter(tranche: str) -> str:
    """Return SQL WHERE clause for birth year filtering (DD/MM/YYYY format)."""
    if tranche and tranche != "ALL" and tranche in AGE_TRANCHES:
        year_min, year_max = AGE_TRANCHES[tranche]
        return f"(SUBSTR(date_naissance, 7, 4) >= '{year_min}' AND SUBSTR(date_naissance, 7, 4) <= '{year_max}' AND date_naissance != '')"
    return "1=1"


def _banque_filter(banque: str) -> str:
    """Return SQL WHERE clause for bank filtering."""
    if banque and banque != "ALL":
        return f"banque = '{banque}'"
    return "1=1"


def get_available_banques() -> list:
    """Return list of (banque, count) tuples for all banks in DB."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT banque, COUNT(*) as cnt FROM clients WHERE banque != '' GROUP BY banque ORDER BY cnt DESC"
    )
    results = [(row["banque"], row["cnt"]) for row in cursor.fetchall()]
    conn.close()
    return results


def get_leads_count(region: str = "ALL", name_type: str = "ALL", banque: str = "ALL", tranche: str = "ALL") -> int:
    conn = get_connection()
    where = f"used = 0 AND {_banque_filter(banque)} AND {_region_filter(region)} AND {_name_filter(name_type)} AND {_age_filter(tranche)}"
    cursor = conn.execute(f"SELECT COUNT(*) FROM clients WHERE {where}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_leads(region: str = "ALL", batch_size: int = 100, name_type: str = "ALL", banque: str = "ALL", tranche: str = "ALL") -> list:
    conn = get_connection()
    where = f"used = 0 AND {_banque_filter(banque)} AND {_region_filter(region)} AND {_name_filter(name_type)} AND {_age_filter(tranche)}"
    cursor = conn.execute(
        f"SELECT * FROM clients WHERE {where} ORDER BY RANDOM() LIMIT ?",
        (batch_size,)
    )
    results = cursor.fetchall()
    # Mark as used
    if results:
        ids = [(row["id"],) for row in results]
        conn.executemany("UPDATE clients SET used = 1 WHERE id = ?", ids)
        conn.commit()
    conn.close()
    return results


def get_used_count() -> int:
    conn = get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM clients WHERE used = 1")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def reset_used():
    """Reset all leads back to available."""
    conn = get_connection()
    conn.execute("UPDATE clients SET used = 0")
    conn.commit()
    conn.close()


def clear_db():
    conn = get_connection()
    conn.execute("DELETE FROM clients")
    conn.commit()
    conn.close()
