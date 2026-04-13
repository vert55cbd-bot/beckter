"""
Import SG emoji-format TXT files.
Format:
🔍 NOM PRENOM
🎂 DD/MM/YYYY
📬 ADRESSE, CODE_POSTAL VILLE
📲 TELEPHONE
📝 EMAIL
💳 IBAN
──────────── (separator)
"""
import re
import sys
from datetime import datetime
from database import init_db, insert_client, get_client_count


def parse_address(addr: str):
    """Parse '65 RUE BRETEUIL, 13006 MARSEILLE' into adresse, code_postal, ville."""
    # Try to split on the last comma
    parts = addr.rsplit(",", 1)
    if len(parts) == 2:
        adresse = parts[0].strip()
        rest = parts[1].strip()
        # Extract code postal (5 digits) and ville
        match = re.match(r"(\d{5})\s+(.*)", rest)
        if match:
            return adresse, match.group(1), match.group(2).strip()
        return adresse, "", rest
    # No comma — try to find code postal anywhere
    match = re.search(r"(\d{5})\s+(.*)", addr)
    if match:
        adresse = addr[:match.start()].strip().rstrip(",")
        return adresse, match.group(1), match.group(2).strip()
    return addr, "", ""


def parse_name(name_line: str):
    """Split 'NOM PRENOM' — first word = nom, rest = prenom."""
    parts = name_line.strip().split()
    if len(parts) >= 2:
        return parts[0].upper(), " ".join(parts[1:]).upper()
    return name_line.upper(), ""


def import_sg_emoji(filepath: str):
    init_db()

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by separator lines (──────)
    blocks = re.split(r"─{5,}", content)

    count = 0
    errors = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        data = {}
        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("🔍"):
                nom, prenom = parse_name(line[1:].strip())
                data["nom"] = nom
                data["prenom"] = prenom

            elif line.startswith("🎂"):
                val = line[1:].strip()
                data["date_naissance"] = val
                try:
                    dob = datetime.strptime(val, "%d/%m/%Y")
                    today = datetime.now()
                    data["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except:
                    data["age"] = 0

            elif line.startswith("📬"):
                adresse, cp, ville = parse_address(line[1:].strip())
                data["adresse"] = adresse
                data["code_postal"] = cp
                data["ville"] = ville

            elif line.startswith("📲"):
                data["telephone"] = line[1:].strip()

            elif line.startswith("📝"):
                data["email"] = line[1:].strip()

            elif line.startswith("💳"):
                data["iban"] = line[1:].strip()

        # Skip header lines or blocks without phone
        if "telephone" not in data or not data["telephone"]:
            if "nom" in data:
                errors += 1
            continue

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
            "bic": "",
        }
        insert_client(client)
        count += 1

    total = get_client_count()
    print(f"✅ {count} fiches importées depuis {filepath}")
    if errors:
        print(f"⚠️  {errors} blocs ignorés (pas de téléphone)")
    print(f"📊 Total en base : {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python import_sg_emoji.py <fichier1.txt> [fichier2.txt] ...")
        sys.exit(1)
    for filepath in sys.argv[1:]:
        import_sg_emoji(filepath)
