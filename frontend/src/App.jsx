import { useState, useEffect, useCallback } from "react";
import "./App.css";
import Search from "./components/Search";
import PrivacyPolicy from "./components/PrivacyPolicy";
import SessionTimeoutWarning from "./components/SessionTimeoutWarning";
import Toast from "./components/Toast";
import useSessionTimeout from "./hooks/useSessionTimeout";
import { TelegramProvider } from "./telegram/TelegramContext";
import TelegramWrapper from "./telegram/TelegramWrapper";
import { api } from "./api/client";
import PharmacistDashboard from "./pharmacist/PharmacistDashboard";

function App() {
  const [page, setPage] = useState(window.location.pathname);
  const [toast, setToast] = useState(null); // { message, type }
  const [showCookieBanner, setShowCookieBanner] = useState(false);

  // Проверяем, это pharmacist dashboard или обычный поиск
  // Определяем по поддомену ИЛИ по пути ИЛИ по наличию токена в URL (для WebApp)
  const hostname = window.location.hostname;
  const isPharmacistSubdomain = hostname.startsWith('pharmacist.') || hostname === 'pharmacist.spravka.novamedika.com';
  const isPharmacistPath = window.location.pathname.startsWith('/pharmacist');
  
  // Проверяем наличие JWT токена в URL (WebApp authentication)
  const urlParams = new URLSearchParams(window.location.search);
  const hasAuthToken = urlParams.has('token');
  
  // Упрощенная проверка: если мы внутри Telegram WebApp, считаем что это может быть фармацевт
  // Финальная проверка регистрации произойдет на бэкенде при логине
  const isInTelegram = !!window.Telegram?.WebApp;
  
  const isPharmacistMode = isPharmacistSubdomain || isPharmacistPath || (hasAuthToken && isInTelegram);

  // Сохраняем режим в localStorage при первом определении
  useEffect(() => {
    if (isPharmacistMode && !savedMode) {
      localStorage.setItem('app_mode', 'pharmacist');
    } else if (!isPharmacistMode && savedMode === 'pharmacist') {
      // Если пользователь перешел на основной сайт, очищаем режим
      localStorage.removeItem('app_mode');
    }
  }, [isPharmacistMode, savedMode]);

  // Инициализация хука таймаута (30 минут)
  const { showWarning, secondsLeft, extendSession } = useSessionTimeout(30);

  // Отслеживаем изменение pathname (кнопки назад/вперёд в браузере)
  useEffect(() => {
    const onPopState = () => setPage(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Глобальный обработчик API ошибок
  const handleError = useCallback((error) => {
    const message = error.userMessage || error.message;
    setToast({ message, type: 'error' });
  }, []);

  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (r) => r,
      (error) => {
        if (error.isApiError || error.userMessage) {
          handleError(error);
        }
        return Promise.reject(error);
      },
    );
    return () => api.interceptors.response.eject(interceptor);
  }, [handleError]);

  useEffect(() => {
    const isInTelegram = window.Telegram?.WebApp;
    if (
      window.location.protocol === "https:" &&
      !localStorage.getItem("cookiesAccepted") &&
      !isInTelegram
    ) {
      setShowCookieBanner(true);
    }
  }, []);

  const handleAcceptCookies = () => {
    setShowCookieBanner(false);
    localStorage.setItem("cookiesAccepted", "true");
    document.cookie =
      "cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax";
    
    // Показываем success toast
    setToast({ message: 'Настройки cookies сохранены', type: 'success' });
  };

  // Если режим фармацевта - показываем dashboard
  if (isPharmacistMode) {
    return <PharmacistDashboard />;
  }

  // Простой роутинг по pathname
  if (page === "/privacy-policy") {
    return <PrivacyPolicy />;
  }

  return (
    <TelegramProvider>
      <TelegramWrapper>
        <div className="App">
          {/* Компонент предупреждения о таймауте */}
          <SessionTimeoutWarning
            showWarning={showWarning}
            secondsLeft={secondsLeft}
            onExtend={extendSession}
          />

          {/* Баннер cookies */}
          {showCookieBanner && (
            <div className="fixed bottom-4 left-4 right-4 bg-white rounded-2xl shadow-lg border border-telegram-border z-50 max-w-md mx-auto">
              <div className="p-4">
                <div className="text-center">
                  <p className="text-gray-800 mb-4 text-sm leading-relaxed">
                    Мы используем только технические файлы cookie для корректной
                    работы сайта. Продолжая использовать сайт, вы соглашаетесь с
                    этим.
                  </p>
                  <div className="flex flex-col space-y-2">
                    <button
                      onClick={handleAcceptCookies}
                      className="bg-telegram-primary hover:bg-blue-600 text-gray-900 font-medium py-2 px-4 rounded-lg transition-colors text-sm"
                    >
                      Принять
                    </button>
                    <a
                      href="/privacy-policy"
                      className="text-telegram-primary hover:text-blue-600 font-medium py-2 text-sm"
                    >
                      Политика конфиденциальности
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Основной компонент поиска */}
          <Search />

          {/* Toast уведомления */}
          {toast && (
            <Toast
              message={toast.message}
              type={toast.type}
              onClose={() => setToast(null)}
              duration={toast.type === 'error' ? 5000 : 3000}
            />
          )}
        </div>
      </TelegramWrapper>
    </TelegramProvider>
  );
}

export default App;
