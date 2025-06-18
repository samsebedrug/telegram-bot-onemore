import logging
import os
import gspread
import nest_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler, filters)

nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("TelegramBotData").sheet1

# Состояния
(SELECTING_STATUS, ENTER_NAME, ENTER_CONTACT, ROLE_OR_SERVICE,
 ENTER_DESCRIPTION) = range(5)

# Клавиатуры
main_keyboard = [
    [InlineKeyboardButton("Клиент", callback_data="Клиент")],
    [InlineKeyboardButton("Соискатель", callback_data="Соискатель")],
    [InlineKeyboardButton("Другое", callback_data="Другое")]
]

def get_main_keyboard():
    return InlineKeyboardMarkup(main_keyboard + [[
        InlineKeyboardButton("На сайт", url="https://onemore.video")
    ]])

def get_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("В начало", callback_data="start")],
        [InlineKeyboardButton("На сайт", url="https://onemore.video")]
    ])

def write_to_sheet(user_id, column_index, value):
    cell = sheet.find(str(user_id))
    if not cell:
        sheet.append_row([user_id] + [""] * (column_index - 1) + [value])
    else:
        row = cell.row
        sheet.update_cell(row, column_index + 1, value)

def start_new_row(user_id):
    sheet.append_row([user_id] + [""] * 5)

def clear_user_data(user_id):
    cell = sheet.find(str(user_id))
    if cell:
        row = cell.row
        sheet.delete_rows(row)
    start_new_row(user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    clear_user_data(user_id)

    if update.message:
        await update.message.reply_text(
            "Добро пожаловать! Выберите, кто вы:",
            reply_markup=get_main_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "Добро пожаловать! Выберите, кто вы:",
            reply_markup=get_main_keyboard()
        )

    return SELECTING_STATUS

async def select_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    status = query.data
    write_to_sheet(user_id, 1, status)
    await query.edit_message_text(
        "Как вас зовут или какую компанию вы представляете?",
        reply_markup=get_back_keyboard()
    )
    return ENTER_NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = update.message.text
    write_to_sheet(user_id, 2, name)
    await update.message.reply_text(
        "Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).",
        reply_markup=get_back_keyboard()
    )
    return ENTER_CONTACT

async def enter_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    contact = update.message.text
    write_to_sheet(user_id, 3, contact)

    cell = sheet.find(str(user_id))
    status = sheet.cell(cell.row, 2).value

    if status == "Клиент":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="Реклама")],
            [InlineKeyboardButton("Документальное кино", callback_data="Документальное кино")],
            [InlineKeyboardButton("Клип", callback_data="Клип")],
            [InlineKeyboardButton("Digital-контент", callback_data="Digital-контент")],
            [InlineKeyboardButton("Другое", callback_data="Другое")]
        ]
        await update.message.reply_text(
            "Что вас интересует? (или напишите свой вариант)",
            reply_markup=InlineKeyboardMarkup(keyboard + get_back_keyboard().inline_keyboard)
        )
    elif status == "Соискатель":
        await update.message.reply_text(
            "Какова ваша роль в производстве?",
            reply_markup=get_back_keyboard()
        )
    else:
        await update.message.reply_text(
            "Расскажите подробнее о вашем запросе:",
            reply_markup=get_back_keyboard()
        )
        return ENTER_DESCRIPTION

    return ROLE_OR_SERVICE

async def role_or_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if update.callback_query:
        await update.callback_query.answer()
        value = update.callback_query.data
        await update.callback_query.edit_message_text(
            "Расскажите подробнее о вашем запросе:",
            reply_markup=get_back_keyboard()
        )
    else:
        value = update.message.text
        await update.message.reply_text(
            "Расскажите подробнее о вашем запросе:",
            reply_markup=get_back_keyboard()
        )

    write_to_sheet(user_id, 4, value)
    return ENTER_DESCRIPTION

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    description = update.message.text
    write_to_sheet(user_id, 5, description)
    await update.message.reply_text(
        "Спасибо! Мы получили ваши данные и скоро с вами свяжемся.",
        reply_markup=get_back_keyboard()
    )
    return ConversationHandler.END

async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start, pattern="^start$")
        ],
        states={
            SELECTING_STATUS: [CallbackQueryHandler(select_status)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_contact)],
            ROLE_OR_SERVICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, role_or_service),
                CallbackQueryHandler(role_or_service)
            ],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
        },
        fallbacks=[],
        per_message=True,
    )

    app.add_handler(conv_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
