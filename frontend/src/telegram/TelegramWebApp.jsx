import { useEffect, useState } from 'react';

export const useTelegramWebApp = () => {
  const [tg, setTg] = useState(null);
  const [isTelegram, setIsTelegram] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const initTelegram = () => {
      if (window.Telegram?.WebApp) {
        const telegram = window.Telegram.WebApp;

        // Инициализация
        telegram.ready();
        telegram.expand();

        // Настройка темы
        telegram.setHeaderColor('#2b6cb0');
        telegram.setBackgroundColor('#f7fafc');

        // Включение подтверждения закрытия
        telegram.enableClosingConfirmation();

        setTg(telegram);
        setIsTelegram(true);
        setIsReady(true);

        console.log('Telegram Web App initialized:', {
          platform: telegram.platform,
          version: telegram.version,
          user: telegram.initDataUnsafe?.user
        });
      } else {
        setIsReady(true); // Все равно помечаем как готово, даже если не в Telegram
        console.log('Not in Telegram environment');
      }
    };

    // Проверяем наличие Telegram Web App каждые 100ms до 5 секунд
    let attempts = 0;
    const maxAttempts = 50;

    const checkTelegram = () => {
      if (window.Telegram?.WebApp) {
        initTelegram();
      } else if (attempts < maxAttempts) {
        attempts++;
        setTimeout(checkTelegram, 100);
      } else {
        setIsReady(true);
        console.log('Telegram Web App not detected after timeout');
      }
    };

    checkTelegram();
  }, []);

  return { tg, isTelegram, isReady };
};

export const useTelegramUser = () => {
  const { tg, isTelegram, isReady } = useTelegramWebApp();

  if (!isReady || !isTelegram || !tg) {
    return null;
  }

  const user = tg.initDataUnsafe?.user;

  return user ? {
    id: user.id,
    firstName: user.first_name,
    lastName: user.last_name,
    username: user.username,
    languageCode: user.language_code,
    theme: tg.colorScheme,
    platform: tg.platform
  } : null;
};

// Новый хук для основных функций Telegram Web App
export const useTelegramAPI = () => {
  const { tg, isTelegram, isReady } = useTelegramWebApp();

  const showAlert = (message) => {
    if (isTelegram && tg) {
      tg.showAlert(message);
    } else {
      alert(message);
    }
  };

  const showConfirm = (message, callback) => {
    if (isTelegram && tg) {
      tg.showConfirm(message, callback);
    } else {
      const result = confirm(message);
      callback(result);
    }
  };

  const closeApp = () => {
    if (isTelegram && tg) {
      tg.close();
    }
  };

  const setBackgroundColor = (color) => {
    if (isTelegram && tg) {
      tg.setBackgroundColor(color);
    }
  };

  const setHeaderColor = (color) => {
    if (isTelegram && tg) {
      tg.setHeaderColor(color);
    }
  };

  return {
    showAlert,
    showConfirm,
    closeApp,
    setBackgroundColor,
    setHeaderColor,
    isTelegram,
    isReady
  };
};
