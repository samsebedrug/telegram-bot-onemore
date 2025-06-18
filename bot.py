import os
import logging
import asyncio
import nest_asyncio

from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("One More Bot").sheet1

# Conversation states
ROLE, NAME, CONTACT, PROJECT_TYPE, ABOUT = range(5)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Клиент", "Соискатель", "Свой вариант"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    welcome_text = (
        "Добро пожаловать в One More Production!\n"
        "Мы создаём рекламу, клипы, документальное кино и всевозможный digital-контент.\n\n"
        "С нами просто. И точно захочется one more.\n\n"
        "
