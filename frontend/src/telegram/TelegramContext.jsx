/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from 'react';
import { logger } from '../utils/logger';

const TelegramContext = createContext(null);

export function TelegramProvider({ children }) {
  const [tg, setTg] = useState(null);
  const [isTelegram, setIsTelegram] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Debounced viewport handler with limited logging
    let viewportLogCount = 0;
    const MAX_VIEWPORT_LOGS = 10;
    let viewportTimer = null;
    let didSetReady = false;

    const markReady = () => {
      if (!didSetReady) {
        didSetReady = true;
        setIsReady(true);
      }
    };

    const handleViewportChange = () => {
      if (viewportTimer) return; // debounce: skip if timer already active
      viewportTimer = setTimeout(() => {
        viewportTimer = null;
      }, 300);

      if (viewportLogCount < MAX_VIEWPORT_LOGS) {
        viewportLogCount++;
        logger.debug(
          '[Telegram] Viewport changed (debounced)',
        );
      }
    };

    const initTelegram = () => {
      if (window.Telegram?.WebApp) {
        const telegram = window.Telegram.WebApp;

        telegram.ready();
        telegram.expand();

        telegram.setHeaderColor('#2b6cb0');
        telegram.setBackgroundColor('#f7fafc');
        telegram.enableClosingConfirmation();

        // Subscribe to viewport changes with debounce
        telegram.onEvent(
          'viewportChanged',
          handleViewportChange,
        );

        setTg(telegram);
        setIsTelegram(true);
        markReady();

        logger.log('Telegram Web App initialized:', {
          platform: telegram.platform,
          version: telegram.version,
          user: telegram.initDataUnsafe?.user,
        });
      } else {
        markReady();
        logger.log('Not in Telegram environment');
      }
    };

    const checkTelegram = () => {
      if (window.Telegram?.WebApp) {
        initTelegram();
      } else {
        markReady();
        logger.log(
          'Telegram Web App not detected; continuing without blocking UI',
        );
      }
    };

    checkTelegram();

    return () => {
      // Cleanup: unsubscribe from viewport events
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.offEvent(
          'viewportChanged',
          handleViewportChange,
        );
      }
      if (viewportTimer) {
        clearTimeout(viewportTimer);
      }
    };
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
    throw new Error(
      'useTelegramContext must be used within TelegramProvider',
    );
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
