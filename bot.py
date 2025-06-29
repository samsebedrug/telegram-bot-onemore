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
        [InlineKeyboardButton("\ud83c\udf10 На сайт", url="https://onemorepro.com")],
        [InlineKeyboardButton("\ud83d\udd01 Начать заново", callback_data="restart")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    consent_caption = (
        "Добро пожаловать в One More Production!\n\n"
        "Мы играем по правилам, поэтому должны получить от вас согласие на обработку данных.\n\n"
        "Нажимая кнопку ниже, вы подтверждаете своё согласие с нашей <a href='https://onemorepro.com/docs/privacy.pdf'>"
        "политикой конфиденциальности</a> и обработкой персональных данных."
    )
    keyboard = [[InlineKeyboardButton("Согласен", callback_data="agree")]] + base_keyboard().inline_keyboard
    if update.message:
        await update.message.reply_photo(
            photo="https://onemorepro.com/images/4.jpg",
            caption=consent_caption,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_photo(
            photo="https://onemorepro.com/images/4.jpg",
            caption=consent_caption,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return GREETING

async def greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Клиент", callback_data="client")],
        [InlineKeyboardButton("Соискатель", callback_data="applicant")],
        [InlineKeyboardButton("Другое", callback_data="other")]
    ] + base_keyboard().inline_keyboard
    welcome_text = (
        "Добро пожаловать в One More Production!\n\n"
        "Мы создаём рекламу, клипы, документальное кино и digital-контент.\n"
        "С нами просто и точно захочется one more.\n\n"
        "\ud83d\udd3b Выберите, кто вы:"
    )
    await query.message.reply_photo(
        photo="https://onemorepro.com/images/11-1.jpg",
        caption=welcome_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    raw_role = query.data
    role_map = {"client": "клиент", "applicant": "соискатель", "other": "другое"}
    role = role_map.get(raw_role, raw_role)
    context.user_data["role"] = raw_role
    context.user_data["row"] = [role, "", "", "", ""]
    await query.message.reply_photo(
        photo="https://onemorepro.com/images/12.jpg",
        caption="Напишите, пожалуйста, ваше имя или название компании, которую вы представляете",
        reply_markup=base_keyboard()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Пожалуйста, введите корректное имя (до 100 символов).", reply_markup=base_keyboard())
        return GET_NAME
    context.user_data["name"] = name
    if "row" not in context.user_data:
        context.user_data["row"] = ["", name, "", "", ""]
    context.user_data["row"][1] = name
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/13-1.jpg",
        caption="Оставьте, пожалуйста, ваш контакт (телефон, email или ник в Telegram).",
        reply_markup=base_keyboard()
    )
    return GET_CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.text.strip()
    context.user_data["contact"] = contact
    context.user_data["row"][2] = contact
    role = context.user_data.get("role")
    if role in ["applicant", "other"]:
        await update.message.reply_photo(
            photo="https://onemorepro.com/images/3.jpg",
            caption="Какова ваша роль в производстве?",
            reply_markup=base_keyboard()
        )
    elif role == "client":
        keyboard = [
            [InlineKeyboardButton("Реклама", callback_data="ad")],
            [InlineKeyboardButton("Документальное кино", callback_data="doc")],
            [InlineKeyboardButton("Клип", callback_data="clip")],
            [InlineKeyboardButton("Digital-контент", callback_data="digital")],
            [InlineKeyboardButton("Другое", callback_data="other")]
        ] + base_keyboard().inline_keyboard
        await update.message.reply_photo(
            photo="https://onemorepro.com/images/3.jpg",
            caption="Что вас интересует?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        return GET_DETAILS
    return GET_POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        position = update.callback_query.data
        await update.callback_query.message.reply_photo(
            photo="https://onemorepro.com/images/6.jpg",
            caption="Расскажите подробнее о вашем запросе:",
            reply_markup=base_keyboard()
        )
    else:
        position = update.message.text
        await update.message.reply_photo(
            photo="https://onemorepro.com/images/6.jpg",
            caption="Расскажите подробнее о вашем запросе:",
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
    await update.message.reply_photo(
        photo="https://onemorepro.com/images/8.jpg",
        caption="Спасибо! Мы получили ваши данные и скоро с вами свяжемся.\n\nДля повторного запуска бота введите команду /start",
        reply_markup=base_keyboard()
    )
    return ConversationHandler.END

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if "row" in context.user_data:
            all_records = sheet.get_all_values()
            if context.user_data["row"] in all_records:
                index = all_records.index(context.user_data["row"]) + 1
                sheet.delete_row(index)
    except Exception:
        logger.warning("Не удалось удалить строку при рестарте")
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
            GREETING: [CallbackQueryHandler(greeting, pattern="^agree$"), CallbackQueryHandler(restart, pattern="^restart$")],
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role), CallbackQueryHandler(restart, pattern="^restart$")],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name), CallbackQueryHandler(restart, pattern="^restart$")],
            GET_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact), CallbackQueryHandler(restart, pattern="^restart$")],
            GET_POSITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_position),
                CallbackQueryHandler(get_position),
                CallbackQueryHandler(restart, pattern="^restart$")
            ],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details), CallbackQueryHandler(restart, pattern="^restart$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(restart, pattern="^restart$")
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
