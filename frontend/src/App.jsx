import React, { useEffect, useState } from "react";
import Search from "./components/Search";
import TelegramWrapper from "./telegram/TelegramWrapper";
import "./App.css";

function App() {
  const [showCookieBanner, setShowCookieBanner] = useState(false);

  useEffect(() => {
    // Показываем баннер cookies только если не в Telegram
    const isInTelegram = window.Telegram?.WebApp;
    if (window.location.protocol === 'https:' && !localStorage.getItem('cookiesAccepted') && !isInTelegram) {
      setShowCookieBanner(true);
    }
  }, []);

  const handleAcceptCookies = () => {
    setShowCookieBanner(false);
    localStorage.setItem('cookiesAccepted', 'true');
    document.cookie = "cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax";
  };

  return (
    <TelegramWrapper>
      <div className="App">
        {showCookieBanner && (
          <div className="fixed bottom-4 left-4 right-4 bg-white rounded-2xl shadow-lg border border-telegram-border z-50 max-w-md mx-auto">
            <div className="p-4">
              <div className="text-center">
                <p className="text-gray-800 mb-4 text-sm leading-relaxed">
                  Мы используем только технические файлы cookie для корректной работы сайта.
                  Продолжая использовать сайт, вы соглашаетесь с этим.
                </p>
                <div className="flex flex-col space-y-2">
                  <button
                    onClick={handleAcceptCookies}
                    className="bg-telegram-primary hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
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
      </div>
    </TelegramWrapper>
  );
}

export default App;
