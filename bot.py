import logging
import os
import nest_asyncio
import asyncio

from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Состояния
ASK_ROLE, ASK_NAME, ASK_CONTACT, ASK_INFO = range(4)

# Логгирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [KeyboardButton("Клиент"), KeyboardButton("Соискатель")],
    ]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )
    return ASK_ROLE

# Ответ на выбор роли
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Как вас зовут?")
    return ASK_NAME

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Пожалуйста, укажите ваш контакт (телефон, email, Telegram и т.п.):")
    return ASK_CONTACT

async def ask_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text
    role = context.user_data["role"].lower()

    if role == "клиент":
        keyboard = [
            ["Реклама", "Клип"],
            ["Документальный проект", "Другое"]
        ]
        await update.message.reply_text(
            "Что вас интересует?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
    else:
        await update.message.reply_text("Напишите пару слов о себе и ваш запрос.")
    return ASK_INFO

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    role = context.user_data.get("role", "")
    name = context.user_data.get("name", "")
    contact = context.user_data.get("contact", "")
    info = update.message.text

    sheet.append_row([role, name, contact, info])

    keyboard = [
        [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
        [KeyboardButton("🔁 В начало")]
    ]

    await update.message.reply_text(
        "Спасибо! Мы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Основной запуск
async def main():
    token = os.getenv("BOT_TOKEN")
    logger.info("BOT_TOKEN detected: %s", token[:10] + "..." if token else "None")
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_info)],
            ASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)],
        },
        fallbacks=[
            CommandHandler("start", restart),
            MessageHandler(filters.Regex("^(🔁 В начало)$"), restart),
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(conv_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
