// Переменные для Supabase
let supabaseUrl;
let supabaseKey;
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
document.addEventListener('DOMContentLoaded', async function() {
    // Инициализируем модуль i18n, если он еще не инициализирован
    if (window.i18nModule && !window.i18next) {
        await window.i18nModule.initI18n();
    }
    
    // Получаем конфигурацию Supabase с сервера
    try {
        const response = await fetch('/api/auth/config');
        const config = await response.json();
        
        supabaseUrl = config.supabaseUrl;
        supabaseKey = config.supabaseKey;
        
        // Инициализация Supabase
        supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey);
        
        // Делаем клиент доступным глобально
        window.supabaseClient = supabaseClient;
        
        // Инициализация элементов DOM
        initElements();
        
        // Проверка авторизации
        checkAuth();
        
        // Обработчики событий
        setupEventListeners();
    } catch (error) {
        console.error(window.i18nModule.t('auth.errorConfig', 'Ошибка при получении конфигурации Supabase:'), error);
    }
});

// Инициализация элементов DOM
function initElements() {
    // Модальное окно профиля
    profileModal = document.getElementById('profile-modal');
    profileEmail = document.getElementById('profile-email');
    profileAvatar = document.getElementById('profile-avatar-img');
    
    // Элементы в сайдбаре (десктоп)
    sidebarUser = document.getElementById('sidebar-user');
    sidebarEmail = document.getElementById('sidebar-email');
    
    // Элементы в сайдбаре (мобильный)
    mobileSidebarUser = document.getElementById('mobile-sidebar-user');
    mobileSidebarEmail = document.getElementById('mobile-sidebar-email');
    
    // Кнопка выхода
    logoutButton = document.getElementById('logout-button');
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Открытие модального окна профиля при клике на блок пользователя (десктоп)
    if (sidebarUser) {
        sidebarUser.addEventListener('click', openProfileModal);
    }
    
    // Открытие модального окна профиля при клике на блок пользователя (мобильный)
    if (mobileSidebarUser) {
        mobileSidebarUser.addEventListener('click', openProfileModal);
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
        console.error(window.i18nModule.t('auth.errorCheckAuth', 'Ошибка при проверке авторизации:'), error);
        updateUIForUnauthenticatedUser();
    }
}

// Обновление UI для авторизованного пользователя
function updateUIForAuthenticatedUser() {
    if (!currentUser) return;
    
    // Обновляем информацию в модальном окне профиля
    if (profileEmail) {
        profileEmail.textContent = currentUser.email || window.i18nModule.t('auth.noEmail', 'Нет email');
    }
    
    // Обновляем email в сайдбаре (десктоп)
    if (sidebarEmail) {
        sidebarEmail.textContent = currentUser.email || window.i18nModule.t('auth.noEmail', 'Нет email');
    }
    
    // Обновляем email в сайдбаре (мобильный)
    if (mobileSidebarEmail) {
        mobileSidebarEmail.textContent = currentUser.email || window.i18nModule.t('auth.noEmail', 'Нет email');
    }
    
    // Устанавливаем аватар пользователя
    const avatarUrl = currentUser.user_metadata?.avatar_url || '/static/images/icon_profile.svg';
    
    if (profileAvatar) {
        profileAvatar.src = avatarUrl;
    }
    
    if (sidebarUser && sidebarUser.querySelector('img')) {
        sidebarUser.querySelector('img').src = avatarUrl;
    }
    
    if (mobileSidebarUser && mobileSidebarUser.querySelector('img')) {
        mobileSidebarUser.querySelector('img').src = avatarUrl;
    }
}

// Обновление UI для неавторизованного пользователя
function updateUIForUnauthenticatedUser() {
    // Обновляем текст в сайдбаре (десктоп)
    if (sidebarEmail) {
        sidebarEmail.textContent = window.i18nModule.t('auth.login', 'Войти');
    }
    
    // Обновляем текст в сайдбаре (мобильный)
    if (mobileSidebarEmail) {
        mobileSidebarEmail.textContent = window.i18nModule.t('auth.login', 'Войти');
    }
    
    // Устанавливаем аватар по умолчанию
    const defaultAvatarUrl = '/static/images/icon_profile.svg';
    
    if (sidebarUser && sidebarUser.querySelector('img')) {
        sidebarUser.querySelector('img').src = defaultAvatarUrl;
    }
    
    if (mobileSidebarUser && mobileSidebarUser.querySelector('img')) {
        mobileSidebarUser.querySelector('img').src = defaultAvatarUrl;
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
        // Сначала отправляем запрос на сервер для удаления сессии
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // Затем выходим из Supabase
        const { error } = await supabaseClient.auth.signOut();
        
        if (error) {
            throw error;
        }
        
        // Сбрасываем текущего пользователя
        currentUser = null;
        
        // Перенаправляем на страницу авторизации
        window.location.href = '/auth';
        
    } catch (error) {
        console.error(window.i18nModule.t('auth.errorLogout', 'Ошибка при выходе из аккаунта:'), error);
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
