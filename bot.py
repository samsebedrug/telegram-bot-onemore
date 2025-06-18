import os
import logging
import nest_asyncio
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("One More Bot").sheet1

# States
CHOOSE_ROLE, ASK_NAME, ASK_CONTACT, ASK_INFO = range(4)

# Inline buttons
inline_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔁 В начало", callback_data="restart")],
    [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")]
])

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Клиент", "Соискатель"]]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return CHOOSE_ROLE

# Role selection
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = update.message.text.strip()
    context.user_data["role"] = role
    await update.message.reply_text("Как вас зовут?", reply_markup=inline_buttons)
    return ASK_NAME

# Ask for contact
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Как с вами связаться?", reply_markup=inline_buttons)
    return ASK_CONTACT

# Ask for info or send choices
async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text.strip()
    role = context.user_data["role"].lower()

    if role == "клиент":
        keyboard = [["Хочу рекламу"], ["Интересует продакшн"], ["Нужна консультация"]]
        await update.message.reply_text("Что вас интересует?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
        return ASK_INFO
    else:
        await update.message.reply_text("Расскажите немного о себе и вашем запросе.", reply_markup=inline_buttons)
        return ASK_INFO

# Final step
async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["info"] = update.message.text.strip()
    data = [
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("info", "")
    ]
    sheet.append_row(data)
    await update.message.reply_text("Спасибо! Мы свяжемся с вами как можно скорее.", reply_markup=inline_buttons)
    return ConversationHandler.END

# Restart handler
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.delete()
        await start(update.callback_query, context)
    return CHOOSE_ROLE

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Main
async def main():
    token = os.environ.get("BOT_TOKEN")
    logger.info("BOT_TOKEN detected: %s", token[:10] + "...")

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))

    await app.bot.delete_webhook(drop_pending_updates=True)

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
