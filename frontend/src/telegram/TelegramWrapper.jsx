import React from 'react';
import { useTelegramWebApp } from './TelegramContext';

export default function TelegramWrapper({ children }) {
  const { isReady } = useTelegramWebApp();

  // Не блокируем первоначальный рендер интерфейса ожиданием Telegram SDK.
  if (!isReady) {
    return <>{children}</>;
  }

  return children;
}
