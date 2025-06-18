import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# Удаляем старый Webhook — это ключевой шаг!
Bot("7543889103:AAG9rP-jt7lfcCGZ5hZwJvFwHx9n65XtkVU").delete_webhook(drop_pending_updates=True)

# Потом создаётся Application:
app = ApplicationBuilder().token("7543889103:AAG9rP-jt7lfcCGZ5hZwJvFwHx9n65XtkVU").build()

# Состояния
ROLE, NAME, CONTACT, VIDEO_TYPE, PORTFOLIO, CUSTOM_QUESTION = range(6)

√    context.user_data['role'] = update.message.text
    context.user_data['history'].append(ROLE)
    lang = context.user_data['lang']
    await update.message.reply_text(t("ask_name", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, NAME)
    if state is not None:
        return state
    context.user_data['name'] = update.message.text
    context.user_data['history'].append(NAME)
    lang = context.user_data['lang']
    await update.message.reply_text(t("ask_contact", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    return CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, CONTACT)
    if state is not None:
        return state
    context.user_data['contact'] = update.message.text
    context.user_data['history'].append(CONTACT)
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
        await update.message.reply_text("Задайте свой вопрос:", reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
        return CUSTOM_QUESTION

async def get_video_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, VIDEO_TYPE)
    if state is not None:
        return state
    context.user_data['video_type'] = update.message.text
    context.user_data['history'].append(VIDEO_TYPE)
    return await finish_conversation(update, context)

async def get_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, PORTFOLIO)
    if state is not None:
        return state
    context.user_data['portfolio'] = update.message.text
    context.user_data['history'].append(PORTFOLIO)
    return await finish_conversation(update, context)

async def get_custom_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_control(update, context, CUSTOM_QUESTION)
    if state is not None:
        return state
    context.user_data['custom_question'] = update.message.text
    context.user_data['history'].append(CUSTOM_QUESTION)
    return await finish_conversation(update, context)

async def finish_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    lang = data['lang']
    name = data['name']
    contact = data['contact']
    role = data['role']

    try:
        if "кли" in role.lower():
            extra = data.get('video_type', '')
            save_to_sheet(name, contact, "Клиент", extra)
            await update.message.reply_text(t("thank_client", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
        elif "соискатель" in role.lower():
            extra = data.get('portfolio', '')
            save_to_sheet(name, contact, "Соискатель", extra)
            await update.message.reply_text(t("thank_candidate", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
        else:
            extra = data.get('custom_question', '')
            save_to_sheet(name, contact, role, extra)
            await update.message.reply_text(t("thank_candidate", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при сохранении в Google Таблицы: {e}", reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))

    return ROLE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(t("cancelled", lang), reply_markup=ReplyKeyboardMarkup(control_buttons(lang), resize_keyboard=True))
    return ROLE

state_handlers = {
    ROLE: get_role,
    NAME: get_name,
    CONTACT: get_contact,
    VIDEO_TYPE: get_video_type,
    PORTFOLIO: get_portfolio,
    CUSTOM_QUESTION: get_custom_question
}

app = ApplicationBuilder().token("7543889103:AAG9rP-jt7lfcCGZ5hZwJvFwHx9n65XtkVU").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        VIDEO_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_video_type)],
        PORTFOLIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_portfolio)],
        CUSTOM_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_question)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True
)

app.add_handler(conv_handler)
print("Бот запущен...")
app.run_polling()
