#!/usr/bin/env python
"""
Скрипт для тестирования конвертации дат между григорианским и еврейским календарями.
Проверяет корректность конвертации дат в разных годах.
"""
import datetime
import logging
from hebcal_api import HebcalAPI

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gregorian_to_hebrew_conversion():
    """Тестирование конвертации григорианских дат в еврейские"""
    print("\n=== Тестирование конвертации григорианских дат в еврейские ===")
    
    hebcal = HebcalAPI()
    
    # Список тестовых дат в разных годах
    test_dates = [
        # Текущий год
        datetime.date.today(),
        # Прошлые годы
        datetime.date(2023, 4, 15),
        datetime.date(2022, 9, 25),
        datetime.date(2021, 3, 10),
        datetime.date(2020, 12, 1),
        datetime.date(2019, 7, 4),
        datetime.date(2018, 1, 1),
        # Будущие годы
        datetime.date(2026, 5, 20),
        datetime.date(2027, 11, 30),
        # Особые даты (високосные годы и т.д.)
        datetime.date(2024, 2, 29),  # Високосный год
        datetime.date(2000, 1, 1),   # Начало века
        datetime.date(2100, 12, 31)  # Конец века
    ]
    
    success_count = 0
    failure_count = 0
    
    for date in test_dates:
        print(f"\nТестирование даты: {date.strftime('%Y-%m-%d')}")
        
        try:
            # Конвертация григорианской даты в еврейскую
            hebrew_data = hebcal.convert_date_to_hebrew(date)
            
            if "error" in hebrew_data:
                print(f"ОШИБКА: {hebrew_data.get('error')}")
                failure_count += 1
                continue
            
            # Проверка наличия необходимых полей
            required_fields = ["hebrew", "hy", "hm", "hd"]
            missing_fields = [field for field in required_fields if field not in hebrew_data]
            
            if missing_fields:
                print(f"ОШИБКА: Отсутствуют поля {', '.join(missing_fields)}")
                print(f"Полученные данные: {hebrew_data}")
                failure_count += 1
                continue
            
            # Обратная конвертация для проверки
            hebrew_date = {
                "hy": hebrew_data.get("hy"),
                "hm": hebrew_data.get("hm"),
                "hd": hebrew_data.get("hd")
            }
            
            greg_data = hebcal.convert_date_to_gregorian(hebrew_date)
            
            if "error" in greg_data:
                print(f"ОШИБКА при обратной конвертации: {greg_data.get('error')}")
                failure_count += 1
                continue
            
            # Проверка соответствия дат
            try:
                converted_date = datetime.date(
                    int(greg_data.get("gy", 0)),
                    int(greg_data.get("gm", 0)),
                    int(greg_data.get("gd", 0))
                )
                
                if converted_date == date:
                    print(f"УСПЕШНО: {date.strftime('%Y-%m-%d')} -> {hebrew_data.get('hebrew')} -> {converted_date.strftime('%Y-%m-%d')}")
                    success_count += 1
                else:
                    print(f"ОШИБКА: Даты не совпадают: {date.strftime('%Y-%m-%d')} != {converted_date.strftime('%Y-%m-%d')}")
                    print(f"Еврейская дата: {hebrew_data.get('hebrew')}")
                    print(f"Исходные данные: {hebrew_data}")
                    print(f"Данные обратной конвертации: {greg_data}")
                    failure_count += 1
            except (ValueError, TypeError) as e:
                print(f"ОШИБКА при создании объекта даты: {e}")
                print(f"Данные обратной конвертации: {greg_data}")
                failure_count += 1
        
        except Exception as e:
            print(f"ОШИБКА при тестировании даты {date.strftime('%Y-%m-%d')}: {str(e)}")
            failure_count += 1
    
    print(f"\nИтоги тестирования григорианских дат:")
    print(f"Успешно: {success_count}")
    print(f"Неудачно: {failure_count}")
    print(f"Всего протестировано: {len(test_dates)}")
    
    return success_count, failure_count

def test_hebrew_to_gregorian_conversion():
    """Тестирование конвертации еврейских дат в григорианские"""
    print("\n=== Тестирование конвертации еврейских дат в григорианские ===")
    
    hebcal = HebcalAPI()
    
    # Список тестовых еврейских дат
    test_hebrew_dates = [
        {"hy": 5784, "hm": "Nisan", "hd": 15},     # Песах текущего года
        {"hy": 5783, "hm": "Tishrei", "hd": 1},    # Рош ха-Шана прошлого года
        {"hy": 5782, "hm": "Kislev", "hd": 25},    # Ханука позапрошлого года
        {"hy": 5785, "hm": "Sivan", "hd": 6},      # Шавуот следующего года
        {"hy": 5786, "hm": "Av", "hd": 9},         # 9 Ава через два года
        {"hy": 5780, "hm": "Adar", "hd": 14},      # Пурим 2020 года
        {"hy": 5770, "hm": "Elul", "hd": 1},       # 1 Элула 2010 года
        {"hy": 5800, "hm": "Shvat", "hd": 15},     # Ту би-Шват далекого будущего
        {"hy": 5750, "hm": "Tamuz", "hd": 17},     # 17 Таммуза 1990 года
        {"hy": 5700, "hm": "Cheshvan", "hd": 10}   # 10 Хешвана 1939 года
    ]
    
    success_count = 0
    failure_count = 0
    
    for hebrew_date in test_hebrew_dates:
        hebrew_str = f"{hebrew_date['hy']} {hebrew_date['hm']} {hebrew_date['hd']}"
        print(f"\nТестирование еврейской даты: {hebrew_str}")
        
        try:
            # Конвертация еврейской даты в григорианскую
            greg_data = hebcal.convert_date_to_gregorian(hebrew_date)
            
            if "error" in greg_data:
                print(f"ОШИБКА: {greg_data.get('error')}")
                failure_count += 1
                continue
            
            # Проверка наличия необходимых полей
            required_fields = ["gy", "gm", "gd"]
            missing_fields = [field for field in required_fields if field not in greg_data]
            
            if missing_fields:
                print(f"ОШИБКА: Отсутствуют поля {', '.join(missing_fields)}")
                print(f"Полученные данные: {greg_data}")
                failure_count += 1
                continue
            
            # Создание объекта даты для проверки
            try:
                greg_date = datetime.date(
                    int(greg_data.get("gy", 0)),
                    int(greg_data.get("gm", 0)),
                    int(greg_data.get("gd", 0))
                )
                
                # Обратная конвертация для проверки
                hebrew_data = hebcal.convert_date_to_hebrew(greg_date)
                
                if "error" in hebrew_data:
                    print(f"ОШИБКА при обратной конвертации: {hebrew_data.get('error')}")
                    failure_count += 1
                    continue
                
                # Нормализуем месяцы для сравнения
                original_month = hebrew_date["hm"]
                returned_month = hebrew_data.get("hm", "")
                
                # Используем функцию нормализации из HebcalAPI
                normalized_original = hebcal.normalize_hebrew_month(original_month)
                normalized_returned = hebcal.normalize_hebrew_month(returned_month)
                
                # Проверка соответствия дат с учетом нормализации месяцев
                if (int(hebrew_data.get("hy", 0)) == hebrew_date["hy"] and
                    normalized_returned == normalized_original and
                    int(hebrew_data.get("hd", 0)) == hebrew_date["hd"]):
                    print(f"УСПЕШНО: {hebrew_str} -> {greg_date.strftime('%Y-%m-%d')} -> {hebrew_data.get('hebrew')}")
                    success_count += 1
                else:
                    print(f"ОШИБКА: Даты не совпадают:")
                    print(f"Исходная еврейская дата: {hebrew_str}")
                    print(f"Полученная еврейская дата: {hebrew_data.get('hebrew')}")
                    print(f"Исходные данные: {hebrew_date}")
                    print(f"Данные обратной конвертации: {hebrew_data}")
                    failure_count += 1
            
            except (ValueError, TypeError) as e:
                print(f"ОШИБКА при создании объекта даты: {e}")
                print(f"Данные конвертации: {greg_data}")
                failure_count += 1
        
        except Exception as e:
            print(f"ОШИБКА при тестировании даты {hebrew_str}: {str(e)}")
            failure_count += 1
    
    print(f"\nИтоги тестирования еврейских дат:")
    print(f"Успешно: {success_count}")
    print(f"Неудачно: {failure_count}")
    print(f"Всего протестировано: {len(test_hebrew_dates)}")
    
    return success_count, failure_count

def main():
    print("=" * 60)
    print("Тестирование конвертации дат между календарями")
    print("=" * 60)
    
    # Тестирование конвертации григорианских дат в еврейские
    g2h_success, g2h_failure = test_gregorian_to_hebrew_conversion()
    
    # Тестирование конвертации еврейских дат в григорианские
    h2g_success, h2g_failure = test_hebrew_to_gregorian_conversion()
    
    # Итоги тестирования
    print("\n" + "=" * 60)
    print("Итоги тестирования конвертации дат")
    print("=" * 60)
    print(f"Григорианские -> Еврейские: {g2h_success} успешно, {g2h_failure} неудачно")
    print(f"Еврейские -> Григорианские: {h2g_success} успешно, {h2g_failure} неудачно")
    
    total_success = g2h_success + h2g_success
    total_failure = g2h_failure + h2g_failure
    total_tests = total_success + total_failure
    
    print(f"\nВсего тестов: {total_tests}")
    print(f"Успешно: {total_success} ({total_success/total_tests*100:.1f}%)")
    print(f"Неудачно: {total_failure} ({total_failure/total_tests*100:.1f}%)")
    
    if total_failure == 0:
        print("\nВсе тесты пройдены успешно!")
        return 0
    else:
        print("\nНекоторые тесты не пройдены. Необходимо исправить ошибки конвертации дат.")
        return 1

if __name__ == "__main__":
    main()
