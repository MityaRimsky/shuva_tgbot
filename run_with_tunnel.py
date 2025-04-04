from flask import Flask, render_template, request, jsonify
from chatbot import SefariaChatBot
import os
import subprocess
import threading
import time
from dotenv import load_dotenv

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

def start_tunnel(port):
    """Запускает localtunnel для создания публичного URL"""
    try:
        # Запускаем localtunnel с помощью Python subprocess
        process = subprocess.Popen(
            ["npx", "localtunnel", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Ждем, пока localtunnel не выведет URL
        for line in process.stdout:
            if "your url is:" in line.lower():
                url = line.strip().split("your url is: ")[1]
                print(f"\n=== ПУБЛИЧНЫЙ URL ДЛЯ ДОСТУПА К БОТУ ===")
                print(f"URL: {url}")
                print(f"Этот URL можно открыть на любом устройстве с доступом в интернет")
                print(f"===========================================\n")
                break
        
        # Держим процесс запущенным
        process.wait()
    except Exception as e:
        print(f"Ошибка при запуске туннеля: {str(e)}")

if __name__ == '__main__':
    # Создаем директорию для шаблонов, если она не существует
    os.makedirs('templates', exist_ok=True)
    
    # Проверяем, инициализирован ли чат-бот
    if not chatbot:
        print("ВНИМАНИЕ: Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле.")
    
    # Запускаем localtunnel в отдельном потоке
    port = 5000
    tunnel_thread = threading.Thread(target=start_tunnel, args=(port,))
    tunnel_thread.daemon = True
    tunnel_thread.start()
    
    # Даем время на запуск туннеля
    time.sleep(2)
    
    # Запускаем Flask-приложение
    app.run(host='0.0.0.0', port=port)
