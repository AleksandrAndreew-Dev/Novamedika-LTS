import React from 'react';
import { Link } from 'react-router-dom';
import { useTelegramWebApp } from '../telegram/TelegramContext';

export default function Footer() {
  const { isTelegram } = useTelegramWebApp();

  return (
    <div className="bg-white border-t border-telegram-border mt-8">
      <div className="max-w-4xl mx-auto py-6 px-4">
        <div className="space-y-4">
          <div className="flex flex-wrap justify-center gap-4 text-sm">
            <Link
              to="/search"
              className="text-telegram-primary hover:text-blue-600 transition-colors"
            >
              Поиск
            </Link>
            <a
              href="/terms"
              className="text-telegram-primary hover:text-blue-600 transition-colors"
            >
              Условия использования
            </a>
            <Link
              to="/privacy-policy"
              className="text-telegram-primary hover:text-blue-600 transition-colors"
            >
              Конфиденциальность
            </Link>
            {!isTelegram && (
              <>
                <a
                  href="/cookie-policy"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Cookie
                </a>
                <a
                  href="/pharmacies-nearby"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Аптеки рядом
                </a>
              </>
            )}
            <a
              href="/contacts"
              className="text-telegram-primary hover:text-blue-600 transition-colors"
            >
              Контакты
            </a>
            <a
              href="/help"
              className="text-telegram-primary hover:text-blue-600 transition-colors"
            >
              Помощь
            </a>
          </div>
          <div className="text-center text-gray-700 text-sm">
            &#169;2025 Novamedika.com
          </div>
        </div>
      </div>
    </div>
  );
}