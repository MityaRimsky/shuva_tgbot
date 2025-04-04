#!/usr/bin/env python
"""
Точка входа для запуска консольного интерфейса Sefaria ChatBot.
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию main из модуля cli
from cli import main

if __name__ == "__main__":
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") == "your_openrouter_api_key_here":
        print("ВНИМАНИЕ: API ключ OpenRouter не найден или не изменен с значения по умолчанию.")
        print("Пожалуйста, добавьте ваш API ключ в файл .env:")
        print("OPENROUTER_API_KEY=your_openrouter_api_key_here")
        sys.exit(1)
    
    # Запуск консольного интерфейса
    sys.exit(main())
