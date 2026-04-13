import React, { useEffect, useState, useCallback } from "react";
import Search from "./components/Search";
import TelegramWrapper from "./telegram/TelegramWrapper";
import { TelegramProvider } from "./telegram/TelegramContext";
import { api } from "./api/client";
import "./App.css";

function App() {
  const [showCookieBanner, setShowCookieBanner] = useState(false);
  const [errorToast, setErrorToast] = useState(null);

  // Глобальный обработчик API ошибок
  const handleError = useCallback((error) => {
    const message = error.userMessage || error.message;
    setErrorToast(message);
    // Автоматически скрываем через 5 секунд
    setTimeout(() => setErrorToast(null), 5000);
  }, []);

  useEffect(() => {
    // Добавляем глобальный обработчик на все API ошибки
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
    // Показываем баннер cookies только если не в Telegram
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

  return (
    <TelegramProvider>
      <TelegramWrapper>
        <div className="App">
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
                      href="/cookie-policy"
                      className="text-telegram-primary hover:text-blue-600 font-medium py-2 text-sm"
                    >
                      Подробнее
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          <Search />

          {/* Глобальный тост ошибок */}
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
