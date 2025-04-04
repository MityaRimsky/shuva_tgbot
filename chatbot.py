from openrouter_api import OpenRouterAPI
from sefaria_api import SefariaAPI

class SefariaChatBot:
    def __init__(self):
        self.openrouter_api = OpenRouterAPI()
        self.sefaria_api = SefariaAPI()
        
        # Системный промпт для модели
        self.system_prompt = """
        Ты - чат-бот, специализирующийся на еврейских текстах и традициях. 
        Ты используешь базу знаний Sefaria для предоставления точной информации.
        Когда тебя спрашивают о еврейских текстах, традициях или концепциях, 
        ты должен использовать предоставленный контекст из Sefaria для формирования ответа.
        Если контекст не предоставлен или недостаточен, ты должен честно признать ограничения своих знаний.
        """
    
    def process_query(self, query):
        """
        Обрабатывает запрос пользователя, ищет релевантную информацию в Sefaria
        и генерирует ответ с использованием OpenRouter.
        
        Args:
            query (str): Запрос пользователя
            
        Returns:
            str: Ответ на запрос
        """
        # Шаг 1: Поиск релевантных текстов в Sefaria
        search_results = self.sefaria_api.search_texts(query)
        
        # Если результаты не найдены, просто передаем запрос в OpenRouter
        if not search_results:
            return self.openrouter_api.generate_response(
                prompt=query,
                context=self.system_prompt
            )
        
        # Шаг 2: Получаем полные тексты для первых 3 результатов
        context_texts = []
        for hit in search_results[:3]:
            source = hit.get("_source", {})
            ref = source.get("ref")
            
            if ref:
                text_data = self.sefaria_api.get_text(ref)
                if text_data and "text" in text_data:
                    text = text_data["text"]
                    if isinstance(text, list):
                        text = "\n".join([str(t) for t in text])
                    
                    context_texts.append(f"Источник: {ref}\nТекст: {text}")
        
        # Шаг 3: Формируем контекст для OpenRouter
        context = self.system_prompt
        if context_texts:
            context += "\n\nРелевантные тексты из Sefaria:\n\n" + "\n\n".join(context_texts)
        
        # Шаг 4: Генерируем ответ с использованием OpenRouter
        response = self.openrouter_api.generate_response(
            prompt=query,
            context=context
        )
        
        return response
    
    def get_specific_text(self, ref):
        """
        Получает конкретный текст по ссылке и форматирует его.
        
        Args:
            ref (str): Ссылка на текст в формате Sefaria
            
        Returns:
            str: Форматированный текст
        """
        text_data = self.sefaria_api.get_text(ref)
        return self.sefaria_api.format_text(text_data)
