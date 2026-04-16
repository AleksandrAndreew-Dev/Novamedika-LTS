import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Хук для автоматической блокировки сеанса при бездействии
 * Требование ОАЦ №66 (приложение 3, пункт 3.7):
 * "обеспечение блокировки доступа к активам информационной системы,
 * средствам защиты информации после истечения установленного времени
 * бездействия (неактивности) пользователя"
 *
 * @param {number} timeoutMinutes - время бездействия до блокировки (по умолчанию 30 минут)
 * @param {Function} onTimeout - callback при истечении времени (по умолчанию — редирект на главную)
 * @returns {Function} resetTimer — функция сброса таймера при активности
 */
export function useSessionTimeout(timeoutMinutes = 30, onTimeout = null) {
  const [isLocked, setIsLocked] = useState(false);
  const timerRef = useRef(null);
  const warningTimerRef = useRef(null);
  const [showWarning, setShowWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  // По умолчанию — редирект на главную с сохранением состояния
  const defaultOnTimeout = useCallback(() => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    setIsLocked(true);
    window.location.href = "/";
  }, []);

  const handleTimeout = onTimeout || defaultOnTimeout;

  // Предупреждение за 2 минуты до блокировки
  const WARNING_TIME = 120; // секунд

  const resetTimer = useCallback(() => {
    // Очищаем существующие таймеры
    if (timerRef.current) clearTimeout(timerRef.current);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);

    // Сбрасываем состояние
    setIsLocked(false);
    setShowWarning(false);
    setSecondsLeft(0);

    // Таймер предупреждения
    warningTimerRef.current = setTimeout(() => {
      setShowWarning(true);
      setSecondsLeft(WARNING_TIME);

      // Обратный отсчёт
      const countdown = setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            clearInterval(countdown);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }, (timeoutMinutes * 60 - WARNING_TIME) * 1000);

    // Таймер блокировки
    timerRef.current = setTimeout(() => {
      handleTimeout();
    }, timeoutMinutes * 60 * 1000);
  }, [timeoutMinutes, handleTimeout]);

  // Запуск при монтировании
  useEffect(() => {
    resetTimer();

    // Отслеживаем активность пользователя
    const events = ["mousedown", "keydown", "scroll", "mousemove", "touchstart"];

    const handleActivity = () => {
      resetTimer();
    };

    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [resetTimer]);

  // Продлить сеанс
  const extendSession = useCallback(() => {
    setShowWarning(false);
    setSecondsLeft(0);
    resetTimer();
  }, [resetTimer]);

  return { isLocked, showWarning, secondsLeft, extendSession };
}

/**
 * Компонент-обёртка для отображения предупреждения о блокировке
 */
export function SessionTimeoutWarning({ showWarning, secondsLeft, onExtend }) {
  if (!showWarning) return null;

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl shadow-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg
              className="w-5 h-5 text-yellow-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className="text-sm font-medium text-gray-900">
              Сеанс скоро истекает
            </p>
            <p className="mt-1 text-sm text-gray-600">
              Вы будете автоматически перенаправлены через{" "}
              <span className="font-mono font-bold text-yellow-700">
                {minutes}:{seconds.toString().padStart(2, "0")}
              </span>{" "}
              из-за неактивности.
            </p>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={onExtend}
              className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1 px-3 rounded-lg transition-colors text-sm min-h-[44px]"
            >
              Продлить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default useSessionTimeout;
