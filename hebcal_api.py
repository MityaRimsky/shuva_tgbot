from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HebcalAPI:
    """Helper for Hebcal endpoints (converter, holidays, shabbat, …)."""

    base_url = "https://www.hebcal.com/hebcal"
    converter_url = "https://www.hebcal.com/converter"
    shabbat_url = "https://www.hebcal.com/shabbat"
    yahrzeit_url = "https://www.hebcal.com/yahrzeit"

    def __init__(self, lang: str = "ru") -> None:
        # Common parameters added to every request
        self.default_params: Dict[str, Any] = {
            "cfg": "json",  # always ask for JSON
            "lg": lang,      # language of transliteration / labels
        }

    # ---------------------------------------------------------------------
    # Conversion helpers
    # ---------------------------------------------------------------------
    def convert_date_to_hebrew(self, gregorian_date: "_dt.date | str") -> Dict[str, Any]:
        """Gregorian → Hebrew. Accepts datetime.date or 'YYYY-MM-DD'."""
        if isinstance(gregorian_date, _dt.date):
            gregorian_date = gregorian_date.strftime("%Y-%m-%d")
        try:
            gy, gm, gd = gregorian_date.split("-")
        except ValueError:
            return {"error": "Неверный формат даты. Используйте YYYY-MM-DD."}

        params = {
            **self.default_params,
            "gy": gy,
            "gm": gm,
            "gd": gd,
            "g2h": 1,  # <-- crucial flag!
        }
        result = self._get_json(self.converter_url, params)
        
        return result

    # Словарь для нормализации названий еврейских месяцев
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
    }

    def normalize_hebrew_month(self, month: str) -> str:
        """Нормализует название еврейского месяца к стандартному формату."""
        if not month:
            return ""
        
        # Приводим к нижнему регистру для поиска в словаре
        month_lower = month.lower()
        
        # Проверяем, есть ли месяц в словаре нормализации
        normalized = self.HEBREW_MONTH_NORMALIZE.get(month_lower)
        if normalized:
            return normalized
        
        # Если месяц не найден в словаре, возвращаем исходное значение
        # с первой буквой в верхнем регистре
        return month.capitalize()

    def convert_date_to_gregorian(self, hebrew_date: "dict | str") -> Dict[str, Any]:
        """Hebrew → Gregorian. Accepts dict {'hy','hm','hd'} or '5786 Nisan 15'."""
        params = {**self.default_params, "h2g": 1}

        if isinstance(hebrew_date, dict):
            # Нормализуем название месяца
            month = hebrew_date.get("hm", "")
            normalized_month = self.normalize_hebrew_month(month)
            
            params.update({
                "hy": hebrew_date.get("hy"),
                "hm": normalized_month,
                "hd": hebrew_date.get("hd"),
            })
            
            # Добавляем подробное логирование
            if month != normalized_month:
                logger.info(f"Нормализация месяца: {month} -> {normalized_month}")
                
        elif isinstance(hebrew_date, str):
            parts = hebrew_date.split()
            if len(parts) >= 3:
                # Нормализуем название месяца
                month = parts[1]
                normalized_month = self.normalize_hebrew_month(month)
                
                params.update({
                    "hy": parts[0], 
                    "hm": normalized_month, 
                    "hd": parts[2]
                })
                
                # Добавляем подробное логирование
                if month != normalized_month:
                    logger.info(f"Нормализация месяца: {month} -> {normalized_month}")
            else:
                return {"error": "Неверный формат еврейской даты. Используйте 'ГОД МЕСЯЦ ДЕНЬ'."}
        else:
            return {"error": "Неверный тип данных для еврейской даты."}

        # Добавляем валидацию параметров перед отправкой запроса
        if not params.get("hy") or not params.get("hm") or not params.get("hd"):
            missing_params = []
            if not params.get("hy"):
                missing_params.append("год")
            if not params.get("hm"):
                missing_params.append("месяц")
            if not params.get("hd"):
                missing_params.append("день")
                
            return {"error": f"Отсутствуют обязательные параметры: {', '.join(missing_params)}"}

        # Получаем результат от API
        result = self._get_json(self.converter_url, params)
        
        return result

    # ---------------------------------------------------------------------
    # Holidays
    # ---------------------------------------------------------------------
    def get_holidays(self, date: "_dt.date | str | None" = None, *, start_date: "_dt.date | str | None" = None,
                     end_date: "_dt.date | str | None" = None, include_minor: bool = True) -> Dict[str, Any]:
        """Return holidays on a single date or in a range."""
        params = {
            **self.default_params,
            "v": 1,
            "maj": "on",
        }
        if include_minor:
            params["min"] = "on"

        if date:
            if isinstance(date, _dt.date):
                date = date.strftime("%Y-%m-%d")
            y, m, d = date.split("-")
            params.update({"year": y, "month": m, "day": d})
        elif start_date and end_date:
            if isinstance(start_date, _dt.date):
                start_date = start_date.strftime("%Y-%m-%d")
            if isinstance(end_date, _dt.date):
                end_date = end_date.strftime("%Y-%m-%d")
            params.update({"start": start_date, "end": end_date})
        else:
            params["year"] = _dt.date.today().year

        return self._get_json(self.base_url, params)

    def get_holidays_for_year(self, year: int | None = None, include_minor: bool = True) -> Dict[str, Any]:
        year = year or _dt.date.today().year
        params = {
            **self.default_params,
            "v": 1,
            "year": year,
            "maj": "on",
        }
        if include_minor:
            params["min"] = "on"
        return self._get_json(self.base_url, params)

    # ---------------------------------------------------------------------
    # Shabbat & Yahrzeit (unchanged minor tweaks)
    # ---------------------------------------------------------------------
    def get_shabbat_times(self, *, date: "_dt.date | str | None" = None, location: str | None = None,
                          latitude: float | None = None, longitude: float | None = None,
                          tzid: str | None = None) -> Dict[str, Any]:
        params: Dict[str, Any] = self.default_params.copy()
        if date:
            if isinstance(date, _dt.date):
                date = date.strftime("%Y-%m-%d")
            params["date"] = date
        if location:
            params["geonameid"] = location
        elif latitude is not None and longitude is not None:
            params.update({"latitude": latitude, "longitude": longitude})
        if tzid:
            params["tzid"] = tzid
        return self._get_json(self.shabbat_url, params)

    def get_yahrzeit_dates(self, date: "_dt.date | str", *, hebrew_date: bool = False, years: int = 5) -> Dict[str, Any]:
        if isinstance(date, _dt.date):
            date = date.strftime("%Y-%m-%d")
        params: Dict[str, Any] = {**self.default_params, "years": years}
        if not hebrew_date:
            y, m, d = date.split("-")
            params.update({"gy": y, "gm": m, "gd": d})
        else:
            parts = date.split()
            if len(parts) >= 3:
                params.update({"hy": parts[0], "hm": parts[1], "hd": parts[2], "h2g": 1})
            else:
                return {"error": "Неверный формат еврейской даты. Используйте 'ГОД МЕСЯЦ ДЕНЬ'."}
        return self._get_json(self.yahrzeit_url, params)

    # ---------------------------------------------------------------------
    # Utility wrappers
    # ---------------------------------------------------------------------
    @staticmethod
    def days_until_event(event_date: "_dt.date | str") -> int | Dict[str, str]:
        if isinstance(event_date, str):
            try:
                event_date = _dt.datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Неверный формат даты. Используйте YYYY-MM-DD."}
        today = _dt.date.today()
        return (event_date - today).days

    @staticmethod
    def days_since_event(event_date: "_dt.date | str") -> int | Dict[str, str]:
        if isinstance(event_date, str):
            try:
                event_date = _dt.datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Неверный формат даты. Используйте YYYY-MM-DD."}
        today = _dt.date.today()
        return (today - event_date).days
    
    def format_hebrew_date(self, date_data: Dict[str, Any]) -> str:
        """Форматирует еврейскую дату в удобочитаемый формат."""
        if not date_data or "hebrew" not in date_data:
            return "Дата не найдена"
        
        return date_data.get("hebrew", "")
    
    def format_holidays(self, holidays_data: Dict[str, Any]) -> str:
        """Форматирует данные о праздниках в удобочитаемый формат."""
        if not holidays_data or "items" not in holidays_data:
            return "Праздники не найдены"
        
        items = holidays_data.get("items", [])
        if not items:
            return "Праздники не найдены"
        
        formatted_holidays = []
        for item in items:
            title = item.get("title", "")
            date_str = item.get("date", "")
            hebrew = ""
            
            if date_str:
                hebrew_date = self.convert_date_to_hebrew(date_str)
                hebrew = hebrew_date.get("hebrew", "")
            
            line = f"• {title} — {date_str}"
            if hebrew:
                line += f" ({hebrew})"
            
            description = item.get("description", "")
            if description:
                line += f": {description}"
            
            formatted_holidays.append(line)
        
        return "\n".join(formatted_holidays)
    
    # ---------------------------------------------------------------------
    # Additional API methods for specific data
    # ---------------------------------------------------------------------
    def get_current_hebrew_date(self) -> Dict[str, Any]:
        """Получает текущую еврейскую дату."""
        today = _dt.date.today()
        return self.convert_date_to_hebrew(today)
    
    def get_parashat_hashavua(self) -> Dict[str, Any]:
        """Получает текущую недельную главу Торы (парашат ха-шавуа)."""
        # Получаем текущую дату и ближайшие 7 дней
        today = _dt.date.today()
        end_date = today + _dt.timedelta(days=7)
        
        # Параметры для запроса парашат ха-шавуа
        params = {
            **self.default_params,
            "v": 1,
            "start": today.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "category": "parashat",
        }
        
        try:
            response = self._get_json(self.base_url, params)
            items = response.get("items", [])
            
            # Ищем первый элемент с категорией parashat
            for item in items:
                if item.get("category") == "parashat":
                    return {
                        "title": item.get("title", ""),
                        "hebrew": item.get("hebrew", ""),
                        "date": item.get("date", "")
                    }
            
            # Если не нашли, возвращаем пустой результат
            return {"error": "Парашат ха-шавуа не найдена", "title": "", "hebrew": "", "date": ""}
        except Exception as e:
            logger.error("Ошибка при получении парашат ха-шавуа: %s", e)
            return {"error": str(e), "title": "", "hebrew": "", "date": ""}
    
    def get_daf_yomi(self) -> Dict[str, Any]:
        """Получает текущий лист Талмуда (даф йоми)."""
        # Получаем текущую дату
        today = _dt.date.today()
        
        # Параметры для запроса даф йоми
        params = {
            **self.default_params,
            "v": 1,
            "start": today.strftime("%Y-%m-%d"),
            "end": today.strftime("%Y-%m-%d"),
            "category": "dafyomi",
        }
        
        try:
            response = self._get_json(self.base_url, params)
            items = response.get("items", [])
            
            # Ищем элемент с категорией dafyomi
            for item in items:
                if item.get("category") == "dafyomi":
                    return {
                        "title": item.get("title", ""),
                        "hebrew": item.get("hebrew", ""),
                        "date": item.get("date", "")
                    }
            
            # Если не нашли, возвращаем пустой результат
            return {"error": "Даф йоми не найден", "title": "", "hebrew": "", "date": ""}
        except Exception as e:
            logger.error("Ошибка при получении даф йоми: %s", e)
            return {"error": str(e), "title": "", "hebrew": "", "date": ""}
    
    def get_upcoming_holidays(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получает ближайшие праздники."""
        # Получаем текущую дату и дату через 180 дней
        today = _dt.date.today()
        end_date = today + _dt.timedelta(days=180)
        
        # Параметры для запроса праздников
        params = {
            **self.default_params,
            "v": 1,
            "start": today.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "category": "holiday",
            "maj": "on",
        }
        
        try:
            response = self._get_json(self.base_url, params)
            items = response.get("items", [])
            
            # Фильтруем только праздники
            holidays = []
            for item in items:
                if item.get("category") == "holiday":
                    holidays.append({
                        "title": item.get("title", ""),
                        "hebrew": item.get("hebrew", ""),
                        "date": item.get("date", "")
                    })
                    
                    # Ограничиваем количество праздников
                    if len(holidays) >= limit:
                        break
            
            return holidays
        except Exception as e:
            logger.error("Ошибка при получении праздников: %s", e)
            return []

    # ---------------------------------------------------------------------
    # Internal HTTP helper
    # ---------------------------------------------------------------------
    def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Hebcal API error (%s): %s", url, exc)
            return {"error": str(exc), "items": []}
        except ValueError as json_err:
            logger.error("Hebcal JSON parse error (%s): %s", url, json_err)
            return {"error": "Ошибка при парсинге JSON", "items": []}
