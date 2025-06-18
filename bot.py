import os
import logging
import asyncio

from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Состояния
CHOOSE_ROLE, GET_NAME, GET_CONTACT, GET_POSITION, GET_DETAILS = range(5)

# Кнопки
def base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F310 На сайт", url="https://onemorepro.com")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ]

    welcome_text = (
        "Добро пожаловать в One More Production!\n\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n"
        "С нами просто и точно захочется one more.\n\n"
        "Воспользуйтесь нашим telegram-ботом или напишите нам на почту weare@onemorepro.com\n\n"
        "\U0001F447 Выберите, кто вы:"
    )

    await update.effective_message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    raw_role = query.data
    role_map = {"client": "клиент", "applicant": "соискатель", "other": "другое"}
    role = role_map.get(raw_role, raw_role)
    context.user_data["role"] = raw_role
    context.user_data["row"] = [role, "", "", "", ""]
    await query.edit_message_text("Как вас зовут или какую компанию вы представляете?", reply_markup=base_keyboard())
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    context.user_data["row"][1] = name
    await update.message.reply_text("Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).", reply_markup=base_keyboard())
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.text
    context.user_data["row"][2] = contact
    role = context.user_data["role"]

    if role in ["applicant", "other"]:
        await update.message.reply_text("Какова ваша роль в производстве?", reply_markup=base_keyboard())
    else:
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="ad")],
            [InlineKeyboardButton("Документальное кино", callback_data="doc")],
            [InlineKeyboardButton("Клип", callback_data="clip")],
            [InlineKeyboardButton("Digital-контент", callback_data="digital")]
        ]
        await update.message.reply_text(
            "Что вас интересует?",
            reply_markup=InlineKeyboardMarkup(keyboard + list(base_keyboard().inline_keyboard))
        )
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        position = update.callback_query.data
        await update.callback_query.edit_message_text("Расскажите подробнее о вашем запросе:", reply_markup=base_keyboard())
    else:
        position = update.message.text
        await update.message.reply_text("Расскажите подробнее о вашем запросе:", reply_markup=base_keyboard())

    context.user_data["row"][3] = position
    return GET_DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text
    context.user_data["row"][4] = details
    sheet.append_row(context.user_data["row"])

    await update.message.reply_text(
        "Спасибо! Мы получили ваши данные и скоро с вами свяжемся.\n\nДля повторного запуска бота введите команду /start",
        reply_markup=base_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            GET_POSITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_position),
                CallbackQueryHandler(get_position)
            ],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        per_message=False,
    )

    app.add_handler(conv_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

if __name__ == "__main__":
    asyncio.run(main())
