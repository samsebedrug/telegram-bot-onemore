import logging
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CallbackContext, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters, ConversationHandler)
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("onemore_form_data").sheet1

# States
ROLE, NAME, CONTACT, INFO, REQUEST = range(5)

MAIN_MENU_BUTTONS = [
    [InlineKeyboardButton("🔁 В начало", callback_data="start")],
    [InlineKeyboardButton("🌐 На сайт", url="https://onemore.video")]
]

def get_main_keyboard():
    return InlineKeyboardMarkup(MAIN_MENU_BUTTONS)

def save_to_sheet(user_data):
    values = [
        user_data.get("role", ""),
        user_data.get("name", ""),
        user_data.get("contact", ""),
        user_data.get("info", ""),
        user_data.get("request", "")
    ]
    sheet.append_row(values)

def reset_user_data(context: CallbackContext, chat_id):
    context.user_data.clear()
    context.user_data["chat_id"] = chat_id

async def start(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    reset_user_data(context, chat_id)

    keyboard = [
        [InlineKeyboardButton("🧑 Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("🏢 Клиент", callback_data="client")],
        [InlineKeyboardButton("🤝 Другое", callback_data="other")]
    ]

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Привет! Выберите, кто вы:",
            reply_markup=InlineKeyboardMarkup(keyboard + MAIN_MENU_BUTTONS)
        )
    else:
        await update.message.reply_text(
            "Привет! Выберите, кто вы:",
            reply_markup=InlineKeyboardMarkup(keyboard + MAIN_MENU_BUTTONS)
        )
    return ROLE

async def handle_role(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data["role"] = role

    if role == "client":
        await query.edit_message_text("Как вас зовут или какую компанию вы представляете?",
                                      reply_markup=get_main_keyboard())
    else:
        await query.edit_message_text("Как вас зовут?", reply_markup=get_main_keyboard())
    return NAME

async def handle_name(update: Update, context: CallbackContext) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Укажите, пожалуйста, ваш контакт (телеграм / почта / телефон):",
                                    reply_markup=get_main_keyboard())
    return CONTACT

async def handle_contact(update: Update, context: CallbackContext) -> int:
    context.user_data["contact"] = update.message.text
    role = context.user_data.get("role")

    if role == "applicant":
        await update.message.reply_text("Какая у вас роль в производстве?",
                                        reply_markup=get_main_keyboard())
        return INFO
    elif role == "client":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="Реклама")],
            [InlineKeyboardButton("Документальное кино", callback_data="Документальное кино")],
            [InlineKeyboardButton("Клип", callback_data="Клип")],
            [InlineKeyboardButton("Digital-контент", callback_data="Digital-контент")],
        ]
        await update.message.reply_text(
            "Выберите интересующий формат или напишите свой:",
            reply_markup=InlineKeyboardMarkup(keyboard + MAIN_MENU_BUTTONS)
        )
        return INFO
    else:
        await update.message.reply_text("Расскажите подробнее о вашем запросе:",
                                        reply_markup=get_main_keyboard())
        return REQUEST

async def handle_info(update: Update, context: CallbackContext) -> int:
    context.user_data["info"] = update.message.text
    await update.message.reply_text("Расскажите подробнее о вашем запросе:",
                                    reply_markup=get_main_keyboard())
    return REQUEST

async def handle_info_button(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["info"] = query.data
    await query.edit_message_text("Расскажите подробнее о вашем запросе:",
                                  reply_markup=get_main_keyboard())
    return REQUEST

async def handle_request(update: Update, context: CallbackContext) -> int:
    context.user_data["request"] = update.message.text
    save_to_sheet(context.user_data)
    await update.message.reply_text(
        "Спасибо! Мы свяжемся с вами в ближайшее время.", reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def restart(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    return await start(update, context)

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(start, pattern="^start$")],
        states={
            ROLE: [CallbackQueryHandler(handle_role)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact)],
            INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_info),
                CallbackQueryHandler(handle_info_button)
            ],
            REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request)]
        },
        fallbacks=[CommandHandler("start", start), CallbackQueryHandler(start, pattern="^start$")],
        per_message=True,
    )

    app.add_handler(conv_handler)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

if __name__ == "__main__":
    main()
