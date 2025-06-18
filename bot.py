import logging
import os
import nest_asyncio
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

# Логгирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Этапы диалога
ASK_NAME, ASK_CONTACT, ASK_ABOUT = range(3)

# Кнопки везде
inline_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
    [InlineKeyboardButton("🔄 В начало", callback_data="start_over")]
])

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Команда /start и начало диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Клиент", "Соискатель"]]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=inline_markup
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Как вас зовут?", reply_markup=inline_markup)
    return ASK_CONTACT

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Как с вами связаться? (email, телефон, никнейм)", reply_markup=inline_markup)
    return ASK_ABOUT

async def ask_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text
    await update.message.reply_text("Расскажите немного о себе и своём запросе:", reply_markup=inline_markup)
    return ConversationHandler.END

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["about"] = update.message.text
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("about", "")
    ])
    await update.message.reply_text(
        "Спасибо! Мы свяжемся с вами.\n\nНажмите \"В начало\" или перейдите на сайт:",
        reply_markup=inline_markup
    )
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    return await start(query, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.", reply_markup=inline_markup)
    return ConversationHandler.END

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_about)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.TEXT, save_and_thank)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart, pattern="^start_over$"))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
