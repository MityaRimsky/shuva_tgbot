from __future__ import annotations

import re
import html
from datetime import datetime, timedelta, date
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta

from openrouter_api import OpenRouterAPI
from sefaria_api import SefariaAPI
from hebcal_api import HebcalAPI

# Регулярные выражения для распознавания дат
DATE_RE = re.compile(r"(\d{4})[- /.](\d{1,2})[- /.](\d{1,2})")  # Полный формат с годом: 2023-05-15
DATE_WITHOUT_YEAR_RE = re.compile(r"(?<!\d)(\d{1,2})[- /.]?(?:\s*)([а-яА-Яa-zA-Z]+)")  # Формат без года: 15 мая, 12 декабря

# Словарь для преобразования названий месяцев в числа
MONTH_NAME_TO_NUMBER = {
    # Русские названия месяцев (различные формы)
    "январ": 1, "янв": 1,
    "феврал": 2, "фев": 2,
    "март": 3, "мар": 3,
    "апрел": 4, "апр": 4,
    "ма": 5, "май": 5,
    "июн": 6,
    "июл": 7,
    "август": 8, "авг": 8,
    "сентябр": 9, "сен": 9,
    "октябр": 10, "окт": 10,
    "ноябр": 11, "ноя": 11,
    "декабр": 12, "дек": 12,
    
    # Английские названия месяцев
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}


class SefariaChatBot:
    def __init__(self):
        self.openrouter_api = OpenRouterAPI()
        self.sefaria_api = SefariaAPI()
        self.hebcal_api = HebcalAPI()
        self.system_prompt = self._build_system_prompt()

    def handle_query(self, query: str) -> str:
        category = self._route_query(query)

        if category == "calendar_today":
            return self._get_calendar_context(query)

        if category == "calendar_info":
            return self._handle_calendar_event(query)

        if category == "calendar_diff":
            return self._handle_date_diff(query)

        if category == "calendar_with_context":
            cal_ctx = self._get_calendar_context(query)
            return self._process_query(query, custom_context=cal_ctx)

        if category == "text_search":
            return self._process_query(query)

        return self._process_query(query)

    def _route_query(self, query: str) -> str:
        router_prompt = """
Ты — маршрутизатор для еврейского чат-бота. Выбери одну из категорий, которая лучше всего описывает намерение пользователя.

Категории:

• calendar_today         — узнать сегодняшнюю/завтрашнюю/вчерашнюю дату, день недели, еврейскую дату и т.п.
• calendar_info          — запрос даты или информации о празднике, шаббате, конвертация дат, сколько дней до события, (например: «19 июля какой день по еврейски», «2 кислев какой день по григориански», «5 сиван конвертируй в григорианский»)
• calendar_diff          — разница между двумя датами
• calendar_with_context  — требуется и календарная информация, и объяснение текста (например: «Расскажи о Шавуоте и когда он будет»)
• text_search            — поиск источников, объяснение понятий, вопросов о законах, комментариях, историях и т.п.
• general                — всё остальное, включая философию, мораль, историю, современность

Отвечай только одной категорией. Без пояснений. Без кавычек. Только имя категории.
"""
        return self.openrouter_api.generate_response(prompt=query, context=router_prompt).strip().lower()

    # Словарь с альтернативными названиями праздников на русском языке
    HOLIDAY_NAMES = {
        "песах": ["песах", "пейсах", "пасха", "песаха", "песаху", "песахе"],
        "шавуот": ["шавуот", "шавуота", "шавуоту", "шавуоте", "шавуотом"],
        "рош ха-шана": ["рош", "рош хашана", "рош ха шана", "рош а-шана", "рош ашана", "рош хашана", "рош гашана", "новый год", "еврейский новый год"],
        "йом киппур": ["йом кипур", "йом-кипур", "йом-киппур", "йом киппур", "судный день", "день искупления"],
        "суккот": ["суккот", "суккота", "суккоту", "суккоте", "суккотом", "кущи", "праздник кущей"],
        "шмини ацерет": ["шмини", "шмини ацерет", "шмини-ацерет"],
        "симхат тора": ["симхат", "симхат тора", "симхат-тора", "симхат тору", "симхат торе", "симхат торой"],
        "ханука": ["ханука", "хануке", "хануку", "ханукой", "ханукой", "праздник свечей", "праздник огней"],
        "ту би-шват": ["ту би-шват", "ту би шват", "ту бишват", "новый год деревьев"],
        "пурим": ["пурим", "пурима", "пуриму", "пуриме", "пуримом"],
        "лаг ба-омер": ["лаг ба-омер", "лаг ба омер", "лаг баомер"],
        "тиша бе-ав": ["тиша бе-ав", "тиша бе ав", "тиша беав", "9 ава"]
    }

    def _handle_calendar_event(self, query: str) -> str:
        # Проверяем, является ли запрос запросом на конвертацию даты
        query_lower = query.lower()
        is_date_conversion = any(phrase in query_lower for phrase in [
            "конвертир", "перевед", "как будет", "какая дата", "какой день", 
            "по еврейски", "по григориански", "в еврейский", "в григорианский",
            "на иврите", "на еврейском"
        ])
        
        # Если это запрос на конвертацию даты, вызываем специальный обработчик
        if is_date_conversion:
            return self._handle_date_conversion(query)
        
        # Проверяем, является ли запрос запросом о времени до праздника
        is_days_until_query = any(phrase in query_lower for phrase in [
            "сколько дней до", "когда будет", "когда наступит", "когда начинается", 
            "когда начнется", "когда отмечают", "когда празднуют", "когда отмечается",
            "когда празднуется", "когда наступает"
        ])
        
        # Определяем, о каком празднике идет речь
        holiday_name = None
        for main_name, alternatives in self.HOLIDAY_NAMES.items():
            if any(alt in query_lower for alt in alternatives):
                holiday_name = main_name
                break
        
        # Определяем год для поиска праздника
        current_year = datetime.now().year
        next_year = current_year + 1
        
        # Проверяем, указан ли год явно в запросе
        year_match = re.search(r"(\d{4})", query)
        explicit_year = int(year_match.group(1)) if year_match else None
        
        # Проверяем, есть ли указание на "следующий год" или "этот год"
        is_next_year = any(phrase in query_lower for phrase in ["следующ", "будущ"])
        is_this_year = any(phrase in query_lower for phrase in ["этот", "текущ", "нынешн"])
        
        # Определяем, какой год использовать
        if explicit_year:
            search_years = [explicit_year]
        elif is_next_year:
            search_years = [next_year]
        elif is_this_year:
            search_years = [current_year]
        else:
            # Если год не указан, ищем в текущем и следующем году
            search_years = [current_year, next_year]
        
        # Если запрос о конкретном празднике
        if holiday_name:
            matches = []
            found_holiday = False
            
            # Ищем праздник в указанных годах
            for year in search_years:
                holidays = self.hebcal_api.get_holidays_for_year(year=year)
                
                for item in holidays.get("items", []):
                    title_lc = item.get("title", "").lower()
                    
                    # Проверяем, соответствует ли название праздника запросу
                    if any(alt in title_lc for alt in self.HOLIDAY_NAMES.get(holiday_name, [])):
                        g_date = item.get("date", "")
                        
                        # Проверяем, не прошел ли уже праздник в текущем году
                        if year == current_year:
                            try:
                                holiday_date = datetime.strptime(g_date, "%Y-%m-%d").date()
                                today = datetime.now().date()
                                
                                # Если праздник уже прошел и мы ищем в текущем году, пропускаем его
                                if holiday_date < today and len(search_years) > 1:
                                    continue
                            except ValueError:
                                pass
                        
                        h_date = self.hebcal_api.convert_date_to_hebrew(g_date).get("hebrew", "")
                        desc = item.get("description", "")
                        
                        # Если запрос о времени до праздника
                        if is_days_until_query:
                            try:
                                holiday_date = datetime.strptime(g_date, "%Y-%m-%d").date()
                                today = datetime.now().date()
                                days_until = (holiday_date - today).days
                                
                                if days_until >= 0:
                                    days_text = f"До праздника осталось {days_until} дней."
                                else:
                                    days_text = f"Праздник прошел {abs(days_until)} дней назад."
                                
                                explanation = (
                                    f"<b>{item.get('title')}</b> — {g_date} ({h_date})\n"
                                    f"{days_text}"
                                )
                            except ValueError:
                                explanation = f"<b>{item.get('title')}</b> — {g_date} ({h_date})"
                        else:
                            explanation = f"<b>{item.get('title')}</b> — {g_date} ({h_date})"
                        
                        if desc:
                            explanation += f": {desc}"
                        
                        matches.append(explanation)
                        found_holiday = True
            
            if found_holiday:
                # Формируем контекст с информацией о празднике
                year_info = ""
                if explicit_year:
                    year_info = f" в {explicit_year} году"
                elif is_next_year:
                    year_info = f" в {next_year} году (следующий год)"
                elif is_this_year:
                    year_info = f" в {current_year} году (текущий год)"
                
                factual_ctx = f"\n\n<b>Информация о празднике{year_info}:</b>\n" + "\n".join(matches)
                
                # Добавляем информацию о празднике из API
                return self._process_query(query, custom_context=self.system_prompt + factual_ctx)
        
        # Если это не запрос о конкретном празднике или праздник не найден
        return self._get_calendar_context(query)
        
    def _handle_date_conversion(self, query: str) -> str:
        """Обрабатывает запросы на конвертацию дат между григорианским и еврейским календарями."""
        query_lower = query.lower()
        
        # Определяем направление конвертации
        to_hebrew = any(phrase in query_lower for phrase in [
            "по еврейски", "в еврейский", "на иврите", "на еврейском", "в еврейскую"
        ])
        to_gregorian = any(phrase in query_lower for phrase in [
            "по григориански", "в григорианский", "в григорианскую"
        ])
        
        # Если направление не определено, пробуем определить по контексту
        if not to_hebrew and not to_gregorian:
            # Если в запросе есть еврейские месяцы, вероятно, нужна конвертация в григорианский
            hebrew_months = ["нисан", "ияр", "сиван", "таммуз", "ав", "элул", 
                            "тишрей", "хешван", "кислев", "тевет", "шват", "адар"]
            if any(month in query_lower for month in hebrew_months):
                to_gregorian = True
            else:
                # По умолчанию конвертируем в еврейский
                to_hebrew = True
        
        # Извлекаем григорианскую дату из запроса
        if to_hebrew:
            # Сначала проверяем полный формат даты (YYYY-MM-DD)
            date_match = DATE_RE.search(query)
            if date_match:
                y, m, d = map(int, date_match.groups())
                try:
                    greg_date = date(y, m, d)
                    hebrew_data = self.hebcal_api.convert_date_to_hebrew(greg_date)
                    
                    if "error" in hebrew_data:
                        return f"<b>Ошибка конвертации:</b>\n{hebrew_data.get('error', 'Неизвестная ошибка')}"
                    
                    # Получаем дополнительную информацию о дате
                    weekday_ru = {
                        "Monday": "понедельник",
                        "Tuesday": "вторник",
                        "Wednesday": "среда",
                        "Thursday": "четверг",
                        "Friday": "пятница",
                        "Saturday": "суббота",
                        "Sunday": "воскресенье",
                    }.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                    
                    # Получаем информацию о праздниках на эту дату
                    holidays = self.hebcal_api.get_holidays(date=greg_date.strftime("%Y-%m-%d"))
                    holiday_lines = []
                    for h in holidays.get("items", []) or []:
                        title = h.get("title", "")
                        desc = h.get("description", "")
                        line = f"• {title}"
                        if desc:
                            line += f": {desc}"
                        holiday_lines.append(line)
                    
                    # Формируем контекст с результатами конвертации и дополнительной информацией
                    factual_block = (
                        f"<b>Результат конвертации даты:</b>\n\n"
                        f"Григорианская дата <b>{greg_date.strftime('%d.%m.%Y')}</b> ({weekday_ru}) "
                        f"соответствует еврейской дате <b>{hebrew_data.get('hebrew', '')}</b>.\n\n"
                        f"<b>Подробная информация:</b>\n"
                        f"• Еврейский год: {hebrew_data.get('hy', '')}\n"
                        f"• Еврейский месяц: {hebrew_data.get('hm', '')}\n"
                        f"• Еврейский день: {hebrew_data.get('hd', '')}\n"
                    )
                    
                    if holiday_lines:
                        factual_block += f"\n<b>Праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
                    else:
                        factual_block += "\n<b>Праздники и события:</b> На эту дату не приходится особых праздников или событий."
                    
                    # Добавляем информацию о еврейском календаре
                    factual_block += (
                        f"\n\n<b>О еврейском календаре:</b>\n"
                        f"Еврейский календарь основан на лунно-солнечном цикле. "
                        f"Год состоит из 12 или 13 месяцев, в зависимости от високосности. "
                        f"День в еврейском календаре начинается с заходом солнца."
                    )
                    
                    return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)
                except ValueError:
                    pass
            
            # Если полный формат не найден, ищем дату без года (например, "15 июля")
            date_without_year_match = DATE_WITHOUT_YEAR_RE.search(query)
            if date_without_year_match:
                day, month_name = date_without_year_match.groups()
                day = int(day)
                
                # Определяем номер месяца по его названию
                month_number = None
                for month_key, month_num in MONTH_NAME_TO_NUMBER.items():
                    if month_key in month_name.lower():
                        month_number = month_num
                        break
                
                if month_number:
                    # Используем текущий год
                    current_year = datetime.now().year
                    try:
                        greg_date = date(current_year, month_number, day)
                        hebrew_data = self.hebcal_api.convert_date_to_hebrew(greg_date)
                        
                        if "error" in hebrew_data:
                            return f"<b>Ошибка конвертации:</b>\n{hebrew_data.get('error', 'Неизвестная ошибка')}"
                        
                        # Получаем дополнительную информацию о дате
                        weekday_ru = {
                            "Monday": "понедельник",
                            "Tuesday": "вторник",
                            "Wednesday": "среда",
                            "Thursday": "четверг",
                            "Friday": "пятница",
                            "Saturday": "суббота",
                            "Sunday": "воскресенье",
                        }.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                        
                        # Получаем информацию о праздниках на эту дату
                        holidays = self.hebcal_api.get_holidays(date=greg_date.strftime("%Y-%m-%d"))
                        holiday_lines = []
                        for h in holidays.get("items", []) or []:
                            title = h.get("title", "")
                            desc = h.get("description", "")
                            line = f"• {title}"
                            if desc:
                                line += f": {desc}"
                            holiday_lines.append(line)
                        
                        # Формируем контекст с результатами конвертации и дополнительной информацией
                        factual_block = (
                            f"<b>Результат конвертации даты:</b>\n\n"
                            f"Григорианская дата <b>{greg_date.strftime('%d.%m.%Y')}</b> ({weekday_ru}) "
                            f"соответствует еврейской дате <b>{hebrew_data.get('hebrew', '')}</b>.\n\n"
                            f"<b>Подробная информация:</b>\n"
                            f"• Еврейский год: {hebrew_data.get('hy', '')}\n"
                            f"• Еврейский месяц: {hebrew_data.get('hm', '')}\n"
                            f"• Еврейский день: {hebrew_data.get('hd', '')}\n"
                        )
                        
                        if holiday_lines:
                            factual_block += f"\n<b>Праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
                        else:
                            factual_block += "\n<b>Праздники и события:</b> На эту дату не приходится особых праздников или событий."
                        
                        # Добавляем информацию о еврейском календаре
                        factual_block += (
                            f"\n\n<b>О еврейском календаре:</b>\n"
                            f"Еврейский календарь основан на лунно-солнечном цикле. "
                            f"Год состоит из 12 или 13 месяцев, в зависимости от високосности. "
                            f"День в еврейском календаре начинается с заходом солнца."
                        )
                        
                        return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)
                    except ValueError:
                        pass
        
        # Извлекаем еврейскую дату из запроса для конвертации в григорианскую
        if to_gregorian:
            # Ищем еврейский месяц
            hebrew_month_map = {
                "нисан": "Nisan", "ияр": "Iyyar", "сиван": "Sivan", 
                "таммуз": "Tamuz", "ав": "Av", "элул": "Elul",
                "тишрей": "Tishrei", "хешван": "Cheshvan", "кислев": "Kislev", 
                "тевет": "Tevet", "шват": "Shvat", "адар": "Adar"
            }
            
            month = None
            for rus_month, eng_month in hebrew_month_map.items():
                if rus_month in query_lower:
                    month = eng_month
                    break
            
            # Ищем день месяца (1-30)
            day_match = re.search(r"(?<!\d)(\d{1,2})(?!\d)", query)
            
            # Пытаемся найти еврейский год (4-5 цифр)
            year_match = re.search(r"(\d{4,5})", query)
            hebrew_year = int(year_match.group(1)) if year_match else None
            
            # Если год не указан, используем текущий еврейский год
            if not hebrew_year and month and day_match:
                # Получаем текущую еврейскую дату для определения текущего еврейского года
                current_hebrew_date = self.hebcal_api.get_current_hebrew_date()
                hebrew_year = int(current_hebrew_date.get("hy", datetime.now().year + 3760))  # Примерное соответствие
            
            if month and day_match and hebrew_year:
                try:
                    hebrew_day = int(day_match.group(1))
                    
                    # Создаем словарь с еврейской датой
                    hebrew_date = {
                        "hy": hebrew_year,
                        "hm": month,
                        "hd": hebrew_day
                    }
                    
                    # Конвертируем в григорианскую дату
                    greg_data = self.hebcal_api.convert_date_to_gregorian(hebrew_date)
                    
                    if "error" in greg_data:
                        return f"<b>Ошибка конвертации:</b>\n{greg_data.get('error', 'Неизвестная ошибка')}"
                    
                    # Создаем объект даты для получения дня недели
                    try:
                        greg_date = date(int(greg_data.get('gy', '')), int(greg_data.get('gm', '')), int(greg_data.get('gd', '')))
                        weekday_ru = {
                            "Monday": "понедельник",
                            "Tuesday": "вторник",
                            "Wednesday": "среда",
                            "Thursday": "четверг",
                            "Friday": "пятница",
                            "Saturday": "суббота",
                            "Sunday": "воскресенье",
                        }.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                        
                        # Получаем информацию о праздниках на эту дату
                        holidays = self.hebcal_api.get_holidays(date=greg_date.strftime("%Y-%m-%d"))
                        holiday_lines = []
                        for h in holidays.get("items", []) or []:
                            title = h.get("title", "")
                            desc = h.get("description", "")
                            line = f"• {title}"
                            if desc:
                                line += f": {desc}"
                            holiday_lines.append(line)
                        
                        # Формируем контекст с результатами конвертации и дополнительной информацией
                        factual_block = (
                            f"<b>Результат конвертации даты:</b>\n\n"
                            f"Еврейская дата <b>{hebrew_day} {month} {hebrew_year}</b> "
                            f"соответствует григорианской дате <b>{greg_date.strftime('%d.%m.%Y')}</b> ({weekday_ru}).\n\n"
                            f"<b>Подробная информация:</b>\n"
                            f"• Григорианский год: {greg_data.get('gy', '')}\n"
                            f"• Григорианский месяц: {greg_data.get('gm', '')}\n"
                            f"• Григорианский день: {greg_data.get('gd', '')}\n"
                            f"• День недели: {weekday_ru}\n"
                        )
                        
                        if holiday_lines:
                            factual_block += f"\n<b>Праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
                        else:
                            factual_block += "\n<b>Праздники и события:</b> На эту дату не приходится особых праздников или событий."
                        
                        # Добавляем информацию о еврейском календаре
                        factual_block += (
                            f"\n\n<b>О еврейском календаре:</b>\n"
                            f"Еврейский календарь основан на лунно-солнечном цикле. "
                            f"Год состоит из 12 или 13 месяцев, в зависимости от високосности. "
                            f"День в еврейском календаре начинается с заходом солнца."
                        )
                        
                        return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)
                    except (ValueError, TypeError):
                        # Если не удалось создать объект даты, возвращаем простой ответ
                        greg_date_str = f"{greg_data.get('gd', '')}.{greg_data.get('gm', '')}.{greg_data.get('gy', '')}"
                        factual_block = (
                            f"<b>Результат конвертации даты:</b>\n\n"
                            f"Еврейская дата <b>{hebrew_day} {month} {hebrew_year}</b> "
                            f"соответствует григорианской дате <b>{greg_date_str}</b>."
                        )
                        return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)
                except (ValueError, KeyError):
                    pass
        
        # Если не удалось извлечь дату или выполнить конвертацию
        return "Не удалось распознать дату в вашем запросе. Пожалуйста, укажите дату в формате ДД месяц (например, '15 июля') для конвертации в еврейскую дату, или укажите еврейскую дату (например, '15 нисан') для конвертации в григорианскую."

    def _handle_date_diff(self, query: str) -> str:
        greg_dates = DATE_RE.findall(query)
        dates: list[date] = []
        for y, m, d in greg_dates[:2]:
            try:
                dates.append(datetime(int(y), int(m), int(d)).date())
            except ValueError:
                pass

        if len(dates) < 2:
            parts = re.split(r"и|between|между|—|-|to", query, maxsplit=1)
            if len(parts) == 2:
                dates = [self._extract_any_date(p.strip()) for p in parts]

        if len(dates) != 2 or None in dates:
            return self._process_query(query)

        delta_days = abs((dates[1] - dates[0]).days)
        heb1 = self.hebcal_api.convert_date_to_hebrew(dates[0]).get("hebrew", "")
        heb2 = self.hebcal_api.convert_date_to_hebrew(dates[1]).get("hebrew", "")

        diff_ctx = (
            f"<b>Разница между датами:</b> {delta_days} дн.\n"
            f"{dates[0]} (григ.) — {heb1}\n"
            f"{dates[1]} (григ.) — {heb2}"
        )
        return self._process_query(query, custom_context=self.system_prompt + "\n\n" + diff_ctx)

    def _extract_any_date(self, text_: str) -> date | None:
        if match := DATE_RE.search(text_):
            y, m, d = map(int, match.groups())
            try:
                return datetime(y, m, d).date()
            except ValueError:
                return None
        try:
            return self.extract_relative_date(text_)
        except Exception:
            return None

    def extract_relative_date(self, query: str) -> date | None:
        query_lower = query.lower()
        today = datetime.now().date()
        
        # Мультиязычные шаблоны для относительных дат
        patterns = [
            # Русский
            (r"(через|спустя)\s*(\d+)\s*(дн[яейь]|день|дня|дней)", lambda n: timedelta(days=n)),  # через 2 дня
            (r"(\d+)\s*(дн[яейь]|день|дня|дней)\s*(назад|тому назад)", lambda n: timedelta(days=-n)),  # 2 дня назад
            (r"(через|спустя)\s*(\d+)\s*(недел[ьию]|недели|недель)", lambda n: timedelta(weeks=n)),  # через 3 недели
            (r"(\d+)\s*(недел[ьию]|недели|недель)\s*(назад|тому назад)", lambda n: timedelta(weeks=-n)),  # 3 недели назад
            (r"(через|спустя)\s*(\d+)\s*(месяц[аев]*|мес\.?)", lambda n: relativedelta(months=+n)),  # через 2 месяца
            (r"(\d+)\s*(месяц[аев]*|мес\.?)\s*(назад|тому назад)", lambda n: relativedelta(months=-n)),  # 2 месяца назад
            (r"(через|спустя)\s*(\d+)\s*(год[ауы]?|лет|года)", lambda n: relativedelta(years=+n)),  # через 1 год
            (r"(\d+)\s*(год[ауы]?|лет|года)\s*(назад|тому назад)", lambda n: relativedelta(years=-n)),  # 1 год назад
            
            # English
            (r"(in)\s*(\d+)\s*(days|day)", lambda n: timedelta(days=n)),  # in 2 days
            (r"(\d+)\s*(days|day)\s*(ago)", lambda n: timedelta(days=-n)),  # 2 days ago
            (r"(in)\s*(\d+)\s*(weeks|week)", lambda n: timedelta(weeks=n)),  # in 3 weeks
            (r"(\d+)\s*(weeks|week)\s*(ago)", lambda n: timedelta(weeks=-n)),  # 3 weeks ago
            (r"(in)\s*(\d+)\s*(months|month)", lambda n: relativedelta(months=+n)),  # in 2 months
            (r"(\d+)\s*(months|month)\s*(ago)", lambda n: relativedelta(months=-n)),  # 2 months ago
            (r"(in)\s*(\d+)\s*(years|year)", lambda n: relativedelta(years=+n)),  # in 1 year
            (r"(\d+)\s*(years|year)\s*(ago)", lambda n: relativedelta(years=-n)),  # 1 year ago
            
            # Hebrew (примерные шаблоны, можно расширить)
            (r"(בעוד)\s*(\d+)\s*(ימים|יום)", lambda n: timedelta(days=n)),  # בעוד 2 ימים
            (r"(\d+)\s*(ימים|יום)\s*(לפני|אחורה)", lambda n: timedelta(days=-n)),  # 2 ימים לפני
            (r"(בעוד)\s*(\d+)\s*(שבועות|שבוע)", lambda n: timedelta(weeks=n)),  # בעוד 3 שבועות
            (r"(\d+)\s*(שבועות|שבוע)\s*(לפני|אחורה)", lambda n: timedelta(weeks=-n)),  # 3 שבועות לפני
        ]

        for pattern, delta_func in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    number = int(match.group(2))  # Вторая группа - число
                    return today + delta_func(number)
                except:
                    continue

        # Мультиязычные фиксированные выражения
        fixed_dates = {
            # Russian
            "позавчера": -2, "вчера": -1, "сегодня": 0, "завтра": 1, "послезавтра": 2,
            # English
            "day before yesterday": -2, "yesterday": -1, "today": 0, "tomorrow": 1, "day after tomorrow": 2,
            # Hebrew
            "שלשום": -2, "אתמול": -1, "היום": 0, "מחר": 1, "מחרתיים": 2
        }

        for phrase, offset in fixed_dates.items():
            if phrase.lower() in query_lower:
                return today + timedelta(days=offset)

        # Обработка числительных без явного указания единиц (по умолчанию дни)
        simple_num_patterns = [
            r"(через|спустя)\s*(\d+)",  # русский
            r"(in)\s*(\d+)",  # english
            r"(בעוד)\s*(\d+)"  # hebrew
        ]
        
        for pattern in simple_num_patterns:
            match = re.search(pattern, query_lower)
            if match and not any(w in query_lower for w in ["week", "month", "year", "недел", "месяц", "год", "שבוע", "חודש", "שנה"]):
                try:
                    days = int(match.group(2))
                    return today + timedelta(days=days)
                except:
                    pass

        # Попытка парсинга даты с автоматическим определением языка
        try:
            parsed = dateparser.parse(
                query,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': datetime.now(),
                    'LANGUAGES': ['ru', 'en', 'he']  # Поддерживаемые языки
                }
            )
            if parsed:
                return parsed.date()
        except:
            pass

        return None

    def _get_calendar_context(self, query: str) -> str:
        # Определяем, содержит ли запрос слово "завтра" или "послезавтра"
        query_lower = query.lower()
        is_tomorrow = "завтра" in query_lower and "послезавтра" not in query_lower
        is_day_after_tomorrow = "послезавтра" in query_lower
        
        target_date = self._extract_any_date(query) or datetime.now().date()
        today = datetime.now().date()
        days_diff = (target_date - today).days
        
        greg_date = target_date.strftime("%Y-%m-%d")
        hebrew_data = self.hebcal_api.convert_date_to_hebrew(target_date)

        weekday_ru = {
            "Monday": "понедельник",
            "Tuesday": "вторник",
            "Wednesday": "среда",
            "Thursday": "четверг",
            "Friday": "пятница",
            "Saturday": "суббота",
            "Sunday": "воскресенье",
        }.get(target_date.strftime("%A"), target_date.strftime("%A"))

        hebrew_date = hebrew_data.get("hebrew", "")
        heb_year = hebrew_data.get("hy", "")

        holidays = self.hebcal_api.get_holidays(date=greg_date)
        holiday_lines = []
        for h in holidays.get("items", []) or []:
            title = h.get("title", "")
            desc = h.get("description", "")
            h_date = h.get("date", "")
            h_hebrew = self.hebcal_api.convert_date_to_hebrew(h_date).get("hebrew", "")
            line = f"• {title} — {h_date} ({h_hebrew})"
            if desc:
                line += f": {desc}"
            holiday_lines.append(line)

        # Добавляем явное указание для всех относительных дат
        date_prefix = ""
        if is_tomorrow:
            date_prefix = "Завтра будет: "
        elif is_day_after_tomorrow:
            date_prefix = "Послезавтра будет: "
        elif days_diff > 0:
            # Склонение слова "день"
            day_word = "день"
            if days_diff % 10 == 1 and days_diff % 100 != 11:
                day_word = "день"
            elif 2 <= days_diff % 10 <= 4 and (days_diff % 100 < 10 or days_diff % 100 >= 20):
                day_word = "дня"
            else:
                day_word = "дней"
            date_prefix = f"Через {days_diff} {day_word} будет: "
        elif days_diff < 0:
            abs_days = abs(days_diff)
            # Склонение слова "день"
            day_word = "день"
            if abs_days % 10 == 1 and abs_days % 100 != 11:
                day_word = "день"
            elif 2 <= abs_days % 10 <= 4 and (abs_days % 100 < 10 or abs_days % 100 >= 20):
                day_word = "дня"
            else:
                day_word = "дней"
            date_prefix = f"{abs_days} {day_word} назад было: "
        
        factual_block = (
            f"<b>Фактическая дата:</b>\n"
            f"{date_prefix}{hebrew_date} (соответствует {greg_date}).\n"
            f"<b>День недели:</b> {weekday_ru}\n\n"
            f"<b>Праздники:</b>\n"
            + ("\n".join(holiday_lines) if holiday_lines else "Нет известных праздников в эту дату.")
            + "\n\n<b>О еврейском календаре:</b>\nЕврейский календарь основан на лунно‑солнечном цикле. Год по еврейскому летоисчислению: "
            + str(heb_year)
        )

        return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)

    def _process_query(self, query: str, custom_context: str | None = None) -> str:
        context = custom_context or self._build_context_from_search(query)
        response = self.openrouter_api.generate_response(prompt=query, context=context)
        return self._clean_html_tags(response)

    def _build_context_from_search(self, query: str) -> str:
        search_results = self.sefaria_api.search_texts(query)
        context_texts: list[str] = []
        for hit in search_results[:3]:
            ref = hit.get("_source", {}).get("ref")
            if ref:
                text_data = self.sefaria_api.get_text(ref)
                if text_data and "text" in text_data:
                    text = text_data["text"]
                    if isinstance(text, list):
                        text = "\n".join(map(str, text))
                    context_texts.append(f"Источник: {ref}\nТекст: {text}")

        ctx = self.system_prompt
        if context_texts:
            ctx += "\n\nРелевантные тексты из Sefaria:\n\n" + "\n\n".join(context_texts)
        return ctx

    def _clean_html_tags(self, text: str) -> str:
        text = text.replace("<б>", "<b>").replace("</б>", "</b>")
        text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        text = text.replace("<ul>", "").replace("</ul>", "")
        text = text.replace("<li>", "• ").replace("</li>", "\n")
        text = text.replace("<ol>", "").replace("</ol>", "")
        # Обработка тега <p>, который не поддерживается в Telegram
        text = text.replace("<p>", "").replace("</p>", "\n")
        # Список тегов, разрешенных в Telegram
        allowed = {"b", "u", "a", "pre", "code", "i", "em", "blockquote", "s"}
        # Исправленное регулярное выражение (один обратный слеш вместо двух)
        return re.sub(r"</?(?!(%s))(\w+)([^>]*?)>" % "|".join(allowed), "", text)

    @staticmethod
    def _build_system_prompt() -> str:
        return """
Ты — эксперт по еврейским текстам, традициям и календарю. Форматируй ответы следующим образом:

1. Источники:
- Всегда указывай точные источники цитат в скобках (пример: Берешит 1:1, Мишна Сангедрин 4:5)
- Для мудрецов и комментаторов указывай период и регион (пример: Раши (Франция, XI век))

2. Объяснения:
- Для всех специальных терминов давай краткое пояснение в скобках
- Сложные концепции объясняй простым языком, но без упрощения содержания
- При упоминании исторических лиц добавляй краткую справку
- При упоминании дат указывай их как по григорианскому, так и по еврейскому календарю

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

<b>Работа с датами и календарём</b>

1. Распознавай даты следующим образом:
   • Извлеки все упоминания дат из запроса USER.
   • Нормализуй их в формате YYYY-MM-DD по григорианскому календарю.
   • Конвертируй в еврейскую дату из григорианской или обратно через доступные методы, если пользователь спрашивает как эта дата будет на еврейском или григоранском.
   • Все даты и календарные события должны браться только из полученных данных.
   • Ты должна возвращать ТОЛЬКО даты из полученных данных без изменений. Не пытайся вычислять их самостоятельно.
   • Если ты ты не получил данные, попроси пользователя уточнить запрос.



Формат ответа:
[Основной ответ]
[Пояснения к терминам]
[Источники и справки]

<blockquote> Формулируйте запросы максимально чётко для получения полезной информации.</blockquote>
<blockquote>⚠️ <b>Внимание:</b> Информация приведена для ознакомления. Для получения авторитетного мнения рекомендуется проконсультироваться с раввином.</blockquote>
"""
