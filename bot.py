import os
import re
import json
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from database import init_db, search_by_phone, insert_client, get_client_count, clear_db, normalize_phone

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token — replace with your bot token from @BotFather
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8655347243:AAGVhDRjsi3oGNMeBUIIJ1YG5-MeC1btjHg")

# Regex to detect a French phone number in a message
PHONE_REGEX = re.compile(r"(?:\+33|0033|0)\s*[1-9](?:[\s.\-]?\d{2}){4}")


def format_client(client) -> str:
    """Format a client record into a nice Telegram message."""
    # Format date of birth (remove time part if present)
    dob = client["date_naissance"]
    if dob and "T" in dob:
        dob = dob.split("T")[0]

    msg = f"\U0001F4C4 *Fiche trouv\u00e9e*\n\n"
    msg += f"\U0001F464 *Infos personnelles*\n"
    msg += f"\u2022 *Nom :* `{client['nom']}`\n"
    msg += f"\u2022 *Pr\u00e9nom :* `{client['prenom']}`\n"

    dob_display = dob if (dob and dob.strip() and dob != "N/A") else "N/A"
    age_display = client["age"] if (client["age"] and int(client["age"]) > 0) else "N/A"
    msg += f"\u2022 *Date de naissance :* `{dob_display}`\n"
    msg += f"\u2022 *\u00c2ge :* `{age_display}`\n"

    if client["email"]:
        msg += f"\u2022 \U0001F4E7 *Email :* `{client['email']}`\n"
    msg += f"\u2022 \U0001F4F1 *T\u00e9l\u00e9phone :* `{client['telephone']}`\n"

    if client["adresse"]:
        msg += f"\u2022 \U0001F3E0 *Adresse :* `{client['adresse']}`\n"
    if client["code_postal"]:
        msg += f"\u2022 \U0001F4EE *Code postal :* `{client['code_postal']}`\n"
    if client["ville"]:
        msg += f"\u2022 \U0001F3D9\uFE0F *Ville :* `{client['ville']}`\n"

    msg += f"\n\U0001F4B3 *Infos bancaires*\n"
    if client["iban"]:
        msg += f"\u2022 *IBAN :* `{client['iban']}`\n"
    if client["bic"]:
        msg += f"\u2022 *BIC :* `{client['bic']}`\n"

    return msg


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_client_count()
    await update.message.reply_text(
        f"\U0001F916 *Bot Fiches Clients*\n\n"
        f"\U0001F4CA Base de donn\u00e9es : *{count}* fiches\n\n"
        f"*Commandes :*\n"
        f"/start \u2014 Afficher ce message\n"
        f"/stats \u2014 Nombre de fiches en base\n"
        f"/clear \u2014 Vider la base de donn\u00e9es\n\n"
        f"*Utilisation :*\n"
        f"\u2022 Collez un num\u00e9ro de t\u00e9l\u00e9phone \u2192 fiche client\n"
        f"\u2022 Envoyez un fichier JSON \u2192 import des fiches",
        parse_mode="Markdown",
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_client_count()
    await update.message.reply_text(
        f"\U0001F4CA *{count}* fiches en base de donn\u00e9es.",
        parse_mode="Markdown",
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_db()
    await update.message.reply_text(
        "\U0001F5D1\uFE0F Base de donn\u00e9es vid\u00e9e.",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — look for phone numbers."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Try to find a phone number in the message
    match = PHONE_REGEX.search(text)
    if not match:
        # Also try if the whole message is just digits (like 0675215403)
        cleaned = text.replace(" ", "").replace(".", "").replace("-", "")
        if re.match(r"^(?:\+33|0033|0)[1-9]\d{8}$", cleaned):
            phone = cleaned
        else:
            return  # Not a phone number, ignore
    else:
        phone = match.group()

    phone = normalize_phone(phone)
    results = search_by_phone(phone)

    if not results:
        await update.message.reply_text(
            f"\u274C Aucune fiche trouv\u00e9e pour `{phone}`",
            parse_mode="Markdown",
        )
        return

    for client in results:
        await update.message.reply_text(
            format_client(client),
            parse_mode="Markdown",
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle JSON file uploads to import clients."""
    if not update.message or not update.message.document:
        return

    doc = update.message.document
    if not doc.file_name.endswith(".json"):
        await update.message.reply_text("\u26A0\uFE0F Envoyez un fichier `.json`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("\u23F3 Import en cours...")

    try:
        file = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        data = json.loads(file_bytes.decode("utf-8"))

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            await status_msg.edit_text("\u274C Format JSON invalide. Attendu : une liste de fiches.")
            return

        count = 0
        for entry in data:
            # Support nested or flat structure
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
        await status_msg.edit_text(
            f"\u2705 *{count}* fiches import\u00e9es !\n\U0001F4CA Total en base : *{total}*",
            parse_mode="Markdown",
        )

    except json.JSONDecodeError:
        await status_msg.edit_text("\u274C Erreur : fichier JSON invalide.")
    except Exception as e:
        logger.error(f"Import error: {e}")
        await status_msg.edit_text(f"\u274C Erreur lors de l'import : `{e}`", parse_mode="Markdown")


def main():
    if BOT_TOKEN == "YOUR_TOKEN_HERE":
        print("=" * 50)
        print("ERREUR : Configure ton token Telegram !")
        print("1. Va sur Telegram, cherche @BotFather")
        print("2. Envoie /newbot et suis les instructions")
        print("3. Copie le token")
        print("4. Lance avec : TELEGRAM_BOT_TOKEN=ton_token python bot.py")
        print("=" * 50)
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\U0001F916 Bot d\u00e9marr\u00e9 ! En attente de messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
