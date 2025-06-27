import os
import logging
import asyncio
import nest_asyncio
from aiohttp import web

from telegram import (
    Update,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
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
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Состояния
(
    GET_NAME,
    GET_CONTACT,
    GET_POSITION,
    GET_DETAILS
) = range(4)

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Отмена")],
            [KeyboardButton("🌐 На сайт")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/11-1.jpg",
        caption="Добро пожаловать в One More Production!\n\nС нами просто и точно захочется one more.\n\nНапишите, пожалуйста, ваше имя или название компании, которую вы представляете",
        reply_markup=main_keyboard()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    name = update.message.text
    context.user_data["name"] = name
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/12.jpg",
        caption="Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).",
        reply_markup=main_keyboard()
    )
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    contact = update.message.text
    context.user_data["contact"] = contact
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/3.jpg",
        caption="Какова ваша роль в производстве или что вас интересует?",
        reply_markup=main_keyboard()
    )
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    position = update.message.text
    context.user_data["position"] = position
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/6.jpg",
        caption="Расскажите подробнее о вашем запросе:",
        reply_markup=main_keyboard()
    )
    return GET_DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text
    context.user_data["details"] = details
    row = [
        context.user_data.get("name", ""),
        context.user_data.get("contact", ""),
        context.user_data.get("position", ""),
        context.user_data.get("details", "")
    ]
    sheet.append_row(row)
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/8.jpg",
        caption="Спасибо! Мы получили ваши данные и скоро с вами свяжемся.\n\nДля повторного запуска бота введите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/14.jpg",
        caption="Диалог завершен. Для перезапуска бота введите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def healthz(request):
    return web.Response(text="ok")

async def webhook_handler(request):
    update = await request.json()
    await request.app["application"].process_update(Update.de_json(update, request.app["application"].bot))
    return web.Response()

async def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            GET_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_position)],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True,
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook")

    web_app = web.Application()
    web_app["application"] = app
    web_app.add_routes([
        web.post("/webhook", webhook_handler),
        web.get("/healthz", healthz),
    ])

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8443)))
    await site.start()

    await app.start()
    logger.info("Bot is running...")
    await asyncio.Event().wait()  # run forever

nest_asyncio.apply()

if __name__ == "__main__":
    asyncio.run(main())
