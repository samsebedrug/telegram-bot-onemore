import logging
import os
import asyncio

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler, filters)
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START, NAME, CONTACT, ROLE, DETAILS = range(5)

SHEET_COLUMNS = ["Статус", "Имя / Компания", "Контакт", "Роль / Интерес", "Описание запроса"]

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Заявки Telegram-бота").sheet1

user_data_rows = {}

site_button = InlineKeyboardButton("На сайт", url="https://onemore.media")
start_over_button = InlineKeyboardButton("В начало", callback_data="start_over")

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [site_button, start_over_button]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Я клиент", callback_data="client"),
        InlineKeyboardButton("Я соискатель", callback_data="seeker")
    ], [
        InlineKeyboardButton("Другое", callback_data="other")
    ]]
    await update.message.reply_text(
        "Привет! Кто вы?",
        reply_markup=InlineKeyboardMarkup(keyboard + list(get_main_keyboard().inline_keyboard))
    )
    return START

async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data_rows[user_id] = ["", "", "", "", ""]
    return await start(update, context)

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data_rows[user_id] = ["", "", "", "", ""]
    choice = query.data
    status = {
        "client": "Клиент",
        "seeker": "Соискатель",
        "other": "Другое"
    }.get(choice, "")
    user_data_rows[user_id][0] = status
    await query.edit_message_text(
        f"Как вас зовут или какую компанию вы представляете?",
        reply_markup=get_main_keyboard()
    )
    return NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_rows[user_id][1] = update.message.text
    await update.message.reply_text("Оставьте контакт для связи:", reply_markup=get_main_keyboard())
    return CONTACT

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_rows[user_id][2] = update.message.text
    role = user_data_rows[user_id][0]
    if role == "Клиент":
        keyboard = [[
            InlineKeyboardButton("Реклама", callback_data="Реклама"),
            InlineKeyboardButton("Документальное кино", callback_data="Документальное кино")
        ], [
            InlineKeyboardButton("Клип", callback_data="Клип"),
            InlineKeyboardButton("Digital-контент", callback_data="Digital-контент")
        ], [
            InlineKeyboardButton("Другое", callback_data="Другое")
        ]]
        await update.message.reply_text(
            "Что вас интересует?",
            reply_markup=InlineKeyboardMarkup(keyboard + list(get_main_keyboard().inline_keyboard))
        )
        return ROLE
    elif role == "Соискатель":
        await update.message.reply_text("Какая у вас роль в производстве?", reply_markup=get_main_keyboard())
        return ROLE
    else:
        await update.message.reply_text("Расскажите подробнее о вашем запросе:", reply_markup=get_main_keyboard())
        return DETAILS

async def handle_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message else update.callback_query.data
    user_data_rows[user_id][3] = text
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Расскажите подробнее о вашем запросе:")
    else:
        await update.message.reply_text("Расскажите подробнее о вашем запросе:")
    return DETAILS

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_rows[user_id][4] = update.message.text
    sheet.append_row(user_data_rows[user_id])
    await update.message.reply_text("Спасибо! Мы с вами свяжемся.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(start_over, pattern="^start_over$")],
        states={
            START: [CallbackQueryHandler(handle_choice)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role), CallbackQueryHandler(handle_role)],
            DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    application.add_handler(conv_handler)
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
