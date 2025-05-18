from __future__ import annotations

import re
import html
import logging
from datetime import datetime, timedelta, date
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta
from typing import Dict, Any, List, Optional, Tuple, Union

from openrouter_api import OpenRouterAPI
from sefaria_api import SefariaAPI
from hebcal_api import HebcalAPI

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Регулярные выражения для распознавания дат
DATE_RE = re.compile(r"(\d{4})[- /.](\d{1,2})[- /.](\d{1,2})")  # Полный формат с годом: 2023-05-15
# Улучшенное регулярное выражение для дат без года, которое лучше обрабатывает различные форматы
DATE_WITHOUT_YEAR_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:[-./]|\s+)?\s*([а-яА-Яa-zA-Z]+)")  # Формат без года: 15 мая, 12 декабря, 29 октября
# Регулярное выражение для формата "DD месяц YYYY"
DATE_WITH_YEAR_TEXT_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:[-./]|\s+)?\s*([а-яА-Яa-zA-Z]+)\s*(?:[-./]|\s+)?\s*(\d{4})")  # Формат с годом: 15 мая 2023, 12 декабря 1948

# Словарь с названиями еврейских месяцев
HEBREW_MONTH_MAP = {
    "нисан": "Nisan", "ияр": "Iyyar", "сиван": "Sivan", 
    "таммуз": "Tamuz", "тамуз": "Tamuz", "ав": "Av", "элул": "Elul",
    "тишрей": "Tishrei", "хешван": "Cheshvan", "кислев": "Kislev", 
    "тевет": "Tevet", "шват": "Shvat", "адар": "Adar", "адар i": "Adar I", "адар ii": "Adar II"
}

# Словарь для нормализации названий еврейских месяцев (учитывает различные варианты написания)
HEBREW_MONTH_NORMALIZE = {
    # Основные варианты
    "nisan": "Nisan", "iyyar": "Iyyar", "sivan": "Sivan", 
    "tamuz": "Tamuz", "tammuz": "Tamuz", "av": "Av", "elul": "Elul",
    "tishrei": "Tishrei", "tishri": "Tishrei", "cheshvan": "Cheshvan", 
    "heshvan": "Cheshvan", "kislev": "Kislev", "tevet": "Tevet", 
    "shvat": "Shvat", "sh'vat": "Shvat", "adar": "Adar", 
    "adar i": "Adar I", "adar 1": "Adar I", "adar ii": "Adar II", "adar 2": "Adar II",
    
    # Варианты с апострофом
    "sh'vat": "Shvat", "adar i'": "Adar I", "adar ii'": "Adar II",
    
    # Русские варианты (для обратной совместимости)
    "нисан": "Nisan", "ияр": "Iyyar", "сиван": "Sivan", 
    "таммуз": "Tamuz", "ав": "Av", "элул": "Elul",
    "тишрей": "Tishrei", "хешван": "Cheshvan", "кислев": "Kislev", 
    "тевет": "Tevet", "шват": "Shvat", "адар": "Adar", 
    "адар i": "Adar I", "адар 1": "Adar I", "адар ii": "Adar II", "адар 2": "Adar II"
}

# Словарь с днями недели
WEEKDAY_RU = {
    "Monday": "понедельник",
    "Tuesday": "вторник",
    "Wednesday": "среда",
    "Thursday": "четверг",
    "Friday": "пятница",
    "Saturday": "суббота",
    "Sunday": "воскресенье",
}

# Словарь для преобразования названий месяцев в числа
MONTH_NAME_TO_NUMBER = {
    # Русские названия месяцев (различные формы, включая падежные формы)
    "январ": 1, "янв": 1, "января": 1, "январе": 1, "январю": 1, "январём": 1, "январем": 1,
    "феврал": 2, "фев": 2, "февраля": 2, "феврале": 2, "февралю": 2, "февралём": 2, "февралем": 2,
    "март": 3, "мар": 3, "марта": 3, "марте": 3, "марту": 3, "мартом": 3,
    "апрел": 4, "апр": 4, "апреля": 4, "апреле": 4, "апрелю": 4, "апрелем": 4,
    "ма": 5, "май": 5, "мая": 5, "мае": 5, "маю": 5, "маем": 5,
    "июн": 6, "июня": 6, "июне": 6, "июню": 6, "июнем": 6,
    "июл": 7, "июля": 7, "июле": 7, "июлю": 7, "июлем": 7,
    "август": 8, "авг": 8, "августа": 8, "августе": 8, "августу": 8, "августом": 8,
    "сентябр": 9, "сен": 9, "сентября": 9, "сентябре": 9, "сентябрю": 9, "сентябрём": 9, "сентябрем": 9,
    "октябр": 10, "окт": 10, "октября": 10, "октябре": 10, "октябрю": 10, "октябрём": 10, "октябрем": 10,
    "ноябр": 11, "ноя": 11, "ноября": 11, "ноябре": 11, "ноябрю": 11, "ноябрём": 11, "ноябрем": 11,
    "декабр": 12, "дек": 12, "декабря": 12, "декабре": 12, "декабрю": 12, "декабрём": 12, "декабрем": 12,
    
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
        
    def _build_system_prompt(self) -> str:
        """
        Создает системный промпт для модели.
        
        Returns:
            str: Системный промпт
        """
        return """
Ты — эксперт по иудаизму, еврейским текстам и традициям. Твоя задача — давать точные, информативные и уважительные ответы на вопросы о еврейской религии, культуре, истории и традициях.

Правила:
1. Отвечай на том языке на котором задан вопрос.
2. Используй уважительный тон и избегай оценочных суждений.
3. Если не знаешь ответа, честно признай это.
4. Приводи источники и цитаты, когда это уместно.
5. Объясняй сложные концепции простым языком.
6. Используй HTML-форматирование для структурирования ответа (<b>жирный</b>, <i>курсив</i>, <u>подчеркнутый</u>).
7. Не используй Markdown-форматирование.
8. Добавляй предупреждение в конце.


Когда отвечаешь на вопросы о еврейских законах (галахе):
- Указывай, что существуют разные мнения и традиции.
- Отмечай различия между сефардской, ашкеназской и другими традициями, если они существенны.
- Подчеркивай, что для практических решений следует консультироваться с раввином.

Когда цитируешь тексты:
- Указывай точный источник (книга, глава, стих).
- По возможности приводи текст на иврите и его перевод.
- Объясняй контекст цитаты.

Когда отвечаешь на вопросы о календаре и датах:
- Указывай даты по григорианскому и еврейскому календарям.
- Объясняй особенности праздников и постов.
- Указывай время начала и окончания Шаббата и праздников, если это уместно.

<blockquote> Формулируйте запросы максимально чётко для получения полезной информации.</blockquote>
<blockquote>⚠️ <b>Внимание:</b> Информация приведена для ознакомления. Для получения авторитетного мнения рекомендуется проконсультироваться с раввином.</blockquote>
"""

    def handle_query(self, query: str) -> str:
        """
        Обрабатывает запрос пользователя и возвращает ответ.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Ответ на запрос
        """
        try:
            # Логируем входящий запрос
            logger.info(f"Получен запрос: {query}")
            
            # Определяем категорию запроса
            category = self._route_query(query)
            logger.info(f"Определена категория запроса: {category}")
            
            # Обрабатываем запрос в зависимости от категории
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
            
            # Если категория не определена, обрабатываем как обычный запрос
            return self._process_query(query)
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}", exc_info=True)
            return f"Произошла ошибка при обработке запроса: {str(e)}"

    def _route_query(self, query: str) -> str:
        """
        Определяет категорию запроса пользователя.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Категория запроса
        """
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
        try:
            logger.info(f"Определение категории запроса: {query}")
            category = self.openrouter_api.generate_response(prompt=query, context=router_prompt).strip().lower()
            logger.info(f"Определена категория: {category}")
            return category
        except Exception as e:
            logger.error(f"Ошибка при определении категории запроса: {e}", exc_info=True)
            # В случае ошибки возвращаем общую категорию
            return "general"

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
        """
        Обрабатывает запросы, связанные с календарными событиями.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Ответ на запрос
        """
        try:
            query_lower = query.lower()
            logger.info(f"Обработка календарного события: {query}")
            
            # Проверяем, является ли запрос запросом о конкретной дате
            is_specific_date_query = any(phrase in query_lower for phrase in [
                "какая дата", "какой день", "что за день", "какое число", 
                "какая была дата", "какой был день", "что за день был"
            ])
            
            # Если это запрос о конкретной дате, сразу возвращаем календарный контекст
            if is_specific_date_query:
                logger.info("Определен запрос о конкретной дате")
                return self._get_calendar_context(query)
            
            # Проверяем, является ли запрос запросом на конвертацию даты
            is_date_conversion = any(phrase in query_lower for phrase in [
                "конвертир", "перевед", "как будет", "какая дата", "какой день", 
                "по еврейски", "по григориански", "в еврейский", "в григорианский",
                "на иврите", "на еврейском"
            ])
            
            # Если это запрос на конвертацию даты, вызываем специальный обработчик
            if is_date_conversion:
                logger.info("Определен запрос на конвертацию даты")
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
            
            logger.info(f"Определен праздник: {holiday_name}")
            
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
            
            logger.info(f"Годы для поиска праздника: {search_years}")
            
            # Если запрос о конкретном празднике
            if holiday_name:
                matches = []
                found_holiday = False
                
                # Ищем праздник в указанных годах
                for year in search_years:
                    logger.info(f"Поиск праздника {holiday_name} в {year} году")
                    holidays = self.hebcal_api.get_holidays_for_year(year=year)
                    
                    if "error" in holidays:
                        logger.error(f"Ошибка при получении праздников: {holidays['error']}")
                        continue
                    
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
                                        logger.info(f"Праздник {title_lc} уже прошел в этом году, пропускаем")
                                        continue
                                except ValueError as e:
                                    logger.error(f"Ошибка при парсинге даты праздника: {e}")
                                    continue
                            
                            # Получаем еврейскую дату и проверяем результат
                            hebrew_data = self.hebcal_api.convert_date_to_hebrew(g_date)
                            if "error" in hebrew_data:
                                logger.error(f"Ошибка при конвертации даты: {hebrew_data['error']}")
                                h_date = "Дата не определена"
                            else:
                                h_date = hebrew_data.get("hebrew", "")
                            
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
                                except ValueError as e:
                                    logger.error(f"Ошибка при расчете дней до праздника: {e}")
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
                    logger.info(f"Найдена информация о празднике {holiday_name}")
                    
                    # Добавляем информацию о празднике из API
                    return self._process_query(query, custom_context=self.system_prompt + factual_ctx)
            
            # Если это не запрос о конкретном празднике или праздник не найден
            logger.info("Праздник не найден или запрос не о празднике, возвращаем календарный контекст")
            return self._get_calendar_context(query)
        except Exception as e:
            logger.error(f"Ошибка при обработке календарного события: {e}", exc_info=True)
            return f"Произошла ошибка при обработке запроса о календарном событии: {str(e)}"
        
    def _handle_date_conversion(self, query: str) -> str:
        """
        Обрабатывает запросы на конвертацию дат между григорианским и еврейским календарями.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Ответ на запрос с результатами конвертации
        """
        try:
            # Добавляем подробное логирование
            logger.info(f"Обработка запроса на конвертацию даты: {query}")
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
                        weekday_ru = WEEKDAY_RU.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                        
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
                            factual_block += f"\n<b>Ближайшие праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
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
                    except ValueError as e:
                        logger.error(f"Ошибка при создании даты: {e}")
                
                # Сначала ищем формат "DD месяц YYYY" (например, "15 июля 1948")
                date_with_year_text_match = DATE_WITH_YEAR_TEXT_RE.search(query)
                if date_with_year_text_match:
                    day, month_name, year = date_with_year_text_match.groups()
                    day = int(day)
                    year = int(year)
                    
                    # Определяем номер месяца по его названию
                    month_number = None
                    for month_key, month_num in MONTH_NAME_TO_NUMBER.items():
                        if month_key in month_name.lower():
                            month_number = month_num
                            break
                    
                    if month_number:
                        # Используем указанный год
                        logger.info(f"Распознана дата с годом: {day} {month_name} {year}")
                        try:
                            greg_date = date(year, month_number, day)
                            hebrew_data = self.hebcal_api.convert_date_to_hebrew(greg_date)
                            
                            if "error" in hebrew_data:
                                return f"<b>Ошибка конвертации:</b>\n{hebrew_data.get('error', 'Неизвестная ошибка')}"
                            
                            # Получаем дополнительную информацию о дате
                            weekday_ru = WEEKDAY_RU.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                            
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
                                factual_block += f"\n<b>Ближайшие праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
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
                        except ValueError as e:
                            logger.error(f"Ошибка при создании даты с годом: {e}")
                
                # Если формат с годом не найден, ищем дату без года (например, "15 июля")
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
                        # Проверяем, есть ли год в запросе
                        year_match = re.search(r"(\d{4})", query)
                        if year_match:
                            # Используем найденный год
                            year = int(year_match.group(1))
                            logger.info(f"Найден год в запросе: {year}")
                        else:
                            # Используем текущий год
                            year = datetime.now().year
                            logger.info(f"Год не найден в запросе, используем текущий: {year}")
                        try:
                            greg_date = date(year, month_number, day)
                            hebrew_data = self.hebcal_api.convert_date_to_hebrew(greg_date)
                            
                            if "error" in hebrew_data:
                                return f"<b>Ошибка конвертации:</b>\n{hebrew_data.get('error', 'Неизвестная ошибка')}"
                            
                            # Получаем дополнительную информацию о дате
                            weekday_ru = WEEKDAY_RU.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                            
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
                                factual_block += f"\n<b>Ближайшие праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
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
                        except ValueError as e:
                            logger.error(f"Ошибка при создании даты без года: {e}")
            
            # Извлекаем еврейскую дату из запроса для конвертации в григорианскую
            if to_gregorian:
                # Ищем еврейский месяц
                month = None
                # Сначала ищем по словарю HEBREW_MONTH_MAP (для обратной совместимости)
                for rus_month, eng_month in HEBREW_MONTH_MAP.items():
                    if rus_month in query_lower:
                        month = eng_month
                        break
                
                # Если месяц не найден, ищем по словарю HEBREW_MONTH_NORMALIZE
                if not month:
                    # Ищем все слова в запросе, которые могут быть названиями месяцев
                    words = re.findall(r'\b[a-zA-Zа-яА-Я\']+\b', query_lower)
                    for word in words:
                        normalized_month = HEBREW_MONTH_NORMALIZE.get(word.lower())
                        if normalized_month:
                            month = normalized_month
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
                            weekday_ru = WEEKDAY_RU.get(greg_date.strftime("%A"), greg_date.strftime("%A"))
                            
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
                                factual_block += f"\n<b>Ближайшие праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
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
                        except (ValueError, TypeError) as e:
                            logger.error(f"Ошибка при создании объекта даты: {e}")
                            # Если не удалось создать объект даты, возвращаем простой ответ
                            greg_date_str = f"{greg_data.get('gd', '')}.{greg_data.get('gm', '')}.{greg_data.get('gy', '')}"
                            factual_block = (
                                f"<b>Результат конвертации даты:</b>\n\n"
                                f"Еврейская дата <b>{hebrew_day} {month} {hebrew_year}</b> "
                                f"соответствует григорианской дате <b>{greg_date_str}</b>."
                            )
                            return self._process_query(query, custom_context=self.system_prompt + "\n\n" + factual_block)
                    except (ValueError, KeyError) as e:
                        logger.error(f"Ошибка при конвертации еврейской даты: {e}")
            
            # Если не удалось извлечь дату или выполнить конвертацию
            return "Не удалось распознать дату в вашем запросе. Пожалуйста, укажите дату в формате ДД месяц (например, '15 июля') для конвертации в еврейскую дату, или укажите еврейскую дату (например, '15 нисан') для конвертации в григорианскую."
        except Exception as e:
            logger.error(f"Ошибка при конвертации даты: {e}", exc_info=True)
            return f"Произошла ошибка при конвертации даты: {str(e)}"
            
    def _handle_date_diff(self, query: str) -> str:
        """
        Обрабатывает запросы о разнице между двумя датами.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Ответ на запрос
        """
        try:
            # Логируем входящий запрос
            logger.info(f"Обработка запроса о разнице между датами: {query}")
            
            # Извлекаем даты из запроса
            dates = self._extract_dates_from_query(query)
            
            if len(dates) < 2:
                return "Для расчета разницы между датами необходимо указать две даты. Пожалуйста, укажите две даты в формате ДД.ММ.ГГГГ или ДД месяц ГГГГ."
            
            # Берем первые две даты
            date1, date2 = dates[:2]
            
            # Рассчитываем разницу в днях
            diff_days = abs((date2 - date1).days)
            
            # Рассчитываем разницу в месяцах и годах
            if date1 > date2:
                date1, date2 = date2, date1  # Меняем местами, чтобы date1 была раньше
                
            years = date2.year - date1.year
            months = date2.month - date1.month
            
            if months < 0:
                years -= 1
                months += 12
                
            # Проверяем, не превышает ли день в date2 количество дней в месяце date1
            day1 = date1.day
            day2 = date2.day
            
            # Получаем последний день месяца date1
            last_day = (date1.replace(day=1) + relativedelta(months=1) - timedelta(days=1)).day
            
            if day1 > last_day:
                day1 = last_day
                
            if day2 < day1:
                months -= 1
                if months < 0:
                    years -= 1
                    months += 12
            
            # Форматируем ответ
            result = f"<b>Разница между датами:</b>\n\n"
            result += f"Дата 1: {date1.strftime('%d.%m.%Y')}\n"
            result += f"Дата 2: {date2.strftime('%d.%m.%Y')}\n\n"
            
            # Добавляем информацию о разнице
            result += f"<b>Разница составляет:</b>\n"
            result += f"• {diff_days} дней\n"
            
            if years > 0 or months > 0:
                years_text = f"{years} {'год' if years == 1 else 'года' if 2 <= years <= 4 else 'лет'}" if years > 0 else ""
                months_text = f"{months} {'месяц' if months == 1 else 'месяца' if 2 <= months <= 4 else 'месяцев'}" if months > 0 else ""
                
                if years > 0 and months > 0:
                    result += f"• {years_text} и {months_text}\n"
                elif years > 0:
                    result += f"• {years_text}\n"
                elif months > 0:
                    result += f"• {months_text}\n"
            
            # Добавляем информацию о неделях
            weeks = diff_days // 7
            remaining_days = diff_days % 7
            
            if weeks > 0:
                weeks_text = f"{weeks} {'неделя' if weeks == 1 else 'недели' if 2 <= weeks <= 4 else 'недель'}"
                days_text = f"{remaining_days} {'день' if remaining_days == 1 else 'дня' if 2 <= remaining_days <= 4 else 'дней'}" if remaining_days > 0 else ""
                
                if remaining_days > 0:
                    result += f"• {weeks_text} и {days_text}\n"
                else:
                    result += f"• {weeks_text}\n"
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при расчете разницы между датами: {e}", exc_info=True)
            return f"Произошла ошибка при расчете разницы между датами: {str(e)}"
    
    def _extract_dates_from_query(self, query: str) -> List[date]:
        """
        Извлекает даты из запроса пользователя.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            List[date]: Список объектов date
        """
        dates = []
        
        # Ищем даты в формате YYYY-MM-DD или DD.MM.YYYY
        date_matches = re.finditer(r"(\d{1,2})[./](\d{1,2})[./](\d{4})|(\d{4})-(\d{1,2})-(\d{1,2})", query)
        
        for match in date_matches:
            try:
                if match.group(1):  # Формат DD.MM.YYYY
                    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    dates.append(date(y, m, d))
                else:  # Формат YYYY-MM-DD
                    y, m, d = int(match.group(4)), int(match.group(5)), int(match.group(6))
                    dates.append(date(y, m, d))
            except ValueError as e:
                logger.error(f"Ошибка при создании объекта даты: {e}")
        
        # Ищем даты в формате "DD месяц YYYY" или "DD месяц"
        date_without_year_matches = re.finditer(r"(\d{1,2})\s+([а-яА-Яa-zA-Z]+)(?:\s+(\d{4}))?", query)
        
        for match in date_without_year_matches:
            try:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3)) if match.group(3) else datetime.now().year
                
                # Определяем номер месяца по его названию
                month_number = None
                for month_key, month_num in MONTH_NAME_TO_NUMBER.items():
                    if month_key in month_name:
                        month_number = month_num
                        break
                
                if month_number:
                    dates.append(date(year, month_number, day))
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка при создании объекта даты из текста: {e}")
        
        return dates
    
    def _get_calendar_context(self, query: str) -> str:
        """
        Получает контекст с календарной информацией.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Контекст с календарной информацией
        """
        try:
            # Определяем, о какой дате идет речь (сегодня, завтра, вчера и т.д.)
            query_lower = query.lower()
            
            # Пытаемся извлечь конкретную дату из запроса
            specific_date = None
            
            # Проверяем формат YYYY-MM-DD или DD.MM.YYYY
            date_match = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})|(\d{4})-(\d{1,2})-(\d{1,2})", query_lower)
            if date_match:
                try:
                    if date_match.group(1):  # Формат DD.MM.YYYY
                        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                        specific_date = date(y, m, d)
                    else:  # Формат YYYY-MM-DD
                        y, m, d = int(date_match.group(4)), int(date_match.group(5)), int(date_match.group(6))
                        specific_date = date(y, m, d)
                    logger.info(f"Извлечена конкретная дата из запроса: {specific_date}")
                except ValueError as e:
                    logger.error(f"Ошибка при создании объекта даты: {e}")
            
            # Проверяем формат "DD месяц YYYY" (например, "2 сентября 1985")
            if not specific_date:
                date_text_match = re.search(r"(\d{1,2})\s+([а-яА-Яa-zA-Z]+)(?:\s+(\d{4}))?", query_lower)
                if date_text_match:
                    try:
                        day = int(date_text_match.group(1))
                        month_name = date_text_match.group(2).lower()
                        year = int(date_text_match.group(3)) if date_text_match.group(3) else datetime.now().year
                        
                        # Определяем номер месяца по его названию
                        month_number = None
                        for month_key, month_num in MONTH_NAME_TO_NUMBER.items():
                            if month_key in month_name:
                                month_number = month_num
                                break
                        
                        if month_number:
                            specific_date = date(year, month_number, day)
                            logger.info(f"Извлечена конкретная дата из текстового запроса: {specific_date}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка при создании объекта даты из текста: {e}")
            
            # Если конкретная дата не найдена, определяем смещение относительно текущей даты
            if not specific_date:
                offset = 0
                if "завтра" in query_lower or "следующ" in query_lower:
                    offset = 1
                elif "вчера" in query_lower or "предыдущ" in query_lower:
                    offset = -1
                elif "послезавтра" in query_lower:
                    offset = 2
                elif "позавчера" in query_lower:
                    offset = -2
                
                # Получаем дату с учетом смещения
                target_date = datetime.now().date() + timedelta(days=offset)
            else:
                # Используем конкретную дату из запроса
                target_date = specific_date
            
            # Получаем еврейскую дату
            hebrew_data = self.hebcal_api.convert_date_to_hebrew(target_date)
            
            if "error" in hebrew_data:
                return f"<b>Ошибка при получении еврейской даты:</b>\n{hebrew_data.get('error', 'Неизвестная ошибка')}"
            
            # Получаем день недели
            weekday_ru = WEEKDAY_RU.get(target_date.strftime("%A"), target_date.strftime("%A"))
            
            # Получаем информацию о праздниках на эту дату
            holidays = self.hebcal_api.get_holidays(date=target_date.strftime("%Y-%m-%d"))
            holiday_lines = []
            for h in holidays.get("items", []) or []:
                title = h.get("title", "")
                desc = h.get("description", "")
                line = f"• {title}"
                if desc:
                    line += f": {desc}"
                holiday_lines.append(line)
            
            # Получаем информацию о недельной главе Торы
            parashat = self.hebcal_api.get_parashat_hashavua()
            parashat_info = ""
            if "error" not in parashat:
                parashat_title = parashat.get("title", "")
                parashat_date = parashat.get("date", "")
                
                if parashat_title and parashat_date:
                    try:
                        parashat_date_obj = datetime.strptime(parashat_date, "%Y-%m-%d").date()
                        days_until = (parashat_date_obj - datetime.now().date()).days
                        
                        if days_until >= 0:
                            parashat_info = f"\n\n<b>Недельная глава Торы:</b>\n• {parashat_title} (будет читаться через {days_until} дней)"
                        else:
                            parashat_info = f"\n\n<b>Недельная глава Торы:</b>\n• {parashat_title} (читалась {abs(days_until)} дней назад)"
                    except ValueError:
                        parashat_info = f"\n\n<b>Недельная глава Торы:</b>\n• {parashat_title}"
            
            # Формируем контекст с календарной информацией
            if specific_date:
                # Для конкретной даты из запроса
                date_description = f"Дата {target_date.strftime('%d.%m.%Y')}"
            else:
                # Для относительной даты
                date_description = "Сегодня"
                if offset == 1:
                    date_description = "Завтра"
                elif offset == -1:
                    date_description = "Вчера"
                elif offset == 2:
                    date_description = "Послезавтра"
                elif offset == -2:
                    date_description = "Позавчера"
            
            calendar_context = (
                f"<b>Календарная информация:</b>\n\n"
                f"<b>{date_description}</b> ({weekday_ru})\n"
                f"Еврейская дата: <b>{hebrew_data.get('hebrew', '')}</b>\n\n"
                f"<b>Подробная информация:</b>\n"
                f"• Григорианский год: {target_date.year}\n"
                f"• Григорианский месяц: {target_date.month}\n"
                f"• Григорианский день: {target_date.day}\n"
                f"• День недели: {weekday_ru}\n"
                f"• Еврейский год: {hebrew_data.get('hy', '')}\n"
                f"• Еврейский месяц: {hebrew_data.get('hm', '')}\n"
                f"• Еврейский день: {hebrew_data.get('hd', '')}\n"
            )
            
            if holiday_lines:
                calendar_context += f"\n<b>Ближайшие праздники и события на эту дату:</b>\n" + "\n".join(holiday_lines)
            else:
                calendar_context += "\n<b>Праздники и события:</b> На эту дату не приходится особых праздников или событий."
            
            calendar_context += parashat_info
            
            return calendar_context
        except Exception as e:
            logger.error(f"Ошибка при получении календарного контекста: {e}", exc_info=True)
            return f"Произошла ошибка при получении календарной информации: {str(e)}"
    
    def _process_query(self, query: str, custom_context: str = None) -> str:
        """
        Обрабатывает запрос пользователя с помощью модели OpenRouter.
        
        Args:
            query (str): Запрос пользователя
            custom_context (str, optional): Пользовательский контекст для модели
            
        Returns:
            str: Ответ на запрос
        """
        try:
            # Используем пользовательский контекст, если он предоставлен
            context = custom_context if custom_context else self.system_prompt
            
            # Генерируем ответ с помощью модели
            response = self.openrouter_api.generate_response(prompt=query, context=context)
            
            return response
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}", exc_info=True)
            return f"Произошла ошибка при обработке запроса: {str(e)}"
