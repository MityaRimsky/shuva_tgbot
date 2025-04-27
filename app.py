from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import sys
import traceback
import json
import logging
from dotenv import load_dotenv
from functools import wraps
from supabase import create_client, Client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('supabase-auth')

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

# Инициализация Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = None

if supabase_url and supabase_key:
    try:
        print("Инициализация Supabase...")
        supabase = create_client(supabase_url, supabase_key)
        print("Supabase успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Supabase: {str(e)}")
        print(traceback.format_exc())

print("Создание Flask-приложения...")
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key")
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

# Декоратор для проверки аутентификации
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Проверка наличия токена в сессии
        if 'auth_token' not in session:
            return redirect(url_for('auth'))
        
        # Проверка валидности токена через Supabase
        if supabase:
            try:
                # Получаем токен из сессии
                token = session['auth_token']
                
                # Проверяем токен через Supabase
                response = supabase.auth.get_user(token)
                
                # Если токен валидный, обновляем данные пользователя в сессии
                if response and hasattr(response, 'user') and response.user:
                    session['user_email'] = response.user.email
                    return f(*args, **kwargs)
                else:
                    # Если токен невалидный, удаляем его из сессии и перенаправляем на страницу авторизации
                    logger.warning(f"Невалидный токен: {token[:10]}...")
                    session.pop('auth_token', None)
                    session.pop('user_email', None)
                    return redirect(url_for('auth'))
            except Exception as e:
                logger.error(f"Ошибка при проверке токена: {str(e)}")
                # В случае ошибки, удаляем токен из сессии и перенаправляем на страницу авторизации
                session.pop('auth_token', None)
                session.pop('user_email', None)
                return redirect(url_for('auth'))
        
        # Если Supabase не инициализирован, просто проверяем наличие токена в сессии
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@auth_required
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

@app.route('/auth')
def auth():
    # Если пользователь уже авторизован, перенаправляем на главную страницу
    if 'auth_token' in session:
        return redirect(url_for('index'))
    
    return render_template('auth.html')

@app.route('/auth/reset-password')
def reset_password():
    # Страница для сброса пароля после перехода по ссылке из email
    return render_template('auth.html')

@app.route('/privacy')
def privacy():
    # Страница политики конфиденциальности
    return render_template('privacy.html')

@app.route('/api/chat', methods=['POST'])
@auth_required
def chat():
    if not chatbot:
        return jsonify({
            "error": "Чат-бот не инициализирован. Убедитесь, что API ключ OpenRouter указан в .env файле."
        }), 500
    
    data = request.json
    query = data.get('query', '')
    session_id = data.get('session_id', '')
    
    if not query:
        return jsonify({"error": "Запрос не может быть пустым"}), 400
    
    try:
        response = chatbot.process_query(query)
        return jsonify({
            "response": response,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": f"Ошибка при обработке запроса: {str(e)}"}), 500

@app.route('/api/text/<path:ref>')
@auth_required
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

# API для работы с аутентификацией
@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json
    token = data.get('token')
    
    if not token:
        logger.warning("Попытка входа без токена")
        return jsonify({"success": False, "error": "Токен не предоставлен"}), 400
    
    # Проверка токена через Supabase
    if supabase:
        try:
            logger.info(f"Проверка токена через Supabase: {token[:10]}...")
            
            # Проверяем токен через Supabase
            response = supabase.auth.get_user(token)
            
            # Если токен валидный, сохраняем его в сессии
            if response and hasattr(response, 'user') and response.user:
                session['auth_token'] = token
                session['user_email'] = response.user.email
                logger.info(f"Успешный вход пользователя: {response.user.email}")
                return jsonify({"success": True})
            else:
                logger.warning("Невалидный токен при попытке входа")
                return jsonify({"success": False, "error": "Невалидный токен"}), 401
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {str(e)}")
            return jsonify({"success": False, "error": "Ошибка при проверке токена"}), 500
    
    # Если Supabase не инициализирован, просто сохраняем токен в сессии
    logger.warning("Supabase не инициализирован, сохраняем токен без проверки")
    session['auth_token'] = token
    session['user_email'] = data.get('email')
    
    return jsonify({"success": True})

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    try:
        # Получаем токен из сессии
        token = session.get('auth_token')
        
        # Если токен есть и Supabase инициализирован
        if token and supabase:
            try:
                # Получаем данные пользователя из токена
                user_response = supabase.auth.get_user(token)
                
                if user_response and hasattr(user_response, 'user') and user_response.user:
                    user_id = user_response.user.id
                    
                    # Обновляем статус активных сессий пользователя в таблице chat_sessions
                    try:
                        # Устанавливаем is_active = false для всех активных сессий пользователя
                        supabase.table('chat_sessions') \
                            .update({'is_active': False, 'updated_at': 'now()'}) \
                            .eq('user_id', user_id) \
                            .eq('is_active', True) \
                            .execute()
                        
                        logger.info(f"Успешно обновлены сессии пользователя {user_id}")
                    except Exception as e:
                        logger.warning(f"Ошибка при обновлении сессий пользователя: {str(e)}")
                
                # Пробуем разные варианты метода выхода из Supabase
                try:
                    # Вариант 1: без параметров
                    supabase.auth.signout()
                    logger.info("Успешный выход из Supabase (метод signout)")
                except Exception as e1:
                    try:
                        # Вариант 2: с токеном
                        supabase.auth.signout(jwt=token)
                        logger.info("Успешный выход из Supabase (метод signout с jwt)")
                    except Exception as e2:
                        try:
                            # Вариант 3: sign_out без параметров
                            supabase.auth.sign_out()
                            logger.info("Успешный выход из Supabase (метод sign_out)")
                        except Exception as e3:
                            try:
                                # Вариант 4: sign_out с токеном
                                supabase.auth.sign_out(token)
                                logger.info("Успешный выход из Supabase (метод sign_out с токеном)")
                            except Exception as e4:
                                logger.warning(f"Ошибка при выходе из Supabase: {str(e1)}, {str(e2)}, {str(e3)}, {str(e4)}")
            except Exception as e:
                logger.warning(f"Ошибка при получении данных пользователя: {str(e)}")
    except Exception as e:
        logger.warning(f"Ошибка при выходе из Supabase: {str(e)}")
    finally:
        # В любом случае удаляем данные из сессии Flask
        session.pop('auth_token', None)
        session.pop('user_email', None)
    
    return jsonify({"success": True})

@app.route('/api/auth/user')
def auth_user():
    if 'auth_token' not in session:
        return jsonify({"authenticated": False}), 401
    
    # Проверка токена через Supabase
    if supabase:
        try:
            # Получаем токен из сессии
            token = session['auth_token']
            
            # Проверяем токен через Supabase
            response = supabase.auth.get_user(token)
            
            # Если токен валидный, возвращаем данные пользователя
            if response and hasattr(response, 'user') and response.user:
                user = response.user
                return jsonify({
                    "authenticated": True,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "email_confirmed": user.email_confirmed_at is not None,
                        "last_sign_in": user.last_sign_in_at
                    }
                })
            else:
                # Если токен невалидный, удаляем его из сессии
                logger.warning(f"Невалидный токен при запросе данных пользователя: {token[:10]}...")
                session.pop('auth_token', None)
                session.pop('user_email', None)
                return jsonify({"authenticated": False, "error": "Невалидный токен"}), 401
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {str(e)}")
            # В случае ошибки, удаляем токен из сессии
            session.pop('auth_token', None)
            session.pop('user_email', None)
            return jsonify({"authenticated": False, "error": "Ошибка при проверке токена"}), 500
    
    # Если Supabase не инициализирован, просто возвращаем данные из сессии
    return jsonify({
        "authenticated": True,
        "user": {
            "email": session.get('user_email', 'user@example.com')
        }
    })

@app.route('/api/auth/config')
def auth_config():
    # Предоставляем только публичный ключ Supabase, который безопасно передавать клиенту
    return jsonify({
        "supabaseUrl": os.getenv("SUPABASE_URL"),
        "supabaseKey": os.getenv("SUPABASE_KEY")
    })

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
