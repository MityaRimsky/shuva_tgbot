from openrouter_api import OpenRouterAPI
from sefaria_api import SefariaAPI

class SefariaChatBot:
    def __init__(self):
        self.openrouter_api = OpenRouterAPI()
        self.sefaria_api = SefariaAPI()
        
        # Системный промпт для модели
        self.system_prompt = """
        Ты — эксперт по еврейским текстам и традициям. Форматируй ответы следующим образом:

        1. Источники:
        - Всегда указывай точные источники цитат в скобках (пример: Берешит 1:1, Мишна Сангедрин 4:5)
        - Для мудрецов и комментаторов указывай период и регион (пример: Раши (Франция, XI век))

        2. Объяснения:
        - Для всех специальных терминов давай краткое пояснение в скобках
        - Сложные концепции объясняй простым языком, но без упрощения содержания
        - При упоминании исторических лиц добавляй краткую справку

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
        - Форматируй структуру ответа с помощью Markdown. 
        - Используй жирные заголовки (**Пояснения к терминам**, **Источники и справки**) 
        даже если не все разделы обязательны.

        Формат ответа:
        [Основной ответ]
        [Пояснения к терминам]
        [Источники и справки]

        Пример:
        Вопрос: "Что означает концепция тиккун олам?"
        Ответ: 
        "Тиккун олам (букв. 'исправление мира') — это концепция... [развёрнутое объяснение]

        Пояснения:
        - Тиккун олам: идея человеческого участия в совершенствовании мира
        - Цдука: еврейская концепция благотворительности

        Источники:
        - Упоминается в Мишне (Гитин 4:5)
        - Развита лурианской каббалой (Исаак Лурия, Цфат, XVI век)"
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
