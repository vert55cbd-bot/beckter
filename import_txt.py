"""
Import pipe-delimited TXT file into the database.
Format: telephone|nom_complet|date_naissance|email|adresse|ville (code_postal)|iban|bic
"""
import re
import sys
from database import init_db, insert_client, get_client_count, normalize_phone


def parse_ville_cp(ville_cp: str):
    """Parse 'VILLE (CODE_POSTAL)' into separate ville and code_postal."""
    match = re.match(r"^(.*?)\s*\((\d{5})\)\s*$", ville_cp)
    if match:
        return match.group(1).strip(), match.group(2)
    return ville_cp.strip(), ""


def parse_nom_complet(nom_complet: str):
    """Split full name into prenom and nom (last word = nom, rest = prenom)."""
    parts = nom_complet.strip().split()
    if len(parts) >= 2:
        # First word(s) = prenom, last word = nom
        prenom = " ".join(parts[:-1])
        nom = parts[-1]
        return nom, prenom
    return nom_complet, ""


def import_txt_file(filepath: str):
    init_db()

    count = 0
    errors = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            parts = line.split("|")
            if len(parts) < 7:
                print(f"Ligne {line_num} ignorée (format invalide): {line[:50]}...")
                errors += 1
                continue

            telephone = parts[0].strip()
            nom_complet = parts[1].strip()
            date_naissance = parts[2].strip()
            email = parts[3].strip()
            adresse = parts[4].strip()
            ville_cp = parts[5].strip()
            iban = parts[6].strip()
            bic = parts[7].strip() if len(parts) > 7 else ""

            nom, prenom = parse_nom_complet(nom_complet)
            ville, code_postal = parse_ville_cp(ville_cp)

            # Handle N/A for date
            if date_naissance == "N/A":
                date_naissance = ""

            client = {
                "nom": nom,
                "prenom": prenom,
                "date_naissance": date_naissance,
                "age": 0,
                "email": email,
                "telephone": telephone,
                "adresse": adresse,
                "code_postal": code_postal,
                "ville": ville,
                "iban": iban,
                "bic": bic,
            }
            insert_client(client)
            count += 1

    total = get_client_count()
    print(f"✅ {count} fiches importées !")
    if errors:
        print(f"⚠️  {errors} lignes ignorées (format invalide)")
    print(f"📊 Total en base : {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python import_txt.py <fichier.txt>")
        sys.exit(1)
    import_txt_file(sys.argv[1])
