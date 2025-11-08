// App.jsx
import React, { useEffect, useState } from "react";
import Search from "./components/Search";
import "./App.css";

function App() {
  const [showCookieBanner, setShowCookieBanner] = useState(false);

  useEffect(() => {
    // Показываем баннер только на HTTPS и если нет флага в localStorage
    if (window.location.protocol === 'https:' && !localStorage.getItem('cookiesAccepted')) {
      setShowCookieBanner(true);
    }

    // Обработчик для кнопки принятия cookies
    const handleAcceptCookies = () => {
      setShowCookieBanner(false);
      localStorage.setItem('cookiesAccepted', 'true');
      document.cookie = "cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax";
    };

    const acceptButton = document.getElementById('accept-cookies');
    if (acceptButton) {
      acceptButton.addEventListener('click', handleAcceptCookies);
    }

    return () => {
      if (acceptButton) {
        acceptButton.removeEventListener('click', handleAcceptCookies);
      }
    };
  }, []);

  return (
    <div className="App">
      {/* Cookie Banner */}
      {showCookieBanner && (
        <div id="cookie-banner" className="cookie-banner">
          <div className="cookie-content">
            <p>Мы используем только технические файлы cookie для корректной работы сайта. Продолжая использовать сайт, вы соглашаетесь с этим.</p>
            <button id="accept-cookies" className="btn btn-primary">Принять</button>
            <a href="/cookie-policy" className="cookie-link">Подробнее</a>
          </div>
        </div>
      )}

      <Search />
    </div>
  );
}

export default App;
