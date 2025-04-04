#!/usr/bin/env python
"""
Точка входа для запуска тестов API Sefaria ChatBot.
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию main из модуля test_api
from test_api import main

if __name__ == "__main__":
    # Загрузка переменных окружения
    load_dotenv()
    
    # Запуск тестов
    sys.exit(main())
