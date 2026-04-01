"""
Import SG pipe-delimited TXT files.
Format: prenom|nom|date_naissance|adresse|code_postal|ville|telephone|email|iban|bic
"""
import sys
from datetime import datetime
from database import init_db, insert_client, get_client_count


def import_sg_pipe(filepath: str):
    init_db()
    count = 0
    errors = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 8:
                errors += 1
                continue

            prenom = parts[0].strip().upper()
            nom = parts[1].strip().upper()
            date_naissance = parts[2].strip()
            adresse = parts[3].strip()
            code_postal = parts[4].strip()
            ville = parts[5].strip()
            telephone = parts[6].strip()
            email = parts[7].strip()
            iban = parts[8].strip() if len(parts) > 8 else ""
            bic = parts[9].strip() if len(parts) > 9 else ""

            age = 0
            if date_naissance and date_naissance != "N/A":
                try:
                    dob = datetime.strptime(date_naissance, "%d/%m/%Y")
                    today = datetime.now()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except:
                    pass

            client = {
                "nom": nom,
                "prenom": prenom,
                "date_naissance": date_naissance,
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
        print("Usage : python import_sg_pipe.py <fichier.txt>")
        sys.exit(1)
    for f in sys.argv[1:]:
        import_sg_pipe(f)
