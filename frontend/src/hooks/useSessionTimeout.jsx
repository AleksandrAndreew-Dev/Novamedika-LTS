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
 * @returns {Object} { isLocked, showWarning, secondsLeft, extendSession }
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
    warningTimerRef.current = setTimeout(
      () => {
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
      },
      (timeoutMinutes * 60 - WARNING_TIME) * 1000,
    );

    // Таймер блокировки
    timerRef.current = setTimeout(
      () => {
        handleTimeout();
      },
      timeoutMinutes * 60 * 1000,
    );
  }, [timeoutMinutes, handleTimeout]);

  // Запуск при монтировании
  useEffect(() => {
    resetTimer();

    // Отслеживаем активность пользователя
    const events = [
      "mousedown",
      "keydown",
      "scroll",
      "mousemove",
      "touchstart",
    ];

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

export default useSessionTimeout;
