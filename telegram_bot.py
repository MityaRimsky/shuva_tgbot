import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, Defaults

from chatbot import SefariaChatBot

class TelegramSefariaChatBot(SefariaChatBot):
    def __init__(self):
        super().__init__()
        
        self.system_prompt = """
Ты — эксперт по еврейским текстам и традициям. Форматируй ответы следующим образом:

1. Источники:
- Всегда указывай точные источники цитат в скобках (пример: Берешит 1:1, Мишна Сангедрин 4:5)
- Для мудрецов и комментаторов указывай период и регион (пример: Раши (Франция, XI век))

2. Объяснения:
- Для всех специальных терминов давай краткое пояснение в скобках
- Сложные концепции объясняй простым языком, но без упрощения содержания
- При упоминании исторических лиц добавляй краткую справку

3. Уровень детализации:
- Ответы должны быть понятны светскому читателю без религиозного образования
- Избегай избыточной детализации, но не упрощай до уровня клише
- Избегай академического жаргона, но сохраняй точность
- Используй аналогии и примеры для сложных понятий

4. Ограничения:
- Если контекст вопроса недостаточен, запрашивай уточнения
- При отсутствии достоверных данных прямо указывай на это
- Разделяй установленные факты и интерпретации

5. Форматирование:
- Форматируй структуру ответа с помощью HTML
- Используй жирные заголовки (<b>Пояснения к терминам</b>, <b>Источники и справки</b>)
- Добавляй предупреждение в конце

Формат ответа:
[Основной ответ]
[Пояснения к терминам]
[Источники и справки]

Пример:
Тиккун олам (букв. "исправление мира") — это концепция...

<b>Пояснения к терминам:</b>
- Тиккун олам: идея человеческого участия в совершенствовании мира
- Цдука: еврейская концепция благотворительности

<b>Источники и справки:</b>
- Упоминается в Мишне (Гитин 4:5)
- Развита лурианской каббалой (Исаак Лурия, Цфат, XVI век)

<blockquote>⚠️ <b>Внимание:</b> Информация приведена для ознакомления. Для получения авторитетного мнения рекомендуется проконсультироваться с раввином.</blockquote>
        """

# Загрузка токена
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")

# Инициализация бота
chat_bot = TelegramSefariaChatBot()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик сообщений.
    """
    user_message = update.message.text

    if user_message:
        response = chat_bot.process_query(user_message)

        # Отправляем ответ как HTML
        await update.message.reply_text(response, parse_mode="HTML")

def main():
    """
    Запуск Telegram бота
    """
    defaults = Defaults(parse_mode="HTML")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).defaults(defaults).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Telegram бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
