"""
Import all bank folders from Desktop/Banques (except Societe Generale*).
Format: prenom|nom|dateNaissance|adresse|codePostal|ville|tel|email|iban|bic
The folder name is used as the bank name (BIC code or friendly name).
"""
import os
import sys
from datetime import datetime
from database import init_db, bulk_insert_clients, get_client_count, classify_name

BANQUES_DIR = "/Users/user/Desktop/Banques"
SKIP_PREFIXES = ("Societe Generale",)


def parse_bank_name(folder_name: str) -> str:
    """Map folder name to a short bank label."""
    name = folder_name.upper()
    # Known mappings
    if "CIC" in name or name.startswith("CMCIFRPP"):
        return "CIC"
    if "BNP" in name or name.startswith("BNPA"):
        return "BNP"
    if "LCL" in name or name.startswith("CRLYFRPP"):
        return "LCL"
    if "CREDIT AGRICOLE" in name or name.startswith("AGRI"):
        return "CA"
    if "CAISSE D'EPARGNE" in name or "CAISSE D EPARGNE" in name or name.startswith("CEPA"):
        return "CE"
    if "BANQUE POSTALE" in name or name.startswith("PSSTFRPP"):
        return "BP"
    if "CREDIT MUTUEL" in name or name.startswith("CMCIFR"):
        return "CM"
    if "HSBC" in name or name.startswith("CCFRFRPP"):
        return "HSBC"
    if "BOURSORAMA" in name or name.startswith("BOUS"):
        return "BOURSO"
    if "AXA" in name:
        return "AXA"
    if "ING" in name:
        return "ING"
    if "FORTUNEO" in name:
        return "FORTUNEO"
    # Use folder name as-is (truncated)
    return folder_name[:20]


def import_folder(folder_path: str, bank_name: str) -> int:
    """Import clients.txt from a bank folder. Returns count imported."""
    clients_file = os.path.join(folder_path, "clients.txt")
    if not os.path.exists(clients_file):
        return 0

    clients = []
    with open(clients_file, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline()  # Skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 10:
                continue

            prenom, nom, dob, adresse, cp, ville, tel, email, iban, bic = parts[:10]

            # Calculate age
            age = 0
            if dob:
                try:
                    d = datetime.strptime(dob, "%d/%m/%Y")
                    today = datetime.now()
                    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
                except:
                    pass

            name_type = classify_name(nom, prenom)

            clients.append({
                "nom": nom.strip(),
                "prenom": prenom.strip(),
                "date_naissance": dob.strip(),
                "age": age,
                "email": email.strip(),
                "telephone": tel.strip(),
                "adresse": adresse.strip(),
                "code_postal": cp.strip(),
                "ville": ville.strip(),
                "iban": iban.strip(),
                "bic": bic.strip(),
                "banque": bank_name,
                "name_type": name_type,
            })

    if clients:
        # Bulk insert in chunks of 5000
        for i in range(0, len(clients), 5000):
            chunk = clients[i:i+5000]
            bulk_insert_clients(chunk)

    return len(clients)


def main():
    init_db()
    before = get_client_count()
    print(f"Base avant import : {before:,}")

    folders = sorted(os.listdir(BANQUES_DIR))
    total_imported = 0
    banks_imported = 0

    for folder in folders:
        if folder.startswith("."):
            continue
        if any(folder.startswith(skip) for skip in SKIP_PREFIXES):
            print(f"⏭  Skip : {folder}")
            continue

        folder_path = os.path.join(BANQUES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        bank_name = parse_bank_name(folder)
        count = import_folder(folder_path, bank_name)
        if count > 0:
            total_imported += count
            banks_imported += 1
            print(f"✅ {bank_name} ({folder}) : {count:,} fiches")

    after = get_client_count()
    print(f"\n{'='*50}")
    print(f"Import terminé : {total_imported:,} fiches de {banks_imported} banques")
    print(f"Total en base : {after:,}")


if __name__ == "__main__":
    main()
