"""
Script pour importer un fichier JSON dans la base de données.
Usage : python import_json.py fichier.json
"""
import json
import sys
from database import init_db, insert_client, get_client_count


def import_json_file(filepath: str):
    init_db()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        print("Erreur : le JSON doit contenir une liste de fiches ou une seule fiche.")
        sys.exit(1)

    count = 0
    for entry in data:
        client = {
            "nom": entry.get("nom", entry.get("Nom", "")),
            "prenom": entry.get("prenom", entry.get("Prenom", entry.get("prénom", ""))),
            "date_naissance": entry.get("date_naissance", entry.get("dateNaissance", entry.get("date_de_naissance", ""))),
            "age": entry.get("age", entry.get("Age", 0)),
            "email": entry.get("email", entry.get("Email", entry.get("mail", ""))),
            "telephone": entry.get("telephone", entry.get("Telephone", entry.get("tel", entry.get("téléphone", "")))),
            "adresse": entry.get("adresse", entry.get("Adresse", entry.get("address", ""))),
            "code_postal": entry.get("code_postal", entry.get("codePostal", entry.get("cp", ""))),
            "ville": entry.get("ville", entry.get("Ville", entry.get("city", ""))),
            "iban": entry.get("iban", entry.get("IBAN", "")),
            "bic": entry.get("bic", entry.get("BIC", "")),
        }
        insert_client(client)
        count += 1

    total = get_client_count()
    print(f"✅ {count} fiches importées !")
    print(f"📊 Total en base : {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python import_json.py <fichier.json>")
        sys.exit(1)
    import_json_file(sys.argv[1])
