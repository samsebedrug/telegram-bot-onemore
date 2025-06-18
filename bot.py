import logging
import os
import asyncio
import nest_asyncio

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
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

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
sheet = gspread.authorize(credentials).open("One More Bot").sheet1

# Этапы
ASK_ROLE, ASK_NAME, ASK_CONTACT, ASK_ABOUT = range(4)

# Кнопки
main_keyboard = ReplyKeyboardMarkup(
    [["Клиент", "Соискатель"]], resize_keyboard=True, one_time_keyboard=True
)
site_button = InlineKeyboardButton("На сайт", url="https://onemorepro.com")
restart_button = InlineKeyboardButton("В начало", callback_data="start_over")
inline_markup = InlineKeyboardMarkup([[site_button], [restart_button]])


# Хэндлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=main_keyboard,
    )
    return ASK_ROLE


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Как вас зовут?")
    return ASK_NAME


async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Как с вами связаться?")
    return ASK_CONTACT


async def ask_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text
    await update.message.reply_text("Расскажите немного о себе или о вашем запросе.")
    return ASK_ABOUT


async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["about"] = update.message.text
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("about", "")
    ])
    await update.message.reply_text(
        "Спасибо! Мы получили вашу информацию и свяжемся с вами.",
        reply_markup=inline_markup,
    )
    return ConversationHandler.END


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.delete()
        await start(update.callback_query, context)
    return ASK_ROLE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=inline_markup)
    return ConversationHandler.END


# Основная функция
async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

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
    app.add_handler(CallbackQueryHandler(restart, pattern="start_over"))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )


# Для Render
nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
