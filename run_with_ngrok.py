from flask import Flask, render_template, request, jsonify
from chatbot import SefariaChatBot
import os
from dotenv import load_dotenv
from pyngrok import ngrok

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
chatbot = None

# Проверка наличия API ключа перед инициализацией чат-бота
if os.getenv("OPENROUTER_API_KEY"):
    try:
        chatbot = SefariaChatBot()
    except Exception as e:
        print(f"Ошибка при инициализации чат-бота: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not chatbot:
        return jsonify({
            "error": "Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле."
        }), 500
    
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "Запрос не может быть пустым"}), 400
    
    try:
        response = chatbot.process_query(query)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": f"Ошибка при обработке запроса: {str(e)}"}), 500

@app.route('/api/text/<path:ref>')
def get_text(ref):
    if not chatbot:
        return jsonify({
            "error": "Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле."
        }), 500
    
    try:
        text = chatbot.get_specific_text(ref)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": f"Ошибка при получении текста: {str(e)}"}), 500

if __name__ == '__main__':
    # Создаем директорию для шаблонов, если она не существует
    os.makedirs('templates', exist_ok=True)
    
    # Проверяем, инициализирован ли чат-бот
    if not chatbot:
        print("ВНИМАНИЕ: Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле.")
    
    # Запускаем ngrok для создания публичного URL
    port = 5000
    public_url = ngrok.connect(port).public_url
    print(f" * Ngrok туннель запущен на {public_url}")
    print(f" * Внешний URL для доступа к боту: {public_url}")
    
    # Запускаем Flask-приложение
    app.run(port=port)
