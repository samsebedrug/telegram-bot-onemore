import os
import logging
import asyncio
import nest_asyncio

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
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

# Кнопки
def base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F310 На сайт", url="https://onemorepro.com")],
        [InlineKeyboardButton("\U0001F501 В начало", callback_data="restart")]
    ])

def role_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['row'] = ["", "", "", "", ""]
    context.user_data['stage'] = 'choose_role'

    await update.message.reply_text(
        "Добро пожаловать в One More Production!\n\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "\ud83d\udc47 Выберите, кто вы:",
        reply_markup=role_keyboard()
    )

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['row'] = ["", "", "", "", ""]
    context.user_data['stage'] = 'choose_role'

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Добро пожаловать в One More Production!\n\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "\ud83d\udc47 Выберите, кто вы:",
        reply_markup=role_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    stage = context.user_data.get('stage')

    if data == "restart":
        return await restart(update, context)

    if stage == "choose_role" and data in ("client", "applicant", "other"):
        context.user_data['row'][0] = data
        context.user_data['stage'] = "get_name"
        await query.edit_message_text("Как вас зовут или какую компанию вы представляете?", reply_markup=base_keyboard())

    elif stage == "get_contact" and data == "skip":
        context.user_data['stage'] = "get_position"
        await query.edit_message_text("Какова ваша роль в производстве?", reply_markup=base_keyboard())

    elif stage == "get_position":
        context.user_data['row'][3] = data
        context.user_data['stage'] = "get_details"
        await query.edit_message_text("Расскажите подробнее о вашем запросе:", reply_markup=base_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    stage = context.user_data.get("stage")

    if stage == "get_name":
        context.user_data['row'][1] = text
        context.user_data['stage'] = "get_contact"
        await update.message.reply_text("Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).", reply_markup=base_keyboard())

    elif stage == "get_contact":
        context.user_data['row'][2] = text
        role = context.user_data['row'][0]
        context.user_data['stage'] = "get_position"

        if role == "client":
            keyboard = [
                [InlineKeyboardButton("Реклама", callback_data="ad")],
                [InlineKeyboardButton("Документальное кино", callback_data="doc")],
                [InlineKeyboardButton("Клип", callback_data="clip")],
                [InlineKeyboardButton("Digital-контент", callback_data="digital")]
            ]
            await update.message.reply_text("Что вас интересует?", reply_markup=InlineKeyboardMarkup(keyboard + base_keyboard().inline_keyboard))
        else:
            await update.message.reply_text("Какова ваша роль в производстве?", reply_markup=base_keyboard())

    elif stage == "get_position":
        context.user_data['row'][3] = text
        context.user_data['stage'] = "get_details"
        await update.message.reply_text("Расскажите подробнее о вашем запросе:", reply_markup=base_keyboard())

    elif stage == "get_details":
        context.user_data['row'][4] = text
        sheet.append_row(context.user_data['row'])
        context.user_data.clear()
        await update.message.reply_text("Спасибо! Мы получили ваши данные и скоро с вами свяжемся.", reply_markup=base_keyboard())

async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()

if __name__ == "__main__":
    asyncio.run(main())
