import logging
import os
import nest_asyncio
import asyncio

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
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

# Этапы диалога
ASK_ROLE, ASK_NAME, ASK_CONTACT, ASK_ABOUT = range(4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Клавиатура с ссылкой и возвратом
def base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
        [InlineKeyboardButton("🔁 В начало", callback_data="restart")]
    ])

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Клиент", "Соискатель"]]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_ROLE

# Роль: Клиент / Соискатель / Свой вариант
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Как вас зовут?", reply_markup=base_keyboard())
    return ASK_NAME

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, контакт (телефон или Telegram):", reply_markup=base_keyboard())
    return ASK_CONTACT

async def ask_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text
    role = context.user_data.get("role", "").lower()
    if role == "клиент":
        sheet.append_row([context.user_data["role"], context.user_data["name"], context.user_data["contact"], ""])
        await update.message.reply_text("Спасибо! Мы с вами свяжемся.", reply_markup=base_keyboard())
        return ConversationHandler.END
    else:
        await update.message.reply_text("Расскажите немного о себе и что вы ищете:", reply_markup=base_keyboard())
        return ASK_ABOUT

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["about"] = update.message.text
    sheet.append_row([
        context.user_data["role"],
        context.user_data["name"],
        context.user_data["contact"],
        context.user_data["about"]
    ])
    await update.message.reply_text("Спасибо! Мы изучим вашу информацию и свяжемся при возможности.", reply_markup=base_keyboard())
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Начнём сначала.")
    return await start(query, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.", reply_markup=base_keyboard())
    return ConversationHandler.END

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_about)],
            ASK_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("🔁 В начало"), start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & filters.UpdateType.CALLBACK_QUERY, restart))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
