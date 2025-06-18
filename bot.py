import logging
import os
import asyncio
import nest_asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Telegram conversation states
CHOOSE_ROLE, CLIENT_NAME, CLIENT_TYPE, CLIENT_DETAILS, APPLICANT_NAME, APPLICANT_CONTACT, APPLICANT_ABOUT, APPLICANT_REQUEST = range(8)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keyboards
start_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Клиент", callback_data="client"),
        InlineKeyboardButton("Соискатель", callback_data="applicant"),
    ],
    [InlineKeyboardButton("Другое", callback_data="other")],
])

nav_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("На сайт", url="https://onemorepro.com")],
    [InlineKeyboardButton("В начало", callback_data="restart")],
])

content_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Реклама", callback_data="ad"),
        InlineKeyboardButton("Документальное кино", callback_data="doc"),
    ],
    [
        InlineKeyboardButton("Клип", callback_data="clip"),
        InlineKeyboardButton("Digital-контент", callback_data="digital"),
    ],
    [InlineKeyboardButton("Другое", callback_data="other_content")],
])

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.message:
        await update.message.reply_text(
            "Добро пожаловать в One More Production!\n"
            "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
            "С нами просто. И точно захочется one more.\n\n"
            "👇 Выберите, кто вы (или нажмите 'Другое'):",
            reply_markup=start_keyboard,
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Добро пожаловать в One More Production!\n"
            "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
            "С нами просто. И точно захочется one more.\n\n"
            "👇 Выберите, кто вы (или нажмите 'Другое'):",
            reply_markup=start_keyboard,
        )
    return CHOOSE_ROLE

async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data.clear()
    context.user_data["role"] = "Другое" if role == "other" else ("Клиент" if role == "client" else "Соискатель")

    if role == "client":
        await query.edit_message_text("Как вас зовут или какую компанию вы представляете?", reply_markup=nav_keyboard)
        return CLIENT_NAME
    else:
        await query.edit_message_text("Как вас зовут?", reply_markup=nav_keyboard)
        return APPLICANT_NAME

# CLIENT
async def client_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Что именно вас интересует?", reply_markup=content_keyboard)
    return CLIENT_TYPE

async def client_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["content_type"] = query.data if query.data != "other_content" else "Другое"
    await query.edit_message_text("Расскажите подробнее о вашем запросе:", reply_markup=nav_keyboard)
    return CLIENT_DETAILS

async def client_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["details"] = update.message.text
    sheet.append_row([
        context.user_data.get("name", ""),
        context.user_data.get("role", ""),
        context.user_data.get("content_type", ""),
        context.user_data.get("details", ""),
        "",
        ""
    ])
    await update.message.reply_text("Спасибо! Мы с вами свяжемся.", reply_markup=nav_keyboard)
    return ConversationHandler.END

# APPLICANT / OTHER
async def applicant_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, ваш контакт (email, Telegram или телефон):", reply_markup=nav_keyboard)
    return APPLICANT_CONTACT

async def applicant_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text
    await update.message.reply_text("Расскажите немного о себе:", reply_markup=nav_keyboard)
    return APPLICANT_ABOUT

async def applicant_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["about"] = update.message.text
    await update.message.reply_text("Какой у вас запрос?", reply_markup=nav_keyboard)
    return APPLICANT_REQUEST

async def applicant_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["request"] = update.message.text
    sheet.append_row([
        context.user_data.get("name", ""),
        context.user_data.get("role", ""),
        "",
        "",
        context.user_data.get("about", ""),
        context.user_data.get("request", "")
    ])
    await update.message.reply_text("Спасибо! Мы с вами свяжемся.", reply_markup=nav_keyboard)
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        return await start(update, context)
    return ConversationHandler.END

async def main():
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(role_chosen)],
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_name)],
            CLIENT_TYPE: [CallbackQueryHandler(client_type)],
            CLIENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_details)],
            APPLICANT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, applicant_name)],
            APPLICANT_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, applicant_contact)],
            APPLICANT_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, applicant_about)],
            APPLICANT_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, applicant_request)],
        },
        fallbacks=[CallbackQueryHandler(restart, pattern="^restart$")],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    application.add_handler(CommandHandler("start", start))

    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
    )

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
