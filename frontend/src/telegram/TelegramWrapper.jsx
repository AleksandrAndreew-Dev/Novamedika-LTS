import React from 'react';
import { useTelegramWebApp } from './TelegramWebApp';

export default function TelegramWrapper({ children }) {
  const { isReady } = useTelegramWebApp();

  // Показываем лоадер пока Telegram Web App инициализируется
  if (!isReady) {
    return (
      <div className="min-h-screen bg-telegram-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-telegram-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка приложения...</p>
        </div>
      </div>
    );
  }

  return children;
}
