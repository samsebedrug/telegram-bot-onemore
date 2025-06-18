import asyncio
import os
import logging
from telegram import Bot
from telegram.error import InvalidToken

async def test_bot_token():
    token = os.getenv("BOT_TOKEN")
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if not token:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения.")
        return

    bot = Bot(token=token)

    try:
        me = await bot.get_me()
        logger.info(f"✅ Токен работает. Бот: {me.username} (ID: {me.id})")
    except InvalidToken as e:
        logger.error("❌ InvalidToken: Неверный токен.")
    except Exception as e:
        logger.exception(f"❌ Другая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot_token())
