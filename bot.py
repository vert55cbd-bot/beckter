import io
import os
import re
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from database import (
    init_db, search_by_phone, insert_client, get_client_count,
    clear_db, normalize_phone, get_leads, get_leads_count,
    get_available_banques, get_used_count, reset_used, get_banques_with_stock,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token — replace with your bot token from @BotFather
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8655347243:AAGVhDRjsi3oGNMeBUIIJ1YG5-MeC1btjHg")

# Regex to detect a French phone number in a message
PHONE_REGEX = re.compile(r"(?:\+33|0033|0)\s*[1-9](?:[\s.\-]?\d{2}){4}")


def format_client(client) -> str:
    """Format a client record into a premium Telegram message."""
    dob = client["date_naissance"]
    if dob and "T" in dob:
        dob = dob.split("T")[0]

    dob_display = dob if (dob and dob.strip() and dob != "N/A") else "N/A"
    age_display = client["age"] if (client["age"] and int(client["age"]) > 0) else "N/A"
    banque = client["banque"] if client["banque"] else "N/A"

    msg = (
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001F4CB *FICHE CLIENT*\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\U0001F464 *Identit\u00e9*\n"
        f"\u251C \U0001F4DD Nom : `{client['nom']}`\n"
        f"\u251C \U0001F4DD Pr\u00e9nom : `{client['prenom']}`\n"
        f"\u251C \U0001F382 N\u00e9(e) : `{dob_display}`\n"
        f"\u2514 \U0001F522 \u00c2ge : `{age_display}`\n\n"
        f"\U0001F4F2 *Contact*\n"
        f"\u251C \U0001F4F1 T\u00e9l : `{client['telephone']}`\n"
    )
    if client["email"]:
        msg += f"\u2514 \u2709\uFE0F Email : `{client['email']}`\n"
    else:
        msg = msg.rstrip("\n").replace("\u251C \U0001F4F1", "\u2514 \U0001F4F1") + "\n"

    msg += f"\n\U0001F4CD *Adresse*\n"
    if client["adresse"]:
        msg += f"\u251C \U0001F3E0 `{client['adresse']}`\n"
    if client["code_postal"] or client["ville"]:
        ville_str = f"{client['code_postal']} {client['ville']}".strip()
        msg += f"\u2514 \U0001F3D9\uFE0F `{ville_str}`\n"

    msg += (
        f"\n\U0001F4B3 *Bancaire*\n"
        f"\u251C \U0001F3E6 Banque : `{banque}`\n"
    )
    if client["iban"]:
        msg += f"\u251C \U0001F4B3 IBAN : `{client['iban']}`\n"
    if client["bic"]:
        msg += f"\u2514 \U0001F3F7\uFE0F BIC : `{client['bic']}`\n"
    else:
        # Close the last ├ with └
        msg = msg.rstrip("\n")
        if msg.endswith("`"):
            msg = msg.rsplit("\u251C", 1)
            msg = "\u2514".join(msg)
        msg += "\n"

    msg += f"\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"

    return msg


REGION_LABELS = {"IDF": "Ile-de-France", "HORS_IDF": "Hors IDF", "ALL": "Toute la France"}
NAME_LABELS = {"ARABE": "Noms arabes", "FRANCAIS": "Noms fran\u00e7ais", "ALL": "Tous"}
TRANCHE_LABELS = {"1930-1960": "1930-1960", "1960-1980": "1960-1980", "1980-2000": "1980-2000", "2000+": "2000+", "ALL": "Toutes"}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_client_count()
    used = get_used_count()
    dispo = count - used
    banques = get_available_banques()
    nb_banques = len(banques)

    await update.message.reply_text(
        f"\u200E\n"
        f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
        f"        \u26A1\uFE0F  *B E C K S*\n"
        f"        _Lead Manager Pro_\n\n"
        f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
        f"\U0001F7E2  *{dispo:,}*  leads disponibles\n"
        f"\U0001F534  *{used:,}*  leads utilis\u00e9es\n"
        f"\U0001F4BE  *{count:,}*  total en base\n\n"
        f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
        f"_Collez un num\u00e9ro \u2192 recherche instantan\u00e9e_\n",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u26A1 G\u00e9n\u00e9rer des Leads", callback_data="start_generate")],
            [
                InlineKeyboardButton("\U0001F4C8 Stats", callback_data="start_stats"),
                InlineKeyboardButton("\U0001F3E6 Banques", callback_data="start_banques"),
            ],
            [InlineKeyboardButton("\U0001F504 Reset leads utilis\u00e9es", callback_data="start_reset")],
        ]),
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_client_count()
    banques = get_available_banques()

    msg = (
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001F4C8 *STATISTIQUES*\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\U0001F4BE Total : *{count:,}* fiches\n\n"
    )
    if banques:
        msg += "\U0001F3E6 *Par banque :*\n"
        for b, c in banques:
            pct = round(c / count * 100, 1) if count else 0
            msg += f"\u251C `{b}` \u2500 *{c:,}* ({pct}%)\n"
        msg = msg[:-1]  # Remove last \n
        msg = msg.rsplit("\u251C", 1)
        msg = "\u2514".join(msg)  # Replace last ├ with └
        msg += "\n"

    idf = get_leads_count("IDF")
    hors = get_leads_count("HORS_IDF")
    msg += (
        f"\n\U0001F4CD *Par r\u00e9gion :*\n"
        f"\u251C \U0001F3D9 IDF \u2500 *{idf:,}*\n"
        f"\u2514 \U0001F30D Hors IDF \u2500 *{hors:,}*\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start menu button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_generate":
        # Trigger generate flow
        banques = get_available_banques()
        if not banques:
            await query.edit_message_text("\u274C Aucune banque en base.", parse_mode="Markdown")
            return

        # Filtrer : que les banques principales (>= 1000 fiches) et exclure codes BIC
        main_banques = [
            (b, c) for b, c in banques
            if c >= 1000 and not (len(b) == 11 and b.isupper() and b[-3:] == "XXX")
        ]

        keyboard = []
        row = []
        for banque, cnt in main_banques:
            icon = BANQUE_ICONS.get(banque, "\U0001F3E6")
            row.append(InlineKeyboardButton(f"{icon} {banque} ({cnt:,})", callback_data=f"gen_banque_{banque}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        total = get_client_count()
        keyboard.append([InlineKeyboardButton(f"\U0001F4CA Toutes ({total:,})", callback_data="gen_banque_ALL")])

        await query.edit_message_text(
            "\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            "\U0001F3E6 S\u00e9lectionnez la banque :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "start_stats":
        count = get_client_count()
        banques = get_available_banques()
        idf = get_leads_count("IDF")
        hors = get_leads_count("HORS_IDF")

        msg = (
            f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
            f"        \U0001F4C8  *STATISTIQUES*\n\n"
            f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
            f"\U0001F4BE  Total : *{count:,}* fiches\n\n"
        )
        if banques:
            for b, c in banques:
                pct = round(c / count * 100, 1) if count else 0
                msg += f"\U0001F3E6  `{b}` \u2014 *{c:,}* _{pct}%_\n"
            msg += "\n"
        msg += (
            f"\U0001F3D9  IDF \u2014 *{idf:,}*\n"
            f"\U0001F30D  Hors IDF \u2014 *{hors:,}*\n"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif data == "start_banques":
        banques = get_banques_with_stock()
        if not banques:
            await query.edit_message_text("\u274C Aucune banque en base.", parse_mode="Markdown")
            return

        msg = (
            f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
            f"        \U0001F3E6  *BANQUES*\n\n"
            f"\u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022 \u2022\n\n"
        )
        for b, total, dispo in banques:
            icon = BANQUE_ICONS.get(b, "\U0001F3E6")
            msg += (
                f"{icon}  *{b}*\n"
                f"      \U0001F4BE `{total:,}` total  |  \U0001F7E2 `{dispo:,}` dispo\n\n"
            )
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif data == "start_reset":
        reset_used()
        count = get_client_count()
        await query.edit_message_text(
            f"\U0001F504 *Leads r\u00e9initialis\u00e9es !*\n\n"
            f"\U0001F7E2 *{count:,}* leads de nouveau disponibles.",
            parse_mode="Markdown",
        )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_db()
    await update.message.reply_text(
        "\U0001F5D1\uFE0F Base de donn\u00e9es vid\u00e9e.",
        parse_mode="Markdown",
    )


BANQUE_ICONS = {
    "SG": "\U0001F534", "CIC": "\U0001F535", "BNP": "\U0001F7E2",
    "LCL": "\U0001F7E1", "CA": "\U0001F7E0", "CM": "\U0001F535",
    "Caisse Epargne": "\U0001F7E3", "BP": "\U0001F535",
    "Banque Populaire": "\U0001F535", "BOURSO": "\u26AB",
    "FORTUNEO": "\U0001F7E2", "BRED": "\U0001F534",
    "Revolut": "\u26AB", "HSBC": "\U0001F534", "AXA": "\U0001F535",
    "N26": "\u26AB", "Lydia": "\U0001F7E3", "Qonto": "\u26AB",
    "ING": "\U0001F7E0", "Bunq": "\U0001F7E2",
}


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bank selection for lead generation."""
    banques = get_available_banques()

    if not banques:
        await update.message.reply_text("\u274C Aucune banque en base.", parse_mode="Markdown")
        return

    # Filtrer : que les banques principales (>= 1000 fiches) et exclure codes BIC
    main_banques = [
        (b, c) for b, c in banques
        if c >= 1000 and not (len(b) == 11 and b.isupper() and b[-3:] == "XXX")
    ]

    keyboard = []
    row = []
    for banque, cnt in main_banques:
        icon = BANQUE_ICONS.get(banque, "\U0001F3E6")
        row.append(InlineKeyboardButton(f"{icon} {banque} ({cnt:,})", callback_data=f"gen_banque_{banque}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    total = get_client_count()
    keyboard.append([InlineKeyboardButton(f"\U0001F4CA Toutes ({total:,})", callback_data="gen_banque_ALL")])

    await update.message.reply_text(
        "\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
        "\U0001F3E6 S\u00e9lectionnez la banque :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_generate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses for /generate."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Step 1: Bank selected -> show region
    if data.startswith("gen_banque_"):
        banque = data.replace("gen_banque_", "")
        context.user_data["gen_banque"] = banque
        banque_label = banque if banque != "ALL" else "Toutes"

        idf_count = get_leads_count("IDF", "ALL", banque)
        hors_count = get_leads_count("HORS_IDF", "ALL", banque)
        all_count = get_leads_count("ALL", "ALL", banque)

        keyboard = [
            [
                InlineKeyboardButton(f"\U0001F3D9 IDF ({idf_count})", callback_data="gen_region_IDF"),
                InlineKeyboardButton(f"\U0001F30D Hors IDF ({hors_count})", callback_data="gen_region_HORS_IDF"),
            ],
            [
                InlineKeyboardButton(f"\U0001F1EB\U0001F1F7 Tous ({all_count})", callback_data="gen_region_ALL"),
            ],
        ]

        await query.edit_message_text(
            f"\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            f"\U0001F3E6 Banque : *{banque_label}*\n\n"
            f"\U0001F4CD S\u00e9lectionnez la r\u00e9gion :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # Step 2: Region selected -> show department filter
    elif data.startswith("gen_region_"):
        region = data.replace("gen_region_", "")
        context.user_data["gen_region"] = region
        banque = context.user_data.get("gen_banque", "ALL")
        banque_label = banque if banque != "ALL" else "Toutes"
        region_label = REGION_LABELS.get(region, region)

        keyboard = [
            [
                InlineKeyboardButton("\U0001F4CD 34 - H\u00e9rault", callback_data="gen_dept_34"),
                InlineKeyboardButton("\U0001F4CD 74 - Hte-Savoie", callback_data="gen_dept_74"),
            ],
            [
                InlineKeyboardButton("\U0001F4CD 84 - Vaucluse", callback_data="gen_dept_84"),
                InlineKeyboardButton("\U0001F4CD 34,74,84", callback_data="gen_dept_34,74,84"),
            ],
            [
                InlineKeyboardButton("\U0001F30D Tous d\u00e9partements", callback_data="gen_dept_ALL"),
            ],
        ]

        await query.edit_message_text(
            f"\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            f"\U0001F3E6 Banque : *{banque_label}*\n"
            f"\U0001F4CD R\u00e9gion : *{region_label}*\n\n"
            f"\U0001F4EC Filtrer par d\u00e9partement :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # Step 2b: Department selected -> show name filter
    elif data.startswith("gen_dept_"):
        depts = data.replace("gen_dept_", "")
        context.user_data["gen_depts"] = depts
        banque = context.user_data.get("gen_banque", "ALL")
        region = context.user_data.get("gen_region", "ALL")
        banque_label = banque if banque != "ALL" else "Toutes"
        region_label = REGION_LABELS.get(region, region)
        dept_label = depts if depts != "ALL" else "Tous"

        keyboard = [
            [
                InlineKeyboardButton("\U0001F1E9\U0001F1FF Arabe", callback_data="gen_name_ARABE"),
                InlineKeyboardButton("\U0001F1EB\U0001F1F7 Fran\u00e7ais", callback_data="gen_name_FRANCAIS"),
            ],
            [
                InlineKeyboardButton("\U0001F465 Tous", callback_data="gen_name_ALL"),
            ],
        ]

        await query.edit_message_text(
            f"\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            f"\U0001F3E6 Banque : *{banque_label}*\n"
            f"\U0001F4CD R\u00e9gion : *{region_label}*\n"
            f"\U0001F4EC D\u00e9pt : *{dept_label}*\n\n"
            f"\U0001F464 Filtrer par type de nom :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # Step 3: Name filter selected -> show age tranche
    elif data.startswith("gen_name_"):
        name_type = data.replace("gen_name_", "")
        context.user_data["gen_name"] = name_type
        banque = context.user_data.get("gen_banque", "ALL")
        region = context.user_data.get("gen_region", "ALL")
        depts = context.user_data.get("gen_depts", "ALL")
        banque_label = banque if banque != "ALL" else "Toutes"
        region_label = REGION_LABELS.get(region, region)
        dept_label = depts if depts != "ALL" else "Tous"
        name_label = NAME_LABELS.get(name_type, name_type)

        keyboard = [
            [
                InlineKeyboardButton("\U0001F9D3 1930-1960", callback_data="gen_age_1930-1960"),
                InlineKeyboardButton("\U0001F468 1960-1980", callback_data="gen_age_1960-1980"),
            ],
            [
                InlineKeyboardButton("\U0001F9D1 1980-2000", callback_data="gen_age_1980-2000"),
                InlineKeyboardButton("\U0001F466 2000+", callback_data="gen_age_2000+"),
            ],
            [
                InlineKeyboardButton("\U0001F465 Toutes", callback_data="gen_age_ALL"),
            ],
        ]

        await query.edit_message_text(
            f"\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            f"\U0001F3E6 Banque : *{banque_label}*\n"
            f"\U0001F4CD R\u00e9gion : *{region_label}*\n"
            f"\U0001F4EC D\u00e9pt : *{dept_label}*\n"
            f"\U0001F464 Noms : *{name_label}*\n\n"
            f"\U0001F4C5 Tranche d'\u00e2ge (ann\u00e9e de naissance) :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # Step 4: Age tranche selected -> show batch size
    elif data.startswith("gen_age_"):
        tranche = data.replace("gen_age_", "")
        context.user_data["gen_tranche"] = tranche
        banque = context.user_data.get("gen_banque", "ALL")
        region = context.user_data.get("gen_region", "ALL")
        depts = context.user_data.get("gen_depts", "ALL")
        name_type = context.user_data.get("gen_name", "ALL")
        banque_label = banque if banque != "ALL" else "Toutes"
        region_label = REGION_LABELS.get(region, region)
        dept_label = depts if depts != "ALL" else "Tous"
        name_label = NAME_LABELS.get(name_type, name_type)
        tranche_label = TRANCHE_LABELS.get(tranche, tranche)

        keyboard = [
            [
                InlineKeyboardButton("100", callback_data="gen_batch_100"),
                InlineKeyboardButton("500", callback_data="gen_batch_500"),
                InlineKeyboardButton("1000", callback_data="gen_batch_1000"),
            ],
        ]

        await query.edit_message_text(
            f"\U0001F4E6 *G\u00e9n\u00e9rateur de Leads*\n\n"
            f"\U0001F3E6 Banque : *{banque_label}*\n"
            f"\U0001F4CD R\u00e9gion : *{region_label}*\n"
            f"\U0001F4EC D\u00e9pt : *{dept_label}*\n"
            f"\U0001F464 Noms : *{name_label}*\n"
            f"\U0001F4C5 \u00c2ge : *{tranche_label}*\n\n"
            f"\U0001F522 Combien de leads ?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # Step 5: Batch size selected -> generate & send file
    elif data.startswith("gen_batch_"):
        batch_size = int(data.replace("gen_batch_", ""))
        banque = context.user_data.get("gen_banque", "ALL")
        region = context.user_data.get("gen_region", "ALL")
        depts = context.user_data.get("gen_depts", "ALL")
        name_type = context.user_data.get("gen_name", "ALL")
        tranche = context.user_data.get("gen_tranche", "ALL")
        banque_label = banque if banque != "ALL" else "Toutes"
        region_label = REGION_LABELS.get(region, region)
        dept_label = depts if depts != "ALL" else "Tous"
        name_label = NAME_LABELS.get(name_type, name_type)
        tranche_label = TRANCHE_LABELS.get(tranche, tranche)

        await query.edit_message_text(
            f"\u23F3 G\u00e9n\u00e9ration de *{batch_size}* leads...\n"
            f"\U0001F3E6 {banque_label} | \U0001F4CD {region_label} | \U0001F4EC {dept_label} | \U0001F464 {name_label} | \U0001F4C5 {tranche_label}",
            parse_mode="Markdown",
        )

        leads = get_leads(region, batch_size, name_type, banque, tranche, depts)

        if not leads:
            await query.edit_message_text(
                f"\u274C Aucun lead trouv\u00e9 pour *{region_label}* / *{name_label}*.",
                parse_mode="Markdown",
            )
            return

        # Build export file
        lines = [
            f"{'='*50}",
            f"  LEADS {banque_label} - {region_label} - Dept {dept_label} - {name_label} - {tranche_label}",
            f"  {len(leads)} fiches",
            f"{'='*50}\n",
        ]

        for i, c in enumerate(leads, 1):
            lines.append(f"{i}. {c['nom']} {c['prenom']}")
            if c["telephone"]:
                lines.append(f"   Tel: {c['telephone']}")
            if c["email"]:
                lines.append(f"   Email: {c['email']}")
            if c["date_naissance"]:
                lines.append(f"   N\u00e9(e): {c['date_naissance']}")
            addr_parts = []
            if c["adresse"]:
                addr_parts.append(c["adresse"])
            if c["code_postal"]:
                addr_parts.append(c["code_postal"])
            if c["ville"]:
                addr_parts.append(c["ville"])
            if addr_parts:
                lines.append(f"   Adresse: {', '.join(addr_parts)}")
            if c["iban"]:
                lines.append(f"   IBAN: {c['iban']}")
            lines.append(f"{'─'*40}")

        content = "\n".join(lines)
        file_buf = io.BytesIO(content.encode("utf-8"))
        banque_tag = banque.lower()
        region_tag = region.lower().replace("_", "-")
        name_tag = name_type.lower()
        file_buf.name = f"leads-{banque_tag}-{region_tag}-{name_tag}-{len(leads)}.txt"

        await query.edit_message_text(
            f"\u2705 *{len(leads)}* leads g\u00e9n\u00e9r\u00e9s\n"
            f"\U0001F3E6 {banque_label} | \U0001F4CD {region_label} | \U0001F464 {name_label}",
            parse_mode="Markdown",
        )
        await query.message.reply_document(
            document=file_buf,
            filename=file_buf.name,
            caption=f"\U0001F4C4 {len(leads)} leads {banque_label} \u2014 {region_label} \u2014 {name_label}",
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
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(handle_start_callback, pattern=r"^start_"))
    app.add_handler(CallbackQueryHandler(handle_generate_callback, pattern=r"^gen_"))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\U0001F916 Bot d\u00e9marr\u00e9 ! En attente de messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
