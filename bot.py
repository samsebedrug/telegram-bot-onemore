import logging
import os
import nest_asyncio
import asyncio

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Conversation states
ASK_ROLE, ASK_NAME, ASK_CONTACT, ASK_DESCRIPTION = range(4)

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Universal inline keyboard
universal_inline = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com"),
        InlineKeyboardButton("🔁 В начало", callback_data="restart")
    ]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Клиент", "Соискатель"]]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Как вас зовут?", reply_markup=universal_inline)
    return ASK_NAME

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Пожалуйста, укажите ваш контакт (телефон, email, соцсети)", reply_markup=universal_inline)
    return ASK_CONTACT

async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text

    if context.user_data["role"].lower() == "клиент":
        reply_keyboard = [["Реклама", "Клип"], ["Документалка", "Другое"]]
        await update.message.reply_text(
            "Что вас интересует?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        )
    else:
        await update.message.reply_text(
            "Расскажите о себе и чём вы заинтересованы:", reply_markup=universal_inline
        )

    return ASK_DESCRIPTION

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text

    # Save to Google Sheet
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("description", "")
    ])

    await update.message.reply_text(
        "Спасибо! Мы получили вашу информацию. Свяжемся с вами в ближайшее время.\n\nЕсли хотите начать заново, нажмите 🔁 В начало.",
        reply_markup=universal_inline
    )
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await start(query, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог завершен. Вы всегда можете начать заново, введя /start.", reply_markup=universal_inline)
    return ConversationHandler.END

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
