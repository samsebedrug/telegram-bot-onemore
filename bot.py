
import os
import logging
import asyncio
import nest_asyncio
from aiohttp import web

from telegram import (
    Update,
    ReplyKeyboardRemove,
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
    GREETING,
    CHOOSE_ROLE,
    GET_NAME,
    GET_CONTACT,
    GET_POSITION,
    GET_DETAILS
) = range(6)

# Кнопки
def base_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 На сайт", url="https://onemorepro.com")],
        [InlineKeyboardButton("🔁 Начать заново", callback_data="restart")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    consent_text = (
        "<img src='https://onemorepro.com/images/4.jpg'/>

"
        "Добро пожаловать в One More Production!

"
        "Мы играем по правилам, поэтому должны получить от вас согласие на обработку данных.

"
        "Нажимая кнопку ниже, вы подтверждаете своё согласие с нашей "
        "<a href='https://onemorepro.com/docs/privacy.pdf'>политикой конфиденциальности</a> и обработкой персональных данных."
    )
    keyboard = [[InlineKeyboardButton("Согласен", callback_data="agree")]]
    if update.message:
        await update.message.reply_html(consent_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return GREETING

async def greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ]
    welcome_text = (
        "<img src='https://onemorepro.com/images/11-1.jpg'/>

"
        "Добро пожаловать в One More Production!

"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.
"
        "С нами просто и точно захочется one more.

"
        "🔻 Выберите, кто вы:"
    )
    await query.message.reply_html(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    raw_role = query.data
    role_map = {"client": "клиент", "applicant": "соискатель", "other": "другое"}
    role = role_map.get(raw_role, raw_role)
    context.user_data["role"] = raw_role
    context.user_data["row"] = [role, "", "", "", ""]
    await query.message.reply_html(
        "<img src='https://onemorepro.com/images/12.jpg'/>

"
        "Напишите, пожалуйста, ваше имя или название компании, которую вы представляете",
        reply_markup=base_keyboard()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Пожалуйста, введите корректное имя (до 100 символов).", reply_markup=base_keyboard())
        return GET_NAME
    context.user_data["name"] = name
    context.user_data["row"][1] = name
    await update.message.reply_html(
        "<img src='https://onemorepro.com/images/13-1.jpg'/>

"
        "Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).",
        reply_markup=base_keyboard()
    )
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.text.strip()
    if not any(s in contact for s in ["@", "+", "."]):
        await update.message.reply_text("Пожалуйста, введите корректный контакт.", reply_markup=base_keyboard())
        return GET_CONTACT
    context.user_data["contact"] = contact
    context.user_data["row"][2] = contact
    role = context.user_data["role"]
    if role in ["applicant", "other"]:
        await update.message.reply_html(
            "<img src='https://onemorepro.com/images/3.jpg'/>

"
            "Какова ваша роль в производстве?",
            reply_markup=base_keyboard()
        )
    elif role == "client":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="ad")],
            [InlineKeyboardButton("Документальное кино", callback_data="doc")],
            [InlineKeyboardButton("Клип", callback_data="clip")],
            [InlineKeyboardButton("Digital-контент", callback_data="digital")],
            [InlineKeyboardButton("Другое", callback_data="other")]
        ]
        await update.message.reply_html(
            "<img src='https://onemorepro.com/images/3.jpg'/>

"
            "Что вас интересует?",
            reply_markup=InlineKeyboardMarkup(keyboard + list(base_keyboard().inline_keyboard))
        )
    else:
        return GET_DETAILS
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        position = update.callback_query.data
        await update.callback_query.message.reply_html(
            "<img src='https://onemorepro.com/images/6.jpg'/>

"
            "Расскажите подробнее о вашем запросе:",
            reply_markup=base_keyboard()
        )
    else:
        position = update.message.text
        await update.message.reply_html(
            "<img src='https://onemorepro.com/images/6.jpg'/>

"
            "Расскажите подробнее о вашем запросе:",
            reply_markup=base_keyboard()
        )
    context.user_data["position"] = position
    context.user_data["row"][3] = position
    return GET_DETAILS

async def get_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text.strip()
    if len(details) > 1000:
        await update.message.reply_text("Слишком много текста. Пожалуйста, сократите до 1000 символов.", reply_markup=base_keyboard())
        return GET_DETAILS
    context.user_data["details"] = details
    context.user_data["row"][4] = details
    try:
        sheet.append_row(context.user_data["row"])
    except Exception as e:
        logger.exception("Ошибка при записи в таблицу")
        await update.message.reply_text("Произошла ошибка при сохранении данных. Попробуйте позже.", reply_markup=base_keyboard())
        return ConversationHandler.END
    await update.message.reply_html(
        "<img src='https://onemorepro.com/images/8.jpg'/>

"
        "Спасибо! Мы получили ваши данные и скоро с вами свяжемся.

"
        "Для повторного запуска бота введите команду /start",
        reply_markup=base_keyboard()
    )
    return ConversationHandler.END
(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
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
            GREETING: [CallbackQueryHandler(greeting, pattern="^agree$")],
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            GET_POSITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_position),
                CallbackQueryHandler(get_position)
            ],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(restart, pattern="^restart$")
        ],
        per_chat=True,
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))

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
