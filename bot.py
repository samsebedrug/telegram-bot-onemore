import logging
import os
import nest_asyncio
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# States
CHOOSE_ROLE, GET_NAME, GET_CONTACT, GET_ABOUT, GET_REQUEST = range(5)

SITE_BUTTON = InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")
RESTART_BUTTON = InlineKeyboardButton("🔄 В начало", callback_data="restart")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client"), InlineKeyboardButton("Соискатель", callback_data="jobseeker")],
        [SITE_BUTTON],
    ]
    context.user_data.clear()
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_ROLE

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Перезапуск...")
        return await start(update.callback_query, context)
    return await start(update, context)

async def handle_role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data["role"] = role
    await query.edit_message_text("Как вас зовут?", reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]))
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, контакт для связи:", reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]))
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text
    await update.message.reply_text("Расскажите немного о себе:", reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]))
    return GET_ABOUT

async def get_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["about"] = update.message.text
    await update.message.reply_text("И теперь, в чём ваш запрос?", reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]))
    return GET_REQUEST

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["request"] = update.message.text
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("about", ""),
        context.user_data.get("request", ""),
    ])
    await update.message.reply_text(
        "Спасибо! Мы получили вашу информацию.\nНажмите /start, чтобы начать сначала.",
        reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]),
    )
    return ConversationHandler.END

async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я пока не понимаю это сообщение. Нажмите /start, чтобы начать сначала.",
        reply_markup=InlineKeyboardMarkup([[SITE_BUTTON, RESTART_BUTTON]]),
    )

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(handle_role_choice, pattern="^(client|jobseeker)$")],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(handle_role_choice, pattern="^(client|jobseeker)$")],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            GET_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_about)],
            GET_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
