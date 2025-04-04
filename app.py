from flask import Flask, render_template, request, jsonify
import os
import sys
import traceback
from dotenv import load_dotenv

print("Запуск приложения...")

# Добавляем текущую директорию в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Текущая директория: {current_dir}")
sys.path.append(current_dir)

try:
    print("Импорт SefariaChatBot...")
    from chatbot import SefariaChatBot
    print("Импорт SefariaChatBot успешен")
except Exception as e:
    print(f"Ошибка при импорте SefariaChatBot: {str(e)}")
    print(traceback.format_exc())

# Загрузка переменных окружения
print("Загрузка переменных окружения...")
load_dotenv()

print("Создание Flask-приложения...")
app = Flask(__name__)
chatbot = None

# Проверка наличия API ключа перед инициализацией чат-бота
api_key = os.getenv("OPENROUTER_API_KEY")
print(f"API ключ найден: {bool(api_key)}")

if api_key:
    try:
        print("Инициализация чат-бота...")
        chatbot = SefariaChatBot()
        print("Чат-бот успешно инициализирован")
    except Exception as e:
        print(f"Ошибка при инициализации чат-бота: {str(e)}")
        print(traceback.format_exc())

@app.route('/')
def index():
    print("Запрос к корневому маршруту '/'")
    try:
        # Проверяем наличие файла шаблона
        template_path = os.path.join('templates', 'index.html')
        if not os.path.exists(template_path):
            print(f"Файл шаблона не найден: {template_path}")
            return f"Ошибка: файл шаблона не найден: {template_path}", 404
        
        print("Рендеринг шаблона index.html")
        return render_template('index.html')
    except Exception as e:
        print(f"Ошибка при рендеринге шаблона: {str(e)}")
        print(traceback.format_exc())
        return f"Ошибка при загрузке страницы: {str(e)}", 500

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
    print("Проверка директории шаблонов...")
    os.makedirs('templates', exist_ok=True)
    
    # Проверяем наличие файла шаблона
    template_path = os.path.join('templates', 'index.html')
    print(f"Проверка наличия файла шаблона: {template_path}")
    if os.path.exists(template_path):
        print(f"Файл шаблона найден: {template_path}")
    else:
        print(f"Файл шаблона не найден: {template_path}")
    
    # Проверяем, инициализирован ли чат-бот
    if not chatbot:
        print("ВНИМАНИЕ: Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле.")
    
    print("Запуск Flask-приложения на http://127.0.0.1:5000")
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Ошибка при запуске Flask-приложения: {str(e)}")
        print(traceback.format_exc())
