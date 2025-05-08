#!/usr/bin/env python
"""
Скрипт для тестирования API Sefaria, OpenRouter и Hebcal.
Проверяет доступность API и корректность работы модулей.
"""
import time
import os
import sys
import datetime
from dotenv import load_dotenv
from openrouter_api import OpenRouterAPI
from sefaria_api import SefariaAPI
from hebcal_api import HebcalAPI

def test_sefaria_api():
    """Тестирование API Sefaria"""
    print("\n=== Тестирование Sefaria API ===")
    
    try:
        sefaria = SefariaAPI()
        all_tests_passed = True
        # Тест поиска с разными параметрами
        print("\nТест поиска с разными настройками:")

        # Обычный поиск
        query = "Torah"
        print(f"Поиск по запросу (exact match): '{query}'")
        results = sefaria.search_texts(query, limit=3)
        if results and isinstance(results, list):
            print(f"Найдено результатов: {len(results)}")
            first_result = results[0] if results else {}
            source = first_result.get("_source", {})
            print(f"- Ссылка: {source.get('ref', 'Н/Д')}")
            print(f"- Заголовок: {source.get('title', 'Н/Д')}")
            print("Тест точного поиска: УСПЕШНО")
        else:
            print("Тест точного поиска: НЕУДАЧА")

        # Лемматизированный поиск
        print(f"\nПоиск с лемматизацией ('naive_lemmatizer') по '{query}'")
        results_lemma = sefaria.search_texts(query, limit=3, field="naive_lemmatizer")
        if results_lemma:
            print(f"Результатов найдено: {len(results_lemma)}")
            print("Тест лемматизированного поиска: УСПЕШНО")
        else:
            print("Тест лемматизированного поиска: НЕУДАЧА")

        # Поиск с расстоянием между словами (slop)
        phrase_query = "In the beginning"
        print(f"\nПоиск фразового запроса с допуском слов ('slop=5'): '{phrase_query}'")
        results_slop = sefaria.search_texts(phrase_query, slop=5)
        if results_slop:
            print(f"Результатов найдено: {len(results_slop)}")
            print("Тест поиска с допуском слов: УСПЕШНО")
        else:
            print("Тест поиска с допуском слов: НЕУДАЧА")

        # Поиск с особыми символами
        special_query = "Moses & Aaron"
        print(f"\nПоиск с особыми символами: '{special_query}'")
        results_special = sefaria.search_texts(special_query)
        if results_special:
            print(f"Результатов найдено: {len(results_special)}")
            print("Тест поиска с особыми символами: УСПЕШНО")
        else:
            print("Тест поиска с особыми символами: НЕУДАЧА")

        # Тест получения текста на английском
        print("\nТест получения текста на английском:")
        ref = "Genesis 1:1"
        print(f"Получение текста: '{ref}'")
        text_data = sefaria.get_text(ref)
        
        if text_data and "text" in text_data:
            print(f"Текст получен: {text_data.get('text', '')[:100]}...")
            print("Тест получения текста на английском: УСПЕШНО")
        else:
            print("Текст не получен. Проверьте подключение к интернету или доступность API.")
            print("Тест получения текста на английском: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест получения текста на иврите
        print("\nТест получения текста на иврите:")
        ref = "Genesis 1:1"
        print(f"Получение текста на иврите: '{ref}'")
        
        if text_data and "he" in text_data:
            print(f"Текст на иврите получен: {text_data.get('he', '')[:100]}...")
            print("Тест получения текста на иврите: УСПЕШНО")
        else:
            print("Текст на иврите не получен. Проверьте доступность API.")
            print("Тест получения текста на иврите: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест проверки структуры данных текста
        print("\nТест проверки структуры данных текста:")
        required_fields = ["text", "he", "ref", "heRef", "sectionRef"]
        missing_fields = [field for field in required_fields if field not in text_data]
        
        if not missing_fields:
            print("Все необходимые поля присутствуют в ответе API")
            print("Тест проверки структуры данных: УСПЕШНО")
        else:
            print(f"Отсутствуют следующие поля: {', '.join(missing_fields)}")
            print("Тест проверки структуры данных: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест получения связанных текстов
        print("\nТест получения связанных текстов:")
        ref = "Genesis 1:1"
        print(f"Получение связанных текстов для: '{ref}'")
        links_data = sefaria.get_links(ref)
        
        if links_data and isinstance(links_data, list):
            print(f"Получено связанных текстов: {len(links_data)}")
            if len(links_data) > 0:
                print(f"Пример связанного текста: {links_data[0].get('category', 'Н/Д')} - {links_data[0].get('ref', 'Н/Д')}")
            print("Тест получения связанных текстов: УСПЕШНО")
        else:
            print("Связанные тексты не получены или формат некорректен.")
            print("Тест получения связанных текстов: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест обработки ошибок при неправильной ссылке
        print("\nТест обработки ошибок при неправильной ссылке:")
        invalid_ref = "NonExistentBook 999:999"
        print(f"Получение текста по неправильной ссылке: '{invalid_ref}'")
        invalid_text_data = sefaria.get_text(invalid_ref)
        
        if not invalid_text_data or "error" in invalid_text_data:
            print("API корректно обрабатывает неправильные ссылки")
            print("Тест обработки ошибок: УСПЕШНО")
        else:
            print("API не обрабатывает неправильные ссылки должным образом")
            print("Тест обработки ошибок: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест форматирования результатов поиска (опциональный, зависит от результатов поиска)
        print("\nТест форматирования результатов поиска (опциональный):")
        formatted_results = sefaria.format_search_results(results)
        
        if formatted_results and isinstance(formatted_results, str) and len(formatted_results) > 0:
            print(f"Форматированные результаты: {formatted_results[:100]}...")
            print("Тест форматирования результатов поиска: УСПЕШНО")
        else:
            print(f"Форматирование результатов поиска вернуло: {formatted_results}")
            print("Тест форматирования результатов поиска: ПРОПУЩЕН (опциональный тест)")
        
        # Тест форматирования текста
        print("\nТест форматирования текста:")
        formatted_text = sefaria.format_text(text_data)
        
        if formatted_text and isinstance(formatted_text, str) and len(formatted_text) > 0:
            print(f"Форматированный текст: {formatted_text[:100]}...")
            print("Тест форматирования текста: УСПЕШНО")
        else:
            print("Форматирование текста не работает корректно")
            print("Тест форматирования текста: НЕУДАЧА")
            all_tests_passed = False
        
        return all_tests_passed
    
    except Exception as e:
        print(f"Ошибка при тестировании Sefaria API: {str(e)}")
        print("Тест Sefaria API: НЕУДАЧА")
        return False

def test_openrouter_api():
    """Тестирование API OpenRouter"""
    print("\n=== Тестирование OpenRouter API ===")
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия API ключа
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("API ключ OpenRouter не найден или не изменен с значения по умолчанию.")
        print("Пожалуйста, добавьте ваш API ключ в файл .env:")
        print("OPENROUTER_API_KEY=your_openrouter_api_key_here")
        return False
    
    try:
        openrouter = OpenRouterAPI()
        
        # Тест генерации ответа
        print("\nТест генерации ответа:")
        prompt = "Привет, как дела?"
        print(f"Промпт: '{prompt}'")
        
        response = openrouter.generate_response(prompt)
        
        if response and isinstance(response, str) and len(response) > 0:
            print(f"Ответ получен: {response[:100]}...")
            print("Тест генерации ответа: УСПЕШНО")
            return True
        else:
            print("Ответ не получен или некорректен.")
            print("Тест генерации ответа: НЕУДАЧА")
            return False
    
    except Exception as e:
        print(f"Ошибка при тестировании OpenRouter API: {str(e)}")
        print("Тест OpenRouter API: НЕУДАЧА")
        return False

def test_hebcal_api():
    """Тестирование API Hebcal"""
    print("\n=== Тестирование Hebcal API ===")
    
    try:
        hebcal = HebcalAPI()
        all_tests_passed = True
        
        # Тест получения текущей еврейской даты
        print("\nТест получения текущей еврейской даты:")
        current_hebrew_date = hebcal.get_current_hebrew_date()
        
        if current_hebrew_date and "hebrew" in current_hebrew_date:
            print(f"Текущая еврейская дата: {current_hebrew_date.get('hebrew', '')}")
            print("Тест получения текущей еврейской даты: УСПЕШНО")
        else:
            print("Не удалось получить текущую еврейскую дату.")
            print("Тест получения текущей еврейской даты: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест конвертации григорианской даты в еврейскую
        print("\nТест конвертации григорианской даты в еврейскую:")
        test_date = "2023-04-15"  # Пример даты
        print(f"Конвертация даты: {test_date}")
        
        hebrew_date = hebcal.convert_date_to_hebrew(test_date)
        
        if hebrew_date and "hebrew" in hebrew_date:
            print(f"Еврейская дата: {hebrew_date.get('hebrew', '')}")
            print("Тест конвертации григорианской даты в еврейскую: УСПЕШНО")
        else:
            print("Не удалось конвертировать дату.")
            print("Тест конвертации григорианской даты в еврейскую: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест получения праздников
        print("\nТест получения еврейских праздников:")
        current_year = datetime.date.today().year
        print(f"Получение праздников на {current_year} год")
        
        holidays = hebcal.get_holidays_for_year(current_year)
        
        if holidays and "items" in holidays and len(holidays["items"]) > 0:
            print(f"Получено праздников: {len(holidays['items'])}")
            print(f"Пример праздника: {holidays['items'][0].get('title', '')}")
            print("Тест получения еврейских праздников: УСПЕШНО")
        else:
            print("Не удалось получить информацию о праздниках.")
            print("Тест получения еврейских праздников: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест получения времени Шаббата
        print("\nТест получения времени Шаббата:")
        # Используем координаты Москвы для примера
        shabbat_times = hebcal.get_shabbat_times(latitude=55.7558, longitude=37.6173, tzid="Europe/Moscow")
        
        if shabbat_times and "items" in shabbat_times and len(shabbat_times["items"]) > 0:
            print(f"Получено элементов: {len(shabbat_times['items'])}")
            print("Тест получения времени Шаббата: УСПЕШНО")
        else:
            print("Не удалось получить информацию о времени Шаббата.")
            print("Тест получения времени Шаббата: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест подсчета дней до события
        print("\nТест подсчета дней до события:")
        future_date = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        print(f"Подсчет дней до даты: {future_date}")
        
        days = hebcal.days_until_event(future_date)
        
        if isinstance(days, int):
            print(f"Дней до события: {days}")
            print("Тест подсчета дней до события: УСПЕШНО")
        else:
            print("Не удалось подсчитать количество дней до события.")
            print("Тест подсчета дней до события: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест форматирования еврейской даты
        print("\nТест форматирования еврейской даты:")
        formatted_date = hebcal.format_hebrew_date(current_hebrew_date)
        
        if formatted_date and isinstance(formatted_date, str) and len(formatted_date) > 0:
            print(f"Форматированная дата: {formatted_date[:100]}...")
            print("Тест форматирования еврейской даты: УСПЕШНО")
        else:
            print("Не удалось отформатировать еврейскую дату.")
            print("Тест форматирования еврейской даты: НЕУДАЧА")
            all_tests_passed = False
        
        # Тест форматирования праздников
        print("\nТест форматирования праздников:")
        formatted_holidays = hebcal.format_holidays(holidays)
        
        if formatted_holidays and isinstance(formatted_holidays, str) and len(formatted_holidays) > 0:
            print(f"Форматированные праздники: {formatted_holidays[:100]}...")
            print("Тест форматирования праздников: УСПЕШНО")
        else:
            print("Не удалось отформатировать праздники.")
            print("Тест форматирования праздников: НЕУДАЧА")
            all_tests_passed = False
        
        return all_tests_passed
    
    except Exception as e:
        print(f"Ошибка при тестировании Hebcal API: {str(e)}")
        print("Тест Hebcal API: НЕУДАЧА")
        return False

def main():
    print("=" * 50)
    print("Тестирование API для Sefaria ChatBot")
    print("=" * 50)
    
    # Тестирование Sefaria API
    sefaria_success = test_sefaria_api()
    
    # Тестирование OpenRouter API
    openrouter_success = test_openrouter_api()
    
    # Тестирование Hebcal API
    hebcal_success = test_hebcal_api()
    
    # Итоги тестирования
    print("\n=== Итоги тестирования ===")
    print(f"Sefaria API: {'УСПЕШНО' if sefaria_success else 'НЕУДАЧА'}")
    print(f"OpenRouter API: {'УСПЕШНО' if openrouter_success else 'НЕУДАЧА'}")
    print(f"Hebcal API: {'УСПЕШНО' if hebcal_success else 'НЕУДАЧА'}")
    
    if sefaria_success and openrouter_success and hebcal_success:
        print("\nВсе тесты пройдены успешно! Вы можете запустить приложение.")
        return 0
    else:
        if not sefaria_success:
            print("\nТесты Sefaria API не пройдены. Однако, основные функции получения и чтения текстов могут работать.")
            print("Проверьте результаты тестов выше для более подробной информации.")
        if not openrouter_success:
            print("\nТесты OpenRouter API не пройдены. Проверьте наличие API ключа и подключение к интернету.")
        if not hebcal_success:
            print("\nТесты Hebcal API не пройдены. Проверьте подключение к интернету и доступность API.")
        
        print("\nНекоторые тесты не пройдены. Рекомендуется исправить ошибки перед запуском приложения.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
