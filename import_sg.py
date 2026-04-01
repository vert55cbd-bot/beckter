"""
Import SG-format TXT files (emoji-labeled, separated by ===).
Format:
🔹 Contact X by : @...
👤 Nom : NOM PRENOM
📅 Date de naissance : DD/MM/YYYY
📧 Email : ...
🏠 Adresse : ...
🏷 Code postal : ...
🏙 Ville : ...
🌍 Pays : ...
📞 Téléphone : ...
💳 IBAN : ...
🏦 BIC : ...
🏦 BANQUE : ...
📭 BASE : ...
"""
import re
import sys
from datetime import datetime
from database import init_db, insert_client, get_client_count


def parse_sg_file(filepath: str):
    init_db()

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by separator line
    blocks = re.split(r"={5,}", content)

    count = 0
    errors = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        data = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse each emoji-labeled field
            if "Nom :" in line or "Nom:" in line:
                val = line.split(":", 1)[1].strip()
                # Split: last word(s) as prenom, first word as nom
                parts = val.split()
                if len(parts) >= 2:
                    data["nom"] = parts[0]
                    data["prenom"] = " ".join(parts[1:])
                else:
                    data["nom"] = val
                    data["prenom"] = ""

            elif "Date de naissance" in line:
                val = line.split(":", 1)[1].strip()
                data["date_naissance"] = val
                # Calculate age
                try:
                    dob = datetime.strptime(val, "%d/%m/%Y")
                    today = datetime.now()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    data["age"] = age
                except:
                    data["age"] = 0

            elif "Email" in line:
                val = line.split(":", 1)[1].strip()
                if val.lower() in ("non renseigné", "non renseigne", "n/a", ""):
                    data["email"] = ""
                else:
                    data["email"] = val

            elif "Adresse" in line:
                val = line.split(":", 1)[1].strip()
                data["adresse"] = val

            elif "Code postal" in line:
                val = line.split(":", 1)[1].strip()
                data["code_postal"] = val

            elif "Ville" in line and "Pays" not in line:
                val = line.split(":", 1)[1].strip()
                data["ville"] = val

            elif "phone" in line.lower() or "Téléphone" in line:
                val = line.split(":", 1)[1].strip()
                data["telephone"] = val

            elif "IBAN" in line:
                val = line.split(":", 1)[1].strip()
                data["iban"] = val

            elif "BIC" in line:
                val = line.split(":", 1)[1].strip()
                data["bic"] = val

        # Only insert if we have at least a phone number
        if "telephone" in data and data["telephone"]:
            client = {
                "nom": data.get("nom", ""),
                "prenom": data.get("prenom", ""),
                "date_naissance": data.get("date_naissance", ""),
                "age": data.get("age", 0),
                "email": data.get("email", ""),
                "telephone": data.get("telephone", ""),
                "adresse": data.get("adresse", ""),
                "code_postal": data.get("code_postal", ""),
                "ville": data.get("ville", ""),
                "iban": data.get("iban", ""),
                "bic": data.get("bic", ""),
            }
            insert_client(client)
            count += 1
        else:
            errors += 1

    total = get_client_count()
    print(f"✅ {count} fiches importées depuis {filepath}")
    if errors:
        print(f"⚠️  {errors} blocs ignorés")
    print(f"📊 Total en base : {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python import_sg.py <fichier1.txt> [fichier2.txt] ...")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        parse_sg_file(filepath)
