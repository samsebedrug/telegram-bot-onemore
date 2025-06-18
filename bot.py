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

# Apply patch for nested event loop issues
nest_asyncio.apply()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
ASK_NAME, ASK_ROLE = range(2)

# Load credentials and authorize Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Привет! Как тебя зовут?")
    return ASK_NAME

async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    reply_keyboard = [["Дизайнер", "Креативщик", "Аккаунт"]]
    await update.message.reply_text(
        "Приятно познакомиться, {}!\nКакая у тебя роль?".format(context.user_data["name"]),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return ASK_ROLE

async def save_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    role = update.message.text
    name = context.user_data["name"]
    sheet.append_row([name, role])
    await update.message.reply_text("Спасибо! Данные сохранены.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Main entry point
async def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Переменная окружения TELEGRAM_TOKEN не установлена.")

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_data)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
