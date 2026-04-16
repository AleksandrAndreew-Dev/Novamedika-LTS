import { useState, useEffect, useCallback } from "react";
import "./App.css";
import Search from "./components/Search";
import PrivacyPolicy from "./components/PrivacyPolicy";
import SessionTimeoutWarning from "./components/SessionTimeoutWarning";
import useSessionTimeout from "./hooks/useSessionTimeout";
import { TelegramProvider } from "./telegram/TelegramContext";
import TelegramWrapper from "./telegram/TelegramWrapper";
import { api } from "./api/client";

function App() {
  const [page, setPage] = useState(window.location.pathname);
  const [errorToast, setErrorToast] = useState(null);
  const [showCookieBanner, setShowCookieBanner] = useState(false);

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
    setErrorToast(message);
    setTimeout(() => setErrorToast(null), 5000);
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
  };

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

          {/* Тост с ошибками */}
          {errorToast && (
            <div className="fixed top-4 left-4 right-4 max-w-md mx-auto z-50 animate-slide-down">
              <div className="bg-red-500 text-white rounded-xl shadow-lg p-4 flex items-center justify-between">
                <span className="text-sm font-medium">{errorToast}</span>
                <button
                  onClick={() => setErrorToast(null)}
                  className="ml-4 text-white hover:text-gray-200 transition-colors flex-shrink-0"
                  aria-label="Закрыть"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
        </div>
      </TelegramWrapper>
    </TelegramProvider>
  );
}

export default App;
