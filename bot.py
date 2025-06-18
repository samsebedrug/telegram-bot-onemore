import logging
import os
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Spreadsheet setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Stages
CHOOSE_ROLE, ASK_NAME, ASK_PROJECT_TYPE, ASK_DETAILS, ASK_NAME_APPLICANT, ASK_CONTACT_APPLICANT, ASK_INFO_APPLICANT = range(7)

# Universal buttons
main_menu_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
    [InlineKeyboardButton("🔁 В начало", callback_data="restart")],
])

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [["Клиент", "Соискатель"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы (или напишите свой вариант):",
        reply_markup=reply_markup
    )
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    role = update.message.text.lower()
    context.user_data['role'] = role

    if role == "клиент":
        await update.message.reply_text("Как вас зовут или какую компанию вы представляете?", reply_markup=main_menu_markup)
        return ASK_NAME
    else:
        await update.message.reply_text("Как вас зовут?", reply_markup=main_menu_markup)
        return ASK_NAME_APPLICANT

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    keyboard = [["Реклама", "Документальное кино"], ["Клип", "Digital-контент"], ["Свой вариант"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Что вас интересует?", reply_markup=reply_markup)
    return ASK_PROJECT_TYPE

async def ask_project_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['project_type'] = update.message.text
    await update.message.reply_text("Расскажите подробнее о вашем запросе", reply_markup=main_menu_markup)
    return ASK_DETAILS

async def ask_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['details'] = update.message.text
    sheet.append_row([
        context.user_data.get("role"),
        context.user_data.get("name"),
        context.user_data.get("project_type"),
        context.user_data.get("details")
    ])
    await update.message.reply_text("Спасибо! Мы с вами свяжемся.", reply_markup=main_menu_markup)
    return ConversationHandler.END

async def ask_name_applicant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, контакт для связи", reply_markup=main_menu_markup)
    return ASK_CONTACT_APPLICANT

async def ask_contact_applicant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['contact'] = update.message.text
    await update.message.reply_text("Расскажите немного о себе", reply_markup=main_menu_markup)
    return ASK_INFO_APPLICANT

async def ask_info_applicant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['info'] = update.message.text
    await update.message.reply_text("И о вашем запросе", reply_markup=main_menu_markup)
    return ASK_DETAILS

async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    return await start(query, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменён.", reply_markup=main_menu_markup)
    return ConversationHandler.END

async def main() -> None:
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PROJECT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_project_type)],
            ASK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_details)],
            ASK_NAME_APPLICANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name_applicant)],
            ASK_CONTACT_APPLICANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact_applicant)],
            ASK_INFO_APPLICANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_info_applicant)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart_callback, pattern="^restart$"))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
