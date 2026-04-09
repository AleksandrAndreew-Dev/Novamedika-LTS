/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from "react";
import { logger } from "../utils/logger";

const TelegramContext = createContext(null);

export function TelegramProvider({ children }) {
  const [tg, setTg] = useState(null);
  const [isTelegram, setIsTelegram] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const initTelegram = () => {
      if (window.Telegram?.WebApp) {
        const telegram = window.Telegram.WebApp;

        telegram.ready();
        telegram.expand();

        telegram.setHeaderColor("#2b6cb0");
        telegram.setBackgroundColor("#f7fafc");
        telegram.enableClosingConfirmation();

        setTg(telegram);
        setIsTelegram(true);
        setIsReady(true);

        logger.log("Telegram Web App initialized:", {
          platform: telegram.platform,
          version: telegram.version,
          user: telegram.initDataUnsafe?.user,
        });
      } else {
        setIsReady(true);
        logger.log("Not in Telegram environment");
      }
    };

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
        logger.log("Telegram Web App not detected after timeout");
      }
    };

    checkTelegram();
  }, []);

  const telegramUser = useMemo(() => {
    if (!isReady || !isTelegram || !tg) return null;
    const user = tg.initDataUnsafe?.user;
    return user
      ? {
          id: user.id,
          firstName: user.first_name,
          lastName: user.last_name,
          username: user.username,
          languageCode: user.language_code,
          theme: tg.colorScheme,
          platform: tg.platform,
        }
      : null;
  }, [isReady, isTelegram, tg]);

  const showAlert = useCallback(
    (message) => {
      if (isTelegram && tg) {
        tg.showAlert(message);
      } else {
        alert(message);
      }
    },
    [isTelegram, tg],
  );

  const showConfirm = useCallback(
    (message, callback) => {
      if (isTelegram && tg) {
        tg.showConfirm(message, callback);
      } else {
        const result = confirm(message);
        callback(result);
      }
    },
    [isTelegram, tg],
  );

  const closeApp = useCallback(() => {
    if (isTelegram && tg) {
      tg.close();
    }
  }, [isTelegram, tg]);

  const setBackgroundColor = useCallback(
    (color) => {
      if (isTelegram && tg) {
        tg.setBackgroundColor(color);
      }
    },
    [isTelegram, tg],
  );

  const setHeaderColor = useCallback(
    (color) => {
      if (isTelegram && tg) {
        tg.setHeaderColor(color);
      }
    },
    [isTelegram, tg],
  );

  const value = useMemo(
    () => ({
      tg,
      isTelegram,
      isReady,
      telegramUser,
      showAlert,
      showConfirm,
      closeApp,
      setBackgroundColor,
      setHeaderColor,
    }),
    [
      tg,
      isTelegram,
      isReady,
      telegramUser,
      showAlert,
      showConfirm,
      closeApp,
      setBackgroundColor,
      setHeaderColor,
    ],
  );

  return (
    <TelegramContext.Provider value={value}>
      {children}
    </TelegramContext.Provider>
  );
}

export function useTelegramContext() {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error("useTelegramContext must be used within TelegramProvider");
  }
  return ctx;
}

// Хуки-алиасы для обратной совместимости
export function useTelegramWebApp() {
  const { tg, isTelegram, isReady } = useTelegramContext();
  return { tg, isTelegram, isReady };
}

export function useTelegramUser() {
  const { telegramUser } = useTelegramContext();
  return telegramUser;
}

export function useTelegramAPI() {
  const {
    showAlert,
    showConfirm,
    closeApp,
    setBackgroundColor,
    setHeaderColor,
    isTelegram,
    isReady,
  } = useTelegramContext();

  return {
    showAlert,
    showConfirm,
    closeApp,
    setBackgroundColor,
    setHeaderColor,
    isTelegram,
    isReady,
  };
}
