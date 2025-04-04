import requests
from urllib.parse import quote
import logging

class SefariaAPI:
    def __init__(self):
        self.base_url = "https://www.sefaria.org/api"
    
    def search_texts(self, query, limit=10, search_type='text', field='exact', slop=0, start=0):
        """
        Поиск текстов в Sefaria по ключевому слову или фразе с расширенными параметрами.

        Args:
            query (str): Поисковый запрос.
            limit (int, optional): Максимальное количество результатов (по умолчанию 10).
            search_type (str, optional): Тип поиска: 'text' или 'sheet' (по умолчанию 'text').
            field (str, optional): Поле для поиска: 'exact' или 'naive_lemmatizer' (по умолчанию 'exact').
            slop (int, optional): Максимальное расстояние между словами (по умолчанию 0).
            start (int, optional): Номер первого возвращаемого результата (по умолчанию 0).

        Returns:
            list: Список найденных текстов.
        """
        url = f"{self.base_url}/search-wrapper"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "query": query,
            "type": search_type,
            "field": field,
            "slop": slop,
            "start": start,
            "size": limit
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("hits", {}).get("hits", [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при обращении к Sefaria API: {e}")
            return []
        
    def get_text(self, ref):
        # Конвертируем ref в tref формат
        tref = ref.replace(" ", "_").replace(":", ".")
        encoded_ref = quote(tref)  # Кодируем для URL
        
        url = f"{self.base_url}/texts/{encoded_ref}"
        print(f"Debug: Requesting URL: {url}")  # Для отладки
        
        try:
            response = requests.get(url, headers={"accept": "application/json"})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def get_links(self, ref):
        """
        Получает связанные тексты и комментарии для указанной ссылки.
        
        Args:
            ref (str): Ссылка на текст в формате Sefaria
            
        Returns:
            list: Список связанных текстов и комментариев
        """
        url = f"{self.base_url}/links/{ref}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при обращении к Sefaria API: {str(e)}")
            return []
    
    def format_search_results(self, results):
        """
        Форматирует результаты поиска в удобочитаемый текст.
        
        Args:
            results (list): Результаты поиска от метода search_texts
            
        Returns:
            str: Форматированный текст с результатами
        """
        if not results:
            return "Результаты не найдены."
        
        formatted_results = []
        for hit in results:
            source = hit.get("_source", {})
            ref = source.get("ref", "Неизвестная ссылка")
            title = source.get("title", "Без названия")
            snippet = source.get("content", "")
            
            formatted_results.append(f"📜 {ref} - {title}\n{snippet}\n")
        
        return "\n".join(formatted_results)
    
    def format_text(self, text_data):
        """
        Форматирует данные текста в удобочитаемый формат.
        
        Args:
            text_data (dict): Данные текста от метода get_text
            
        Returns:
            str: Форматированный текст
        """
        if not text_data:
            return "Текст не найден."
        
        ref = text_data.get("ref", "Неизвестная ссылка")
        he_ref = text_data.get("heRef", "")
        text = text_data.get("text", "")
        
        if isinstance(text, list):
            text = "\n".join([str(t) for t in text])
        
        return f"📜 {ref} ({he_ref})\n\n{text}"
