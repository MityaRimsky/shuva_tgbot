import os
import time
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, Message
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
    CommandHandler,
    Defaults,
    Application,
)

from chatbot import SefariaChatBot

# ────────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)


# ────────────────────────────────────────────────────────────────────────────────
# Helper: safe reply with retry & exponential back-off
# ────────────────────────────────────────────────────────────────────────────────
async def safe_reply(message: Message, text: str, parse_mode: str = "HTML", retries: int = 3):
    delay = 1
    for attempt in range(retries):
        try:
            return await message.reply_text(text, parse_mode=parse_mode)
        except TimedOut:
            logger.warning("TimedOut while sending message. Attempt %s/%s", attempt + 1, retries)
            if attempt == retries - 1:
                return None
            await asyncio.sleep(delay)
            delay *= 2


# ────────────────────────────────────────────────────────────────────────────────
# Bot class (inherits logic from SefariaChatBot)
# ────────────────────────────────────────────────────────────────────────────────
class TelegramSefariaChatBot(SefariaChatBot):
    def __init__(self):
        super().__init__()


# ────────────────────────────────────────────────────────────────────────────────
# Load env & token
# ────────────────────────────────────────────────────────────────────────────────
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")


chat_bot = TelegramSefariaChatBot()


# ────────────────────────────────────────────────────────────────────────────────
# Handlers
# ────────────────────────────────────────────────────────────────────────────────
async def start(update: Update, context: CallbackContext):
    await safe_reply(
        update.message,
        (
            "<b>Шалом!</b> Я ваш эксперт по еврейским текстам, традициям и календарю.\n\n"
            "Просто задайте вопрос — и я постараюсь ответить развёрнуто и с источниками."
        ),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        if not user_input:
            return

        response = chat_bot.handle_query(user_input)

        if not response or not isinstance(response, str):
            response = "⚠️ Произошла ошибка при обработке запроса. Попробуйте позже."

        for i in range(0, len(response), 4000):
            part = response[i:i + 4000]
            try:
                await safe_reply(update.message, part, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Ошибка при отправке HTML-сообщения: {e}. Повтор с plain text.")
                await safe_reply(update.message, part, parse_mode=None)

    except Exception as e:
        logger.exception(f"Ошибка в handle_message: {e}")
        await safe_reply(update.message, "⚠️ Не удалось обработать сообщение. Попробуйте позже.", parse_mode=None)


async def calendar_command(update: Update, context: CallbackContext):
    response = chat_bot.get_calendar_context("сегодня")
    await safe_reply(update.message, response)


async def convert_command(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        await safe_reply(
            update.message,
            "Пример: /convert 2025-05-06 или /convert 5785 Нисан 27",
        )
        return

    query = f"конвертировать дату {' '.join(args)}"
    response = chat_bot.handle_query(query)
    await safe_reply(update.message, response)


# ────────────────────────────────────────────────────────────────────────────────
# Global error handler (keeps bot alive & logs traceback)
# ────────────────────────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update %s: %s", update, context.error, exc_info=context.error)


# ────────────────────────────────────────────────────────────────────────────────
# Main entry point (single-run, no relooping)
# ────────────────────────────────────────────────────────────────────────────────
def main():
    app: Application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .defaults(Defaults(parse_mode="HTML"))
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()