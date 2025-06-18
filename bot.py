import logging
import os
import nest_asyncio
import asyncio

from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# States for the conversation
ASK_ROLE, ASK_NAME, ASK_CONTACT, ASK_INFO = range(4)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Helper keyboard generator

def get_main_keyboard(extra_buttons=None):
    buttons = []
    if extra_buttons:
        buttons.append(extra_buttons)
    buttons.append([
        InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com"),
        InlineKeyboardButton("🔁 В начало", callback_data="restart")
    ])
    return InlineKeyboardMarkup(buttons)

# Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text(
            "Добро пожаловать в One More Production!\n"
            "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
            "С нами просто. И точно захочется one more.\n\n"
            "👇 Выберите, кто вы (или напишите свой вариант):",
            reply_markup=get_main_keyboard([
                InlineKeyboardButton("Клиент", callback_data="client"),
                InlineKeyboardButton("Соискатель", callback_data="applicant")
            ])
        )
    return ASK_ROLE

async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data["role"] = role

    await query.edit_message_text("Как вас зовут?", reply_markup=get_main_keyboard())
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте, пожалуйста, ваш контакт:", reply_markup=get_main_keyboard())
    return ASK_CONTACT

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text
    role = context.user_data.get("role", "соискатель")

    if role == "client":
        options = [
            [InlineKeyboardButton("Реклама", callback_data="ad")],
            [InlineKeyboardButton("Клип", callback_data="music")],
            [InlineKeyboardButton("Документалка", callback_data="doc")],
            [InlineKeyboardButton("Другое", callback_data="other")]
        ]
        reply_markup = InlineKeyboardMarkup(options + get_main_keyboard().inline_keyboard)
        await update.message.reply_text("Что вы хотели бы снять?", reply_markup=reply_markup)
        return ASK_INFO
    else:
        await update.message.reply_text("Расскажите немного о себе и что вас интересует:", reply_markup=get_main_keyboard())
        return ASK_INFO

async def save_and_thank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.message.text
    context.user_data["info"] = data
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("info", "")
    ])
    await update.message.reply_text("Спасибо! Мы свяжемся с вами как можно скорее.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def handle_inline_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["info"] = query.data
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("info", "")
    ])
    await query.edit_message_text("Спасибо! Мы свяжемся с вами как можно скорее.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.delete()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name),
                MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, start),
                MessageHandler(filters.Regex("(?i)^(Клиент|Соискатель)$"), ask_name),
                MessageHandler(filters.ALL, ask_name),
                MessageHandler(filters.TEXT, ask_name),
                MessageHandler(filters.COMMAND, cancel),
                MessageHandler(filters.ALL, cancel),
                MessageHandler(filters.ALL, ask_name),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name),
                MessageHandler(filters.TEXT, ask_name),
                MessageHandler(filters.ALL, ask_name),
            ],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_thank)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.ALL, restart))
    app.add_handler(MessageHandler(filters.TEXT, restart))
    app.add_handler(MessageHandler(filters.COMMAND, cancel))
    app.add_handler(MessageHandler(filters.ALL, cancel))
    app.add_handler(MessageHandler(filters.ALL, ask_name))
    app.add_handler(MessageHandler(filters.ALL, ask_contact))
    app.add_handler(MessageHandler(filters.ALL, save_and_thank))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name))
    app.add_handler(MessageHandler(filters.ALL, ask_name))
    app.add_handler(MessageHandler(filters.ALL, ask_contact))
    app.add_handler(MessageHandler(filters.ALL, save_and_thank))

    app.add_handler(MessageHandler(filters.ALL, restart))
    app.add_handler(MessageHandler(filters.ALL, cancel))
    app.add_handler(MessageHandler(filters.ALL, ask_name))
    app.add_handler(MessageHandler(filters.ALL, ask_contact))
    app.add_handler(MessageHandler(filters.ALL, save_and_thank))

    # Удалим старый webhook, если был
    await app.bot.delete_webhook(drop_pending_updates=True)

    # Запустим webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
