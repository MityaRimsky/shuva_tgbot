import os
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

class OpenRouterAPI:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API ключ не найден. Убедитесь, что он указан в .env файле.")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_response(self, prompt, context=None, model="meta-llama/llama-4-scout:free"):
        """
        Генерирует ответ на основе промпта и контекста с использованием указанной модели.
        
        Args:
            prompt (str): Вопрос или промпт для модели
            context (str, optional): Дополнительный контекст для модели
            model (str, optional): Идентификатор модели для использования
            
        Returns:
            str: Ответ от модели
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = []
        
        # Добавляем контекст, если он предоставлен
        if context:
            messages.append({
                "role": "system",
                "content": f"Используй следующую информацию для ответа на вопрос пользователя: {context}"
            })
        
        # Добавляем промпт пользователя
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            return f"Ошибка при обращении к OpenRouter API: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Ошибка при обработке ответа от OpenRouter API: {str(e)}"
