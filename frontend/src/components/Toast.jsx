import React, { useEffect, useCallback } from 'react';

/**
 * Toast Notification Component
 * 
 * Всплывающие уведомления для обратной связи с пользователем
 * Соответствует e-commerce best practices (Amazon, Wildberries, Ozon)
 */
export default function Toast({ message, type = 'info', onClose, duration = 3000 }) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  // Иконки для разных типов уведомлений
  const icons = {
    success: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  };

  // Цвета для разных типов уведомлений
  const colors = {
    success: 'bg-green-500 text-white',
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-gray-900',
    info: 'bg-blue-500 text-white'
  };

  // Haptic feedback для Telegram Web App
  const handleHapticFeedback = useCallback(() => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      const feedbackType = {
        success: 'notificationOccurred',
        error: 'notificationOccurred',
        warning: 'notificationOccurred',
        info: 'impactOccurred'
      }[type];

      const intensity = {
        success: 'success',
        error: 'error',
        warning: 'warning',
        info: 'light'
      }[type];

      window.Telegram.WebApp.HapticFeedback[feedbackType](intensity);
    }
  }, [type]);

  // Вызываем haptic feedback при монтировании компонента
  useEffect(() => {
    handleHapticFeedback();
  }, [handleHapticFeedback]);

  return (
    <div 
      className={`fixed top-4 right-4 left-4 sm:left-auto sm:max-w-md z-50 animate-slideInDown ${colors[type]} rounded-xl shadow-lg overflow-hidden`}
      role="alert"
      aria-live="polite"
    >
      <div className="p-4 flex items-start gap-3">
        {/* Иконка */}
        <div className="flex-shrink-0 mt-0.5">
          {icons[type]}
        </div>

        {/* Сообщение */}
        <div className="flex-1">
          <p className="text-sm font-medium leading-relaxed">
            {message}
          </p>
        </div>

        {/* Кнопка закрытия */}
        <button
          onClick={onClose}
          className="flex-shrink-0 ml-2 p-1 rounded-lg hover:bg-white/20 transition-colors touch-manipulation"
          aria-label="Закрыть уведомление"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Progress bar для визуализации времени до закрытия */}
      {duration > 0 && (
        <div className="h-1 bg-white/20">
          <div 
            className="h-full bg-white/40 animate-shrinkWidth"
            style={{ animationDuration: `${duration}ms` }}
          ></div>
        </div>
      )}
    </div>
  );
}
