import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from telegram import Bot

# Состояния
ROLE, NAME, CONTACT, VIDEO_TYPE, PORTFOLIO, CUSTOM_QUESTION = range(6)

# Переводы
translations = {
    "ru": {
        "start": """Добро пожаловать в One More Production!
Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.

С нами просто. И точно захочется one more.

👇 Выберите, кто вы (или напишите свой вариант):""",
        "ask_name": "Как к вам можно обращаться?",
        "ask_contact": "Уточните, пожалуйста, ваш номер телефона или @username.",
        "ask_type": "Какой тип видео вас интересует?",
        "ask_portfolio": "Пришлите, пожалуйста, ссылку на портфолио или резюме.",
        "ask_question": "Задайте свой вопрос, и мы постараемся ответить как можно скорее:",
        "thank_client": "Спасибо! Мы скоро свяжемся с вами 🙌",
        "thank_candidate": "Спасибо! Мы рассмотрим вашу заявку и свяжемся при необходимости.",
        "cancelled": "Диалог прерван. Напишите /start, чтобы начать заново.",
        "restart": "🔁 В начало",
        "website_info": "Перейдите на наш сайт:"
    }
}

def t(key, lang):
    return translations[lang].get(key, key)

def control_buttons(lang):
    return [[t("restart", lang), "🔗 Сайт"]]

def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("one-more-production-bot").worksheet("Заявки")
    return sheet

def save_to_sheet(name, contact, role, extra):
    sheet = connect_to_sheet()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, name, contact, role, extra])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    lang = context.user_data['lang'] = 'ru'
    role_keyboard = [["Клиент", "Соискатель"], control_buttons(lang)[0]]
    await update.message.reply_text(t("start", lang),
        reply_markup=ReplyKeyboardMarkup(role_keyboard, resize_keyboard=True))
    return ROLE

async def website_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(
        f"{t('website_info', lang)} https://onemorepro.com",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Перейти", url="https://onemorepro.com")]
        ])
    )
    return None

def is_control_command(text, lang):
    return text in [t("restart", lang), "🔗 Сайт"]

async def handle_control(update, context, current_state):
    lang = context.user_data.get("lang", "ru")
    text = update.message.text
    if text == t("restart", lang):
        return await start(update, context)
    elif "сайт" in text.lower():
        await website_handler(update, context)
        return current_state
    return None

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, ROLE)
    if state is not None:
        return state
    context.user_data['role'] = update.message.text
    lang = context.user_data['lang']
    await update.message.reply_text(t("ask_name", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, NAME)
    if state is not None:
        return state
    context.user_data['name'] = update.message.text
    lang = context.user_data['lang']
    await update.message.reply_text(t("ask_contact", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    return CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, CONTACT)
    if state is not None:
        return state
    context.user_data['contact'] = update.message.text
    lang = context.user_data['lang']
    role = context.user_data['role'].lower()

    if "кли" in role:
        keyboard = [["Реклама", "Клип"], ["Интервью", "Другое"], control_buttons(lang)[0]]
        await update.message.reply_text(t("ask_type", lang), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return VIDEO_TYPE
    elif "соискатель" in role:
        await update.message.reply_text(t("ask_portfolio", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
        return PORTFOLIO
    else:
        await update.message.reply_text(t("ask_question", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
        return CUSTOM_QUESTION

async def get_video_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, VIDEO_TYPE)
    if state is not None:
        return state
    context.user_data['video_type'] = update.message.text
    return await finish_conversation(update, context)

async def get_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, PORTFOLIO)
    if state is not None:
        return state
    context.user_data['portfolio'] = update.message.text
    return await finish_conversation(update, context)

async def finish_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    lang = data['lang']
    name = data['name']
    contact = data['contact']
    role = data['role']

    try:
        if "кли" in role.lower():
            save_to_sheet(name, contact, role, data.get('video_type', ''))
            await update.message.reply_text(t("thank_client", lang))
        else:
            extra = data.get('portfolio') or data.get('video_type') or update.message.text
            save_to_sheet(name, contact, role, extra)
            await update.message.reply_text(t("thank_candidate", lang))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при сохранении в Google Таблицы: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END

app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        VIDEO_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_video_type)],
        PORTFOLIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_portfolio)],
        CUSTOM_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_conversation)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

print("Бот запущен...")
Bot(os.environ.get("BOT_TOKEN")).delete_webhook(drop_pending_updates=True)
app.add_handler(conv_handler)
app.run_polling()
