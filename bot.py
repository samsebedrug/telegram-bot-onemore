import logging
import os
import asyncio
import nest_asyncio

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Apply patch to allow nested event loops (especially in some hosting environments)
nest_asyncio.apply()

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# States
ASK_NAME, ASK_ROLE = range(2)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Привет! Как тебя зовут?")
    return ASK_NAME

# Ask for role
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    context.user_data["name"] = user_name
    reply_keyboard = [["Заказчик", "Исполнитель"]]
    await update.message.reply_text(
        f"Приятно познакомиться, {user_name}! Кто ты?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return ASK_ROLE

# Finish conversation
async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    role = update.message.text
    name = context.user_data["name"]
    sheet.append_row([name, role])
    await update.message.reply_text(f"Спасибо, {name}! Ты записан как {role}.")
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

# Main entry
async def main():
    if not BOT_TOKEN:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
