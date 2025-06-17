from telegram import Bot

# Вставь сюда свой токен
TOKEN = "7543889103:AAG9rP-jt7lfcCGZ5hZwJvFwHx9n65XtkVU"

bot = Bot(token=TOKEN)

try:
    bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook удалён. Теперь можно безопасно запускать polling.")
except Exception as e:
    print(f"❌ Ошибка при удалении webhook: {e}")
