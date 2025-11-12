import { useEffect } from 'react';

const TelegramInit = () => {
  useEffect(() => {
    // Добавляем скрипт Telegram Web App
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-web-app.js';
    script.async = true;
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  return null;
};

export default TelegramInit;
