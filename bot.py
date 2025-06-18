import logging
import os
import nest_asyncio
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Telegram conversation states
(ROLE, NAME, CONTACT, ROLE_DETAIL, DESCRIPTION) = range(5)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Google Sheets client
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Helper for the main keyboard
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 В начало", callback_data="restart")],
        [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")]
    ])

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ]
    await update.message.reply_text(
        "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 One More Production!\n\n\u041c\u044b \u0441\u043e\u0437\u0434\u0430\u0451\u043c \u0440\u0435\u043a\u043b\u0430\u043c\u0443, \u043a\u043b\u0438\u043f\u044b, \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u043e\u0435 \u043a\u0438\u043d\u043e \u0438 digital-\u043a\u043e\u043d\u0442\u0435\u043d\u0442.\n\n\u0421 \u043d\u0430\u043c\u0438 \u043f\u0440\u043e\u0441\u0442\u043e. \u0418 \u0442\u043e\u0447\u043d\u043e \u0437\u0430\u0445\u043e\u0447\u0435\u0442\u0441\u044f one more.\n\n\ud83d\udc47 \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435, \u043a\u0442\u043e \u0432\u044b:",
        reply_markup=InlineKeyboardMarkup(keyboard + get_main_keyboard().inline_keyboard),
    )
    return ROLE

# Button selection handler
async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data
    context.user_data.clear()
    context.user_data["role"] = role

    await query.message.reply_text(
        "Как вас зовут или какую компанию вы представляете?",
        reply_markup=get_main_keyboard()
    )
    return NAME

# Name input handler
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Оставьте ваш контакт (email, Telegram, телефон):",
        reply_markup=get_main_keyboard()
    )
    return CONTACT

# Contact input handler
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact"] = update.message.text

    if context.user_data["role"] == "applicant":
        await update.message.reply_text("Кем вы являетесь в видеопроизводстве?",
                                        reply_markup=get_main_keyboard())
        return ROLE_DETAIL
    elif context.user_data["role"] == "client":
        buttons = [
            [InlineKeyboardButton("\u0420\u0435\u043a\u043b\u0430\u043c\u0430", callback_data="ad")],
            [InlineKeyboardButton("\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u043e\u0435 \u043a\u0438\u043d\u043e", callback_data="doc")],
            [InlineKeyboardButton("\u041a\u043b\u0438\u043f", callback_data="clip")],
            [InlineKeyboardButton("Digital-\u043a\u043e\u043d\u0442\u0435\u043d\u0442", callback_data="digital")]
        ]
        await update.message.reply_text(
            "\u0427\u0442\u043e \u0432\u0430\u0441 \u0438\u043d\u0442\u0435\u0440\u0435\u0441\u0443\u0435\u0442? \u0418\u043b\u0438 \u043d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u0441\u0432\u043e\u0451:",
            reply_markup=InlineKeyboardMarkup(buttons + get_main_keyboard().inline_keyboard))
        return ROLE_DETAIL
    else:
        await update.message.reply_text("\u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043a \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u044e \u0437\u0430\u043f\u0440\u043e\u0441а:", reply_markup=get_main_keyboard())
        return DESCRIPTION

# Role detail handler
async def role_detail_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data["role_detail"] = update.callback_query.data
    else:
        context.user_data["role_detail"] = update.message.text

    await update.effective_message.reply_text("\u0420\u0430\u0441\u0441\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435 \u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0435:", reply_markup=get_main_keyboard())
    return DESCRIPTION

# Final handler
async def description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text
    sheet.append_row([
        context.user_data.get("role", ""),
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("role_detail", ""),
        context.user_data.get("description", "")
    ])
    await update.message.reply_text("\u0421\u043f\u0430\u0441\u0438\u0431\u043e! \u0414\u0430\u043d\u043d\u044b\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u044b.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# Restart
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("\u0412\u044b вернулись в начало. \u041f\u043e\u0435\u0445\u0430\u043b\u0438 \u0441\u043d\u043e\u0432\u0430!", reply_markup=None)
        return await start(update.callback_query, context)

# Main launcher
async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [CallbackQueryHandler(role_handler)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_handler)],
            ROLE_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_detail_handler),
                          CallbackQueryHandler(role_detail_handler)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_handler)],
        },
        fallbacks=[CallbackQueryHandler(restart, pattern="^restart$")],
    )

    app.add_handler(conv_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}"
    )

nest_asyncio.apply()
if __name__ == "__main__":
    asyncio.run(main())
