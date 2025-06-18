import os
import logging
import gspread

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from oauth2client.service_account import ServiceAccountCredentials

# Логгирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Авторизация Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("One More Bot").sheet1  # Убедись, что имя совпадает

# Состояния для ConversationHandler
SELECT_ROLE, ENTER_NAME, ENTER_PHONE, CONFIRM = range(4)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Студент", "Преподаватель"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите вашу роль:", reply_markup=reply_markup)
    return SELECT_ROLE

# Обработка выбранной роли
async def select_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Введите ваше имя:")
    return ENTER_NAME

# Обработка имени
async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите ваш номер телефона:")
    return ENTER_PHONE

# Обработка номера телефона
async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["phone"] = update.message.text

    # Подтверждение
    role = context.user_data["role"]
    name = context.user_data["name"]
    phone = context.user_data["phone"]
    await update.message.reply_text(
        f"Проверьте данные:\n\nРоль: {role}\nИмя: {name}\nТелефон: {phone}\n\nЕсли всё верно, напишите 'Да'"
    )
    return CONFIRM

# Подтверждение и запись
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "да":
        sheet.append_row([
            context.user_data["role"],
            context.user_data["name"],
            context.user_data["phone"]
        ])
        await update.message.reply_text("Данные сохранены. Спасибо!")
    else:
        await update.message.reply_text("Отменено. Начните заново: /start")

    return ConversationHandler.END

# Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Запуск приложения
def main() -> None:
    token = os.getenv("BOT_TOKEN")  # Убедись, что BOT_TOKEN задан в Render
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_role)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # ⛔ БЕЗ asyncio.run(): just call run_polling directly
    application.run_polling()

if __name__ == "__main__":
    main()
