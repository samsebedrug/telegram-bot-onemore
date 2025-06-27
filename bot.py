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
    GREETING,
    CHOOSE_ROLE,
    GET_NAME,
    GET_CONTACT,
    GET_POSITION,
    GET_DETAILS
) = range(6)

# Кнопки

def base_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("/cancel"), KeyboardButton("/start")]], resize_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    image_url = "https://onemorepro.com/images/4.jpg"
    consent_text = (
        "Привет!\n\n"
        "Мы играем по правилам, поэтому должны получить от вас согласие на обработку данных.\n\n"
        "Нажимая кнопку ниже, вы подтверждаете своё согласие с нашей <a href=\"https://onemorepro.com/docs/privacy.pdf\">политикой конфиденциальности</a> "
        "и обработкой персональных данных.\n\n"
        "Введите /agree чтобы продолжить."
    )
    if update.message:
        await update.message.reply_photo(image_url, caption=None)
        await update.message.reply_html(consent_text, reply_markup=base_keyboard())
    return GREETING

async def greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text != "/agree":
        return GREETING

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Клиент")], [KeyboardButton("Соискатель")], [KeyboardButton("Другое")], [KeyboardButton("/cancel"), KeyboardButton("/start")]],
        resize_keyboard=True
    )
    welcome_text = (
        "Добро пожаловать в One More Production!\n\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n"
        "С нами просто и точно захочется one more.\n\n"
        "🔻 Выберите, кто вы:"
    )
    await update.message.reply_text(welcome_text, reply_markup=keyboard)
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw_role = update.message.text.lower()
    if raw_role == "/cancel":
        return await cancel(update, context)
    role_map = {"клиент": "client", "соискатель": "applicant", "другое": "other"}
    role_key = role_map.get(raw_role)
    if not role_key:
        return CHOOSE_ROLE
    context.user_data["role"] = role_key
    context.user_data["row"] = [raw_role, "", "", "", ""]
    await update.message.reply_text("Напишите, пожалуйста, ваше имя или название компании, которую вы представляете", reply_markup=base_keyboard())
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    if name == "/cancel":
        return await cancel(update, context)
    context.user_data["name"] = name
    context.user_data["row"][1] = name
    await update.message.reply_text("Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).", reply_markup=base_keyboard())
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.text
    if contact == "/cancel":
        return await cancel(update, context)
    context.user_data["contact"] = contact
    context.user_data["row"][2] = contact
    role = context.user_data["role"]
    if role in ["applicant", "other"]:
        await update.message.reply_text("Какова ваша роль в производстве?", reply_markup=base_keyboard())
    elif role == "client":
        await update.message.reply_text("Что вас интересует?", reply_markup=base_keyboard())
    else:
        return GET_DETAILS
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    position = update.message.text
    if position == "/cancel":
        return await cancel(update, context)
    context.user_data["position"] = position
    context.user_data["row"][3] = position
    await update.message.reply_text("Расскажите подробнее о вашем запросе:", reply_markup=base_keyboard())
    return GET_DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text
    context.user_data["details"] = details
    context.user_data["row"][4] = details
    sheet.append_row(context.user_data["row"])
    await update.message.reply_photo(
        "https://onemorepro.com/images/6.jpg",
        caption="Спасибо! Мы получили ваши данные и скоро с вами свяжемся.",
        reply_markup=base_keyboard()
    )
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_photo(
        "https://onemorepro.com/images/14.jpg",
        caption="Диалог отменён.",
        reply_markup=base_keyboard()
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
            GREETING: [MessageHandler(filters.TEXT & ~filters.COMMAND, greeting)],
            CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            GET_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_position)],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", restart)
        ],
        per_chat=True,
        per_message=False,
    )

    app.add_handler(conv_handler)

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
