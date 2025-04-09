// Инициализация Supabase клиента
const supabaseUrl = 'https://aauoeuyjpfdncpfvvlbn.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdW9ldXlqcGZkbmNwZnZ2bGJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMzI0OTUsImV4cCI6MjA1OTcwODQ5NX0.1EVu5NKp-4Z_Ax6TMzDbifXZVc0XePKgHbFQzAYfCZo';
let supabaseClient;

// Состояние пользователя
let currentUser = null;

// Элементы DOM для профиля
let profileModal = null;
let profileEmail = null;
let profileAvatar = null;
let userAvatar = null;
let logoutButton = null;
let loginButton = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация Supabase
    supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey);

    // Инициализация элементов DOM
    initElements();
    
    // Проверка авторизации
    checkAuth();
    
    // Обработчики событий
    setupEventListeners();
});

// Инициализация элементов DOM
function initElements() {
    // Модальное окно профиля
    profileModal = document.getElementById('profile-modal');
    profileEmail = document.getElementById('profile-email');
    profileAvatar = document.getElementById('profile-avatar-img');
    
    // Элементы в сайдбаре
    userAvatar = document.getElementById('user-avatar');
    loginButton = document.getElementById('login-button');
    
    // Кнопка выхода
    logoutButton = document.getElementById('logout-button');
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Открытие модального окна профиля при клике на аватар
    if (userAvatar) {
        userAvatar.addEventListener('click', openProfileModal);
    }
    
    // Закрытие модального окна при клике на крестик
    const closeButtons = document.querySelectorAll('.close-modal');
    closeButtons.forEach(button => {
        button.addEventListener('click', closeProfileModal);
    });
    
    // Закрытие модального окна при клике вне его области
    window.addEventListener('click', function(event) {
        if (event.target === profileModal) {
            closeProfileModal();
        }
    });
    
    // Кнопка выхода из аккаунта
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
    
    // Кнопка входа
    if (loginButton) {
        loginButton.addEventListener('click', redirectToLogin);
    }
}

// Проверка авторизации пользователя
async function checkAuth() {
    try {
        const { data, error } = await supabaseClient.auth.getSession();
        
        if (error) {
            throw error;
        }
        
        if (data?.session) {
            // Пользователь авторизован
            currentUser = data.session.user;
            updateUIForAuthenticatedUser();
        } else {
            // Пользователь не авторизован
            updateUIForUnauthenticatedUser();
        }
    } catch (error) {
        console.error('Ошибка при проверке авторизации:', error);
        updateUIForUnauthenticatedUser();
    }
}

// Обновление UI для авторизованного пользователя
function updateUIForAuthenticatedUser() {
    if (!currentUser) return;
    
    // Показываем аватар пользователя
    if (userAvatar) {
        userAvatar.style.display = 'flex';
    }
    
    // Скрываем кнопку входа
    if (loginButton) {
        loginButton.style.display = 'none';
    }
    
    // Обновляем информацию в модальном окне профиля
    if (profileEmail) {
        profileEmail.textContent = currentUser.email || 'Нет email';
    }
    
    // Устанавливаем аватар пользователя
    const avatarUrl = currentUser.user_metadata?.avatar_url || '/static/images/default-avatar.png';
    
    if (profileAvatar) {
        profileAvatar.src = avatarUrl;
    }
    
    if (userAvatar && userAvatar.querySelector('img')) {
        userAvatar.querySelector('img').src = avatarUrl;
    }
}

// Обновление UI для неавторизованного пользователя
function updateUIForUnauthenticatedUser() {
    // Скрываем аватар пользователя
    if (userAvatar) {
        userAvatar.style.display = 'none';
    }
    
    // Показываем кнопку входа
    if (loginButton) {
        loginButton.style.display = 'flex';
    }
}

// Открытие модального окна профиля
function openProfileModal() {
    if (profileModal) {
        profileModal.style.display = 'block';
        setTimeout(() => {
            profileModal.classList.add('active');
        }, 10);
    }
}

// Закрытие модального окна профиля
function closeProfileModal() {
    if (profileModal) {
        profileModal.classList.remove('active');
        setTimeout(() => {
            profileModal.style.display = 'none';
        }, 300);
    }
}

// Выход из аккаунта
async function logout() {
    try {
        const { error } = await supabaseClient.auth.signOut();
        
        if (error) {
            throw error;
        }
        
        // Сбрасываем текущего пользователя
        currentUser = null;
        
        // Обновляем UI
        updateUIForUnauthenticatedUser();
        
        // Закрываем модальное окно профиля
        closeProfileModal();
        
    } catch (error) {
        console.error('Ошибка при выходе из аккаунта:', error);
    }
}

// Перенаправление на страницу входа
function redirectToLogin() {
    window.location.href = '/auth';
}

// Экспорт функций для использования в других скриптах
window.authModule = {
    checkAuth,
    logout,
    redirectToLogin,
    openProfileModal,
    closeProfileModal
};
