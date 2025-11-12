import { useEffect, useState } from 'react';

export const useTelegramWebApp = () => {
  const [tg, setTg] = useState(null);
  const [isTelegram, setIsTelegram] = useState(false);

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      const telegram = window.Telegram.WebApp;
      setTg(telegram);
      setIsTelegram(true);

      // Инициализация Telegram Web App
      telegram.expand();
      telegram.enableClosingConfirmation();
      telegram.setHeaderColor('#2b6cb0');
      telegram.setBackgroundColor('#f7fafc');

      console.log('Telegram Web App initialized:', telegram.initDataUnsafe);
    }
  }, []);

  return { tg, isTelegram };
};

export const useTelegramUser = () => {
  const { tg, isTelegram } = useTelegramWebApp();

  if (!isTelegram || !tg) {
    return null;
  }

  return {
    id: tg.initDataUnsafe?.user?.id,
    firstName: tg.initDataUnsafe?.user?.first_name,
    lastName: tg.initDataUnsafe?.user?.last_name,
    username: tg.initDataUnsafe?.user?.username,
    languageCode: tg.initDataUnsafe?.user?.language_code,
    theme: tg.colorScheme,
    platform: tg.platform
  };
};
