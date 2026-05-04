import { useState, useEffect, useCallback } from "react";
import "./App.css";
import Search from "./components/Search";
import PrivacyPolicy from "./components/PrivacyPolicy";
import SessionTimeoutWarning from "./components/SessionTimeoutWarning";
import Toast from "./components/Toast";
import useSessionTimeout from "./hooks/useSessionTimeout";
import { TelegramProvider } from "./telegram/TelegramContext";
import TelegramWrapper from "./telegram/TelegramWrapper";
import { api } from "./api/client";
import PharmacistDashboard from "./pharmacist/PharmacistDashboard";

function App() {
  const [page, setPage] = useState(window.location.pathname);
  const [toast, setToast] = useState(null); // { message, type }
  const [showCookieBanner, setShowCookieBanner] = useState(false);
  const [consents, setConsents] = useState({
    privacyPolicy: false,
    dataProcessing: false,
    securityProtection: false,
  });

  // Проверяем, это pharmacist dashboard или обычный поиск
  // Определяем по поддомену ИЛИ по пути ИЛИ по наличию токена в URL (для WebApp)
  const hostname = window.location.hostname;
  const isPharmacistSubdomain = hostname.startsWith('pharmacist.') || hostname === 'pharmacist.spravka.novamedika.com';
  const isPharmacistPath = window.location.pathname.startsWith('/pharmacist');
  
  // Проверяем наличие JWT токена в URL (WebApp authentication)
  const urlParams = new URLSearchParams(window.location.search);
  const hasAuthToken = urlParams.has('token');
  
  // Упрощенная проверка: если мы внутри Telegram WebApp, считаем что это может быть фармацевт
  // Финальная проверка регистрации произойдет на бэкенде при логине
  const isInTelegram = !!window.Telegram?.WebApp;
  
  const isPharmacistMode = isPharmacistSubdomain || isPharmacistPath || (hasAuthToken && isInTelegram);

  // Сохраняем режим в localStorage при первом определении
  useEffect(() => {
    if (isPharmacistMode) {
      localStorage.setItem('app_mode', 'pharmacist');
    } else {
      // Если пользователь перешел на основной сайт, очищаем режим
      localStorage.removeItem('app_mode');
    }
  }, [isPharmacistMode]);

  // Инициализация хука таймаута (30 минут)
  const { showWarning, secondsLeft, extendSession } = useSessionTimeout(30);

  // Отслеживаем изменение pathname (кнопки назад/вперёд в браузере)
  useEffect(() => {
    const onPopState = () => setPage(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Глобальный обработчик API ошибок
  const handleError = useCallback((error) => {
    const message = error.userMessage || error.message;
    setToast({ message, type: 'error' });
  }, []);

  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      (r) => r,
      (error) => {
        if (error.isApiError || error.userMessage) {
          handleError(error);
        }
        return Promise.reject(error);
      },
    );
    return () => api.interceptors.response.eject(interceptor);
  }, [handleError]);

  useEffect(() => {
    const isInTelegram = window.Telegram?.WebApp;
    if (
      window.location.protocol === "https:" &&
      !localStorage.getItem("cookiesAccepted") &&
      !isInTelegram
    ) {
      setShowCookieBanner(true);
    }
  }, []);

  const handleConsentChange = (field) => {
    setConsents(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const allConsentsGiven = consents.privacyPolicy && consents.dataProcessing && consents.securityProtection;

  const handleAcceptCookies = () => {
    // Проверяем все согласия
    if (!allConsentsGiven) {
      setToast({ message: 'Пожалуйста, отметьте все необходимые согласия', type: 'error' });
      return;
    }

    setShowCookieBanner(false);
    localStorage.setItem("cookiesAccepted", "true");
    document.cookie =
      "cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax";
    
    // Показываем success toast
    setToast({ message: 'Настройки сохранены. Добро пожаловать!', type: 'success' });
  };

  // Если режим фармацевта - показываем dashboard
  if (isPharmacistMode) {
    return <PharmacistDashboard />;
  }

  // Простой роутинг по pathname
  if (page === "/privacy-policy") {
    return <PrivacyPolicy />;
  }

  return (
    <TelegramProvider>
      <TelegramWrapper>
        <div className="App">
          {/* Компонент предупреждения о таймауте */}
          <SessionTimeoutWarning
            showWarning={showWarning}
            secondsLeft={secondsLeft}
            onExtend={extendSession}
          />

          {/* Баннер cookies и согласий */}
          {showCookieBanner && (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">
                      Защита персональных данных
                    </h2>
                    <p className="text-gray-600 text-sm">
                      Для использования сервиса необходимо дать согласие на обработку персональных данных
                    </p>
                  </div>

                  <div className="space-y-4 mb-6">
                    <label className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={consents.privacyPolicy}
                        onChange={() => handleConsentChange('privacyPolicy')}
                        required
                        className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                      />
                      <span className="text-sm text-gray-700 leading-relaxed">
                        Я согласен на обработку моих персональных данных в соответствии с{" "}
                        <a
                          href="/privacy-policy"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 underline font-medium"
                        >
                          Политикой конфиденциальности
                        </a>
                        . Срок хранения: 1 год после последнего обращения.
                      </span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={consents.dataProcessing}
                        onChange={() => handleConsentChange('dataProcessing')}
                        required
                        className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                      />
                      <span className="text-sm text-gray-700 leading-relaxed">
                        Я согласен на обработку данных для поиска лекарств и проведения онлайн-консультаций с фармацевтами.
                      </span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={consents.securityProtection}
                        onChange={() => handleConsentChange('securityProtection')}
                        required
                        className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                      />
                      <span className="text-sm text-gray-700 leading-relaxed">
                        Я подтверждаю, что ознакомлен с тем, что мои данные будут зашифрованы и защищены в соответствии с требованиями ОАЦ РБ (класс ИС 3-ин).
                      </span>
                    </label>
                  </div>

                  <div className="flex flex-col space-y-3">
                    <button
                      onClick={handleAcceptCookies}
                      disabled={!allConsentsGiven}
                      className={`font-medium py-3 px-4 rounded-xl transition-all text-sm ${
                        allConsentsGiven
                          ? 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg'
                          : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      Принять и продолжить
                    </button>
                    <a
                      href="/privacy-policy"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium py-2 text-sm text-center underline"
                    >
                      Подробнее о политике конфиденциальности
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Основной компонент поиска */}
          <Search />

          {/* Toast уведомления */}
          {toast && (
            <Toast
              message={toast.message}
              type={toast.type}
              onClose={() => setToast(null)}
              duration={toast.type === 'error' ? 5000 : 3000}
            />
          )}
        </div>
      </TelegramWrapper>
    </TelegramProvider>
  );
}

export default App;
