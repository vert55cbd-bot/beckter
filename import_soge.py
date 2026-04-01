"""
Import SOGE pipe-delimited TXT file.
Format: civilite|prenom|nom|date_naissance|lieu_naissance|code_postal|ville|adresse|email|telephone|bic|iban
"""
import sys
from datetime import datetime
from database import init_db, insert_client, get_client_count


def import_soge_file(filepath: str):
    init_db()

    count = 0
    errors = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            parts = line.split("|")
            if len(parts) < 10:
                print(f"Ligne {line_num} ignorée (format invalide)")
                errors += 1
                continue

            # civilite|prenom|nom|date_naissance|lieu_naissance|cp|ville|adresse|email|telephone|bic|iban
            prenom = parts[1].strip().upper()
            nom = parts[2].strip().upper()
            date_naissance = parts[3].strip()
            code_postal = parts[5].strip()
            ville = parts[6].strip()
            adresse = parts[7].strip()
            email = parts[8].strip()
            telephone = parts[9].strip()
            bic = parts[10].strip() if len(parts) > 10 else ""
            iban = parts[11].strip() if len(parts) > 11 else ""

            # Calculate age from date of birth
            age = 0
            dob_display = date_naissance
            if date_naissance and date_naissance != "N/A":
                try:
                    dob = datetime.strptime(date_naissance, "%Y-%m-%d")
                    today = datetime.now()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    dob_display = dob.strftime("%d/%m/%Y")
                except:
                    pass

            client = {
                "nom": nom,
                "prenom": prenom,
                "date_naissance": dob_display,
                "age": age,
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
    print(f"✅ {count} fiches importées depuis {filepath}")
    if errors:
        print(f"⚠️  {errors} lignes ignorées")
    print(f"📊 Total en base : {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python import_soge.py <fichier.txt>")
        sys.exit(1)
    for filepath in sys.argv[1:]:
        import_soge_file(filepath)
