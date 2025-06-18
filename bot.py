import logging
import os
import nest_asyncio
import asyncio

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
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

# Ступени диалога
(
    CHOOSING_STATUS,
    ASK_NAME,
    ASK_CONTACT,
    ASK_ROLE_OR_TYPE,
    ASK_DESCRIPTION,
) = range(5)

# Таблица
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 В начало", callback_data="restart")],
            [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
        ]
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["data"] = ["", "", "", "", ""]
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")],
    ]
    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "👇 Выберите, кто вы:",
        reply_markup=InlineKeyboardMarkup(keyboard + get_main_keyboard().inline_keyboard),
    )
    return CHOOSING_STATUS

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "restart":
        context.user_data.clear()
        return await start(update, context)

    context.user_data["data"][0] = {"client": "Клиент", "applicant": "Соискатель", "other": "Другое"}.get(choice, "")
    await query.edit_message_text("Как вас зовут или какую компанию вы представляете?", reply_markup=get_main_keyboard())
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["data"][1] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram)", reply_markup=get_main_keyboard())
    return ASK_CONTACT

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["data"][2] = update.message.text
    role = context.user_data["data"][0]

    if role == "Соискатель":
        await update.message.reply_text("Какую роль в производстве вы ищете?", reply_markup=get_main_keyboard())
    elif role == "Клиент":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="ads")],
            [InlineKeyboardButton("Документальное кино", callback_data="doc")],
            [InlineKeyboardButton("Клип", callback_data="clip")],
            [InlineKeyboardButton("Digital-контент", callback_data="digital")],
        ]
        await update.message.reply_text("Выберите интересующий тип проекта или напишите свой вариант:", reply_markup=InlineKeyboardMarkup(keyboard + get_main_keyboard().inline_keyboard))
    else:
        await update.message.reply_text("Расскажите немного о себе", reply_markup=get_main_keyboard())

    return ASK_ROLE_OR_TYPE

async def ask_role_or_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        text = update.callback_query.data
        mapping = {
            "ads": "Реклама",
            "doc": "Документальное кино",
            "clip": "Клип",
            "digital": "Digital-контент"
        }
        context.user_data["data"][3] = mapping.get(text, text)
        await update.callback_query.edit_message_text("Расскажите подробнее о вашем запросе", reply_markup=get_main_keyboard())
    else:
        context.user_data["data"][3] = update.message.text
        await update.message.reply_text("Расскажите подробнее о вашем запросе", reply_markup=get_main_keyboard())
    return ASK_DESCRIPTION

async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["data"][4] = update.message.text
    sheet.append_row(context.user_data["data"])
    await update.message.reply_text("Спасибо! Мы скоро с вами свяжемся.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def fallback_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог завершён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_STATUS: [CallbackQueryHandler(button_handler)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_ROLE_OR_TYPE: [
                CallbackQueryHandler(ask_role_or_type),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role_or_type),
            ],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
        },
        fallbacks=[
            CommandHandler("start", fallback_restart),
            CallbackQueryHandler(fallback_restart, pattern="^restart$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_restart),
        ],
    )

    app.add_handler(conv_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

# Render fix
nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
