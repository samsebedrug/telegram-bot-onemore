import os
import logging
import asyncio
import nest_asyncio
from aiohttp import web

from telegram import (
    Update,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Состояния
(
    CHOOSE_ROLE,
    GET_NAME,
    GET_CONTACT,
    GET_POSITION,
    GET_DETAILS
) = range(5)

# Кнопки
def base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ]
    if update.message:
        await update.message.reply_photo(photo="https://onemorepro.com/images/11-1.jpg")
        await update.message.reply_text(
            "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 One More Production!\n\n"
            "\u041c\u044b \u0441\u043e\u0437\u0434\u0430\u0451\u043c \u0440\u0435\u043a\u043b\u0430\u043c\u0443, \u043a\u043b\u0438\u043f\u044b, \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u043e\u0435 \u043a\u0438\u043d\u043e \u0438 digital-\u043a\u043e\u043d\u0442\u0435\u043d\u0442.\n"
            "\u0421 \u043d\u0430\u043c\u0438 \u043f\u0440\u043e\u0441\u0442\u043e \u0438 \u0442\u043e\u0447\u043d\u043e \u0437\u0430\u0445\u043e\u0447\u0435\u0442\u0441\u044f one more.\n\n"
            "\ud83d\udc47 \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435, \u043a\u0442\u043e \u0432\u044b:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo="https://onemorepro.com/images/11-1.jpg")
        await update.callback_query.message.reply_text(
            "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    raw_role = query.data
    role_map = {"client": "клиент", "applicant": "соискатель", "other": "другое"}
    role = role_map.get(raw_role, raw_role)
    context.user_data["role"] = raw_role
    context.user_data["row"] = [role, "", "", "", ""]
    await query.message.reply_photo(photo="https://onemorepro.com/images/12.jpg")
    await query.edit_message_text("\u041a\u0430\u043a \u0432\u0430\u0441 \u0437\u043e\u0432\u0443\u0442 \u0438\u043b\u0438 \u043a\u0430\u043a\u0443\u044e \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u044e \u0432\u044b \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442\u0435?", reply_markup=base_keyboard())
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    context.user_data["name"] = name
    context.user_data["row"][1] = name
    await update.message.reply_photo(photo="https://onemorepro.com/images/13-1.jpg")
    await update.message.reply_text("\u041e\u0441\u0442\u0430\u0432\u044c\u0442\u0435, \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0430\u0448 \u043a\u043e\u043d\u0442\u0430кт...", reply_markup=base_keyboard())
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.text
    context.user_data["contact"] = contact
    context.user_data["row"][2] = contact
    role = context.user_data["role"]
    await update.message.reply_photo(photo="https://onemorepro.com/images/3.jpg")
    if role in ["applicant", "other"]:
        await update.message.reply_text("\u041a\u0430\u043a\u043e\u0432\u0430 \u0432\u0430\u0448\u0430 \u0440\u043e\u043b\u044c...", reply_markup=base_keyboard())
    elif role == "client":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="ad")],
            [InlineKeyboardButton("Документальное кино", callback_data="doc")],
            [InlineKeyboardButton("Клип", callback_data="clip")],
            [InlineKeyboardButton("Digital-контент", callback_data="digital")],
            [InlineKeyboardButton("Другое", callback_data="other")]
        ]
        await update.message.reply_text(
            "\u0427\u0442\u043e \u0432\u0430\u0441 \u0438\u043d\u0442\u0435\u0440\u0435\u0441\u0443\u0435\u0442?",
            reply_markup=InlineKeyboardMarkup(keyboard + list(base_keyboard().inline_keyboard))
        )
    else:
        return GET_DETAILS
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        position = update.callback_query.data
        await update.callback_query.message.reply_photo(photo="https://onemorepro.com/images/6.jpg")
        await update.callback_query.edit_message_text("\u0420\u0430\u0441\u0441\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435...", reply_markup=base_keyboard())
    else:
        position = update.message.text
        await update.message.reply_photo(photo="https://onemorepro.com/images/6.jpg")
        await update.message.reply_text("\u0420\u0430\u0441\u0441\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435...", reply_markup=base_keyboard())
    context.user_data["position"] = position
    context.user_data["row"][3] = position
    return GET_DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text
    context.user_data["details"] = details
    context.user_data["row"][4] = details
    sheet.append_row(context.user_data["row"])
    await update.message.reply_photo(photo="https://onemorepro.com/images/8.jpg")
    await update.message.reply_text(
        "\u0421\u043f\u0430\u0441\u0438\u0431\u043e! \u041c\u044b \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 \u0432\u0430\u0448\u0438 \u0434\u0430\u043d\u043d\u044b\u0435...",
        reply_markup=base_keyboard()
    )
    return ConversationHandler.END

# --- остальная часть кода (restart, cancel, healthz, main) --- остаётся без изменений.
