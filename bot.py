import logging
import os
import nest_asyncio
import asyncio

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния диалога
ASK_NAME, ASK_ROLE = range(2)

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Привет! Как тебя зовут?")
    return ASK_NAME

# Получение имени
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    reply_keyboard = [["Клиент", "Коуч"]]
    await update.message.reply_text(
        "Выбери свою роль:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return ASK_ROLE

# Получение роли
async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = context.user_data.get("name")
    role = update.message.text
    sheet.append_row([name, role])
    await update.message.reply_text("Спасибо! Данные сохранены.")
    return ConversationHandler.END

# Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Основной запуск через webhook
async def main():
    bot_token = os.getenv("BOT_TOKEN")
    port = int(os.getenv("PORT", "10000"))
    webhook_url = f"{os.getenv('RENDER_EXTERNAL_URL')}/webhook"

    application = Application.builder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск webhook
    await application.bot.set_webhook(webhook_url)
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=webhook_url,
    )

nest_asyncio.apply()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
