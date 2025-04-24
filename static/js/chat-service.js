// Модуль для работы с чатами через Supabase
const chatService = (function() {
    // Инициализация клиента Supabase
    async function init() {
        try {
            // Ждем инициализации auth.js, если она еще не произошла
            if (!window.supabaseClient) {
                // Проверяем каждые 100 мс, готов ли supabaseClient
                for (let i = 0; i < 50; i++) { // максимум 5 секунд ожидания
                    await new Promise(resolve => setTimeout(resolve, 100));
                    if (window.supabaseClient) break;
                }
                
                // Если supabaseClient все еще не доступен, инициализируем его сами
                if (!window.supabaseClient) {
                    const response = await fetch('/api/auth/config');
                    const config = await response.json();
                    
                    window.supabaseClient = window.supabase.createClient(
                        config.supabaseUrl, 
                        config.supabaseKey
                    );
                }
            }
            
            return true;
        } catch (error) {
            console.error('Ошибка при инициализации Supabase:', error);
            return false;
        }
    }
    
    // Получение всех сессий чата пользователя
    async function getChatSessions() {
        try {
            // Получаем текущего пользователя
            const { data: authData, error: authError } = await window.supabaseClient.auth.getUser();
            
            if (authError) throw authError;
            if (!authData || !authData.user) throw new Error('Пользователь не авторизован');
            
            const userId = authData.user.id;
            
            // Получаем сессии текущего пользователя
            const { data, error } = await window.supabaseClient
                .from('chat_sessions')
                .select('*')
                .eq('user_id', userId)
                .order('last_active_at', { ascending: false });
                
            if (error) throw error;
            return data || [];
        } catch (error) {
            console.error('Ошибка при получении сессий чата:', error);
            return [];
        }
    }
    
    // Создание новой сессии чата
    async function createChatSession(title = null) {
        try {
            // Получаем текущего пользователя
            const { data: authData, error: authError } = await window.supabaseClient.auth.getUser();
            
            if (authError) throw authError;
            if (!authData || !authData.user) throw new Error('Пользователь не авторизован');
            
            const userId = authData.user.id;
            
            // Если заголовок не передан, используем перевод "Новый чат"
            if (title === null) {
                title = window.i18nModule.t('chat.new');
            }
            
            // Создаем сессию с указанием user_id
            const { data, error } = await window.supabaseClient
                .from('chat_sessions')
                .insert([{ 
                    title,
                    user_id: userId
                }])
                .select()
                .single();
                
            if (error) throw error;
            return data;
        } catch (error) {
            console.error('Ошибка при создании сессии чата:', error);
            return null;
        }
    }
    
    // Обновление сессии чата
    async function updateChatSession(sessionId, updates) {
        try {
            const { data, error } = await window.supabaseClient
                .from('chat_sessions')
                .update(updates)
                .eq('id', sessionId)
                .select()
                .single();
                
            if (error) throw error;
            return data;
        } catch (error) {
            console.error('Ошибка при обновлении сессии чата:', error);
            return null;
        }
    }
    
    // Получение сообщений для конкретной сессии
    async function getChatMessages(sessionId) {
        try {
            const { data, error } = await window.supabaseClient
                .from('chat_messages')
                .select('*')
                .eq('session_id', sessionId)
                .order('timestamp', { ascending: true });
                
            if (error) throw error;
            return data || [];
        } catch (error) {
            console.error('Ошибка при получении сообщений чата:', error);
            return [];
        }
    }
    
    // Добавление нового сообщения
    async function addChatMessage(sessionId, message, isUser) {
        try {
            const { data, error } = await window.supabaseClient
                .from('chat_messages')
                .insert([{
                    session_id: sessionId,
                    sender: isUser ? 'user' : 'bot',
                    content: message
                }])
                .select()
                .single();
                
            if (error) throw error;
            
            // Обновляем время последней активности сессии
            await updateChatSession(sessionId, { 
                last_active_at: new Date().toISOString(),
                title: isUser ? message.substring(0, 50) : undefined
            });
            
            return data;
        } catch (error) {
            console.error('Ошибка при добавлении сообщения:', error);
            return null;
        }
    }
    
    // Удаление сессии чата
    async function deleteChatSession(sessionId) {
        try {
            const { error } = await window.supabaseClient
                .from('chat_sessions')
                .delete()
                .eq('id', sessionId);
                
            if (error) throw error;
            return true;
        } catch (error) {
            console.error('Ошибка при удалении сессии чата:', error);
            return false;
        }
    }
    
    return {
        init,
        getChatSessions,
        createChatSession,
        updateChatSession,
        getChatMessages,
        addChatMessage,
        deleteChatSession
    };
})();

// Экспортируем модуль
window.chatService = chatService;
