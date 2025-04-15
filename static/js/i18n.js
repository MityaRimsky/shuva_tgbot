// Инициализация i18next
async function initI18n() {
    // Загружаем библиотеки
    await loadScript('https://cdn.jsdelivr.net/npm/i18next@21.6.10/i18next.min.js');
    await loadScript('https://cdn.jsdelivr.net/npm/i18next-http-backend@1.3.2/i18nextHttpBackend.min.js');
    await loadScript('https://cdn.jsdelivr.net/npm/i18next-browser-languagedetector@6.1.3/i18nextBrowserLanguageDetector.min.js');
    
    // Инициализируем i18next
    await i18next
        .use(i18nextHttpBackend)
        .use(i18nextBrowserLanguageDetector)
        .init({
            fallbackLng: 'ru',
            debug: true, // Включаем отладку для выявления проблем
            backend: {
                loadPath: '/static/locales/{{lng}}/{{ns}}.json',
            },
            detection: {
                order: ['localStorage', 'navigator'],
                lookupLocalStorage: 'app_language',
                caches: ['localStorage']
            },
            ns: ['translation'],
            defaultNS: 'translation'
        });
    
    // Обновляем тексты на странице после инициализации
    updatePageTexts();
    
    // Возвращаем инициализированный i18next
    return i18next;
}

// Функция для загрузки скрипта
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Функция для перевода текста
function t(key, options) {
    return i18next.t(key, options);
}

// Функция для изменения языка
async function changeLanguage(lng) {
    console.log('Изменение языка на:', lng);
    try {
        await i18next.changeLanguage(lng);
        console.log('Язык успешно изменен на:', i18next.language);
        // Обновляем тексты на странице после изменения языка
        updatePageTexts();
        return true;
    } catch (error) {
        console.error('Ошибка при изменении языка:', error);
        return false;
    }
}

// Функция для обновления всех текстов на странице
function updatePageTexts() {
    console.log('Обновление текстов на странице, текущий язык:', i18next.language);
    
    try {
        // Обновляем все элементы с атрибутом data-i18n
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            
            // Если ключ содержит [атрибут], обновляем атрибут
            if (key.includes('[')) {
                const parts = key.split('[');
                const textKey = parts[0];
                const attrKey = parts[1].replace(']', '');
                
                // Обновляем атрибут
                element.setAttribute(attrKey, t(textKey));
            } else {
                // Обновляем текстовое содержимое
                const translation = t(key);
                console.log(`Перевод для ключа ${key}:`, translation);
                element.textContent = translation;
            }
        });
        
        // Обновляем все элементы с атрибутом data-i18n-placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = t(key);
        });
        
        console.log('Обновление текстов завершено');
    } catch (error) {
        console.error('Ошибка при обновлении текстов:', error);
    }
}

// Экспортируем функции
window.i18nModule = {
    initI18n,
    t,
    changeLanguage,
    updatePageTexts
};
