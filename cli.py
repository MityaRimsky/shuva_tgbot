#!/usr/bin/env python
"""
Консольный интерфейс для Sefaria ChatBot.
Позволяет взаимодействовать с чат-ботом через командную строку.
"""

import os
import sys
from chatbot import SefariaChatBot
from dotenv import load_dotenv

def main():
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Ошибка: API ключ OpenRouter не найден.")
        print("Пожалуйста, добавьте ваш API ключ в файл .env:")
        print("OPENROUTER_API_KEY=your_openrouter_api_key_here")
        sys.exit(1)
    
    try:
        # Инициализация чат-бота
        chatbot = SefariaChatBot()
        
        print("=" * 50)
        print("Sefaria ChatBot (Консольная версия)")
        print("Введите 'выход' или 'exit' для завершения.")
        print("=" * 50)
        
        # Основной цикл взаимодействия
        while True:
            # Получение запроса от пользователя
            query = input("\nВаш вопрос: ")
            
            # Проверка на выход
            if query.lower() in ["выход", "exit", "quit", "q"]:
                print("До свидания!")
                break
            
            # Если запрос пустой, продолжаем
            if not query.strip():
                continue
            
            print("\nОбработка запроса...")
            
            try:
                # Обработка запроса и получение ответа
                response = chatbot.process_query(query)
                
                print("\nОтвет:")
                print("-" * 50)
                print(response)
                print("-" * 50)
            except Exception as e:
                print(f"Ошибка при обработке запроса: {str(e)}")
    
    except Exception as e:
        print(f"Ошибка при инициализации чат-бота: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
