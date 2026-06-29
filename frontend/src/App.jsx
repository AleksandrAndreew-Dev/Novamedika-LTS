import {
  useState,
  useEffect,
  useCallback,
} from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
} from 'react-router-dom';
import './App.css';
import Search from './components/Search';
import PrivacyPolicy from './components/PrivacyPolicy';
import SessionTimeoutWarning from './components/SessionTimeoutWarning';
import Toast from './components/Toast';
import useSessionTimeout from './hooks/useSessionTimeout';
import { TelegramProvider } from './telegram/TelegramContext';
import TelegramWrapper from './telegram/TelegramWrapper';
import { api } from './api/client';
import PharmacistDashboard from './pharmacist/PharmacistDashboard';
import UploadPrescription from './pages/UploadPrescription';
import Login from './pages/Login';
import UserDashboard from './pages/UserDashboard';
import Chat from './pages/Chat';
import NewConsultation from './pages/NewConsultation';
import { ChatProvider } from './context/ChatContext';
import ChatWidget from './components/ChatWidget/ChatWidget';

function App() {
  const [toast, setToast] =
    useState(null); // { message, type }
  const [
    showCookieBanner,
    setShowCookieBanner,
  ] = useState(false);
  const [
    consents,
    setConsents,
  ] = useState({
    privacyPolicy: false,
    dataProcessing: false,
    securityProtection: false,
  });

  // Проверяем, это pharmacist dashboard или обычный поиск
  // Определяем по поддомену ИЛИ по пути ИЛИ по наличию токена в URL (для WebApp)
  const hostname =
    window.location.hostname;
  const isPharmacistSubdomain =
    hostname.startsWith(
      'pharmacist.',
    ) ||
    hostname ===
      'pharmacist.spravka.novamedika.com';
  const isPharmacistPath =
    window.location.pathname.startsWith(
      '/pharmacist',
    );

  // Проверяем наличие JWT токена в URL (WebApp authentication)
  const urlParams =
    new URLSearchParams(
      window.location.search,
    );
  const hasAuthToken =
    urlParams.has('token');

  // Проверяем наличие session token в localStorage (фармацевт уже залогинен)
  const hasPharmacistSession =
    !!localStorage.getItem(
      'pharmacist_session_token',
    );

  // Упрощенная проверка: если мы внутри Telegram WebApp, считаем что это может быть фармацевт
  // Финальная проверка регистрации произойдет на бэкенде при логине
  const isInTelegram =
    !!window.Telegram?.WebApp;

  const isPharmacistMode =
    isPharmacistSubdomain ||
    isPharmacistPath ||
    (hasAuthToken &&
      isInTelegram) ||
    hasPharmacistSession;

  // Сохраняем режим в localStorage при первом определении
  useEffect(() => {
    if (isPharmacistMode) {
      localStorage.setItem(
        'app_mode',
        'pharmacist',
      );
    } else {
      // Если пользователь перешел на основной сайт, очищаем режим
      localStorage.removeItem(
        'app_mode',
      );
    }
  }, [isPharmacistMode]);

  // Инициализация хука таймаута (30 минут)
  const {
    showWarning,
    secondsLeft,
    extendSession,
  } = useSessionTimeout(30);

  // Глобальный обработчик API ошибок
  const handleError =
    useCallback((error) => {
      const message =
        error.userMessage ||
        error.message;
      setToast({
        message,
        type: 'error',
      });
    }, []);

  useEffect(() => {
    const interceptor =
      api.interceptors.response.use(
        (r) => r,
        (error) => {
          if (
            error.isApiError ||
            error.userMessage
          ) {
            handleError(
              error,
            );
          }
          return Promise.reject(
            error,
          );
        },
      );
    return () =>
      api.interceptors.response.eject(
        interceptor,
      );
  }, [handleError]);

  useEffect(() => {
    // Проверяем, действительно ли мы внутри Telegram WebApp
    // window.Telegram.WebApp существует всегда после загрузки SDK,
    // но initData заполняется только когда приложение открыто внутри Telegram
    const isInTelegram = !!(
      window.Telegram?.WebApp
        ?.initData &&
      window.Telegram.WebApp
        .initData.length > 0
    );
    const cookiesAccepted =
      localStorage.getItem(
        'cookiesAccepted',
      );

    // Debug logging для production диагностики
    console.log(
      '[Consent Modal Check]',
      {
        isInTelegram,
        hasTelegramSDK:
          !!window.Telegram
            ?.WebApp,
        hasInitData:
          !!window.Telegram
            ?.WebApp
            ?.initData,
        initDataLength:
          window.Telegram
            ?.WebApp?.initData
            ?.length || 0,
        cookiesAccepted,
        protocol:
          window.location
            .protocol,
        hostname:
          window.location
            .hostname,
        pathname:
          window.location
            .pathname,
        isPharmacistMode,
      },
    );

    // Если мы в Telegram WebApp - проверяем согласие через API
    if (
      isInTelegram &&
      !isPharmacistMode
    ) {
      checkTelegramConsent();
    } else if (
      !isInTelegram &&
      !cookiesAccepted &&
      !isPharmacistMode
    ) {
      // Для обычного браузера показываем модальное окно если нет согласия
      console.log(
        '[Consent Modal] ✅ Showing modal',
      );
      setShowCookieBanner(
        true,
      );
    } else {
      console.log(
        '[Consent Modal] ❌ NOT showing',
        {
          reason: isInTelegram
            ? 'in Telegram (checking via API)'
            : cookiesAccepted
              ? 'already accepted'
              : 'pharmacist mode',
        },
      );
    }
  }, [isPharmacistMode]);

  // Функция проверки согласия через API для Telegram WebApp
  const checkTelegramConsent =
    async () => {
      try {
        const tgUser =
          window.Telegram
            ?.WebApp
            ?.initDataUnsafe
            ?.user;

        if (!tgUser) {
          console.log(
            '[Telegram Consent] No user data in initData',
          );
          return;
        }

        console.log(
          '[Telegram Consent] Checking consent for user:',
          tgUser.id,
        );

        // Вызываем endpoint на правильном хосте (api subdomain)
        const response =
          await fetch(
            'https://api.spravka.novamedika.com/webapp/check-consent',
            {
              method: 'POST',
              headers: {
                'Content-Type':
                  'application/json',
              },
              body: JSON.stringify(
                {
                  telegram_id:
                    tgUser.id,
                  first_name:
                    tgUser.first_name,
                  last_name:
                    tgUser.last_name,
                  username:
                    tgUser.username,
                },
              ),
            },
          );

        if (!response.ok) {
          throw new Error(
            `HTTP error! status: ${response.status}`,
          );
        }

        const data =
          await response.json();
        console.log(
          '[Telegram Consent] Response:',
          data,
        );

        // Если нужно дополнительное согласие для WebApp - показываем модальное окно
        if (
          data.needs_webapp_consent
        ) {
          console.log(
            '[Telegram Consent] ✅ Additional consent needed - showing modal',
          );
          setShowCookieBanner(
            true,
          );
        } else {
          console.log(
            '[Telegram Consent] ❌ Consent already given - no modal needed',
          );
          // Сохраняем флаг что согласие уже есть
          localStorage.setItem(
            'cookiesAccepted',
            'true',
          );
        }
      } catch (error) {
        console.error(
          '[Telegram Consent] Error checking consent:',
          error,
        );
        // В случае ошибки показываем модальное окно для безопасности
        setShowCookieBanner(
          true,
        );
      }
    };

  const handleConsentChange =
    (field) => {
      setConsents((prev) => ({
        ...prev,
        [field]: !prev[field],
      }));
    };

  const allConsentsGiven =
    consents.privacyPolicy &&
    consents.dataProcessing &&
    consents.securityProtection;

  const handleAcceptCookies =
    () => {
      // Проверяем все согласия
      if (!allConsentsGiven) {
        setToast({
          message:
            'Пожалуйста, отметьте все необходимые согласия',
          type: 'error',
        });
        return;
      }

      setShowCookieBanner(
        false,
      );
      localStorage.setItem(
        'cookiesAccepted',
        'true',
      );
      document.cookie =
        'cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax';

      // Показываем success toast
      setToast({
        message:
          'Настройки сохранены. Добро пожаловать!',
        type: 'success',
      });
    };

  // Если режим фармацевта - показываем dashboard
  if (isPharmacistMode) {
    return (
      <PharmacistDashboard />
    );
  }

  return (
    <TelegramProvider>
      <TelegramWrapper>
        <BrowserRouter>
          <ChatProvider>
            <div className="App">
              {/* Компонент предупреждения о таймауте */}
              <SessionTimeoutWarning
                showWarning={
                  showWarning
                }
                secondsLeft={
                  secondsLeft
                }
                onExtend={
                  extendSession
                }
              />

              {/* Баннер cookies и согласий */}
              {showCookieBanner && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
                  <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                    <div className="p-6">
                      <div className="text-center mb-6">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                          <svg
                            className="w-8 h-8 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={
                                2
                              }
                              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                            />
                          </svg>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                          Защита
                          персональных
                          данных
                        </h2>
                        <p className="text-gray-600 text-sm">
                          Для
                          использования
                          сервиса
                          необходимо
                          дать
                          согласие
                          на
                          обработку
                          персональных
                          данных
                        </p>
                      </div>

                      <div className="space-y-4 mb-6">
                        <label
                          htmlFor="consent-privacy"
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors"
                          style={{
                            touchAction:
                              'manipulation',
                            pointerEvents:
                              'auto',
                          }}
                        >
                          <input
                            id="consent-privacy"
                            type="checkbox"
                            checked={
                              consents.privacyPolicy
                            }
                            onChange={() =>
                              handleConsentChange(
                                'privacyPolicy',
                              )
                            }
                            onClick={(
                              e,
                            ) =>
                              e.stopPropagation()
                            }
                            required
                            style={{
                              touchAction:
                                'manipulation',
                              pointerEvents:
                                'auto',
                            }}
                            className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я
                            согласен
                            на
                            обработку
                            моих
                            персональных
                            данных
                            в
                            соответствии
                            с{' '}
                            <a
                              href="/privacy-policy"
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(
                                e,
                              ) =>
                                e.stopPropagation()
                              }
                              className="text-blue-600 hover:text-blue-800 underline font-medium"
                            >
                              Политикой
                              конфиденциальности
                            </a>
                            .
                            Срок
                            хранения:
                            1
                            год
                            после
                            последнего
                            обращения.
                          </span>
                        </label>

                        <label
                          htmlFor="consent-processing"
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors"
                          style={{
                            touchAction:
                              'manipulation',
                            pointerEvents:
                              'auto',
                          }}
                        >
                          <input
                            id="consent-processing"
                            type="checkbox"
                            checked={
                              consents.dataProcessing
                            }
                            onChange={() =>
                              handleConsentChange(
                                'dataProcessing',
                              )
                            }
                            onClick={(
                              e,
                            ) =>
                              e.stopPropagation()
                            }
                            required
                            style={{
                              touchAction:
                                'manipulation',
                              pointerEvents:
                                'auto',
                            }}
                            className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я
                            согласен
                            на
                            обработку
                            данных
                            для
                            поиска
                            лекарств
                            и
                            проведения
                            онлайн-консультаций
                            с
                            фармацевтами.
                          </span>
                        </label>

                        <label
                          htmlFor="consent-security"
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors"
                          style={{
                            touchAction:
                              'manipulation',
                            pointerEvents:
                              'auto',
                          }}
                        >
                          <input
                            id="consent-security"
                            type="checkbox"
                            checked={
                              consents.securityProtection
                            }
                            onChange={() =>
                              handleConsentChange(
                                'securityProtection',
                              )
                            }
                            onClick={(
                              e,
                            ) =>
                              e.stopPropagation()
                            }
                            required
                            style={{
                              touchAction:
                                'manipulation',
                              pointerEvents:
                                'auto',
                            }}
                            className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я
                            подтверждаю,
                            что
                            ознакомлен
                            с
                            тем,
                            что
                            мои
                            данные
                            будут
                            зашифрованы
                            и
                            защищены
                            в
                            соответствии
                            с
                            требованиями
                            ОАЦ
                            РБ
                            (класс
                            ИС
                            3-ин).
                          </span>
                        </label>
                      </div>

                      <div className="flex flex-col space-y-3">
                        <button
                          onClick={
                            handleAcceptCookies
                          }
                          disabled={
                            !allConsentsGiven
                          }
                          className={`font-medium py-3 px-4 rounded-xl transition-all text-sm ${
                            allConsentsGiven
                              ? 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg'
                              : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                          }`}
                        >
                          Принять
                          и
                          продолжить
                        </button>
                        <a
                          href="/privacy-policy"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 font-medium py-2 text-sm text-center underline"
                        >
                          Подробнее
                          о
                          политике
                          конфиденциальности
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <Routes>
                <Route
                  path="/privacy-policy"
                  element={
                    <PrivacyPolicy />
                  }
                />
                <Route
                  path="/login"
                  element={
                    <Login />
                  }
                />
                <Route
                  path="/register"
                  element={
                    <div className="min-h-screen flex items-center justify-center">
                      Registration
                      page
                      coming
                      soon
                    </div>
                  }
                />
                <Route
                  path="/dashboard"
                  element={
                    <UserDashboard />
                  }
                />
                <Route
                  path="/chat/new"
                  element={
                    <NewConsultation />
                  }
                />
                <Route
                  path="/chat/:id"
                  element={
                    <Chat />
                  }
                />
                <Route
                  path="/prescriptions/upload"
                  element={
                    <UploadPrescription />
                  }
                />
                <Route
                  path="/*"
                  element={
                    <Search />
                  }
                />
              </Routes>

              {/* ChatWidget — для веб-версии; в Telegram показываем fallback-ссылку */}
              {window.Telegram
                ?.WebApp
                ?.initData ? (
                <a
                  href={
                    window
                      .Telegram
                      .WebApp
                      .initDataUnsafe
                      ?.start_param
                      ? `/?start=${window.Telegram.WebApp.initDataUnsafe.start_param}`
                      : '/chat/new'
                  }
                  className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg flex items-center justify-center text-white hover:shadow-xl transition-shadow active:scale-90"
                  aria-label="Чат с фармацевтом"
                >
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </a>
              ) : (
                <ChatWidget />
              )}

              {/* Toast уведомления */}
              {toast && (
                <Toast
                  message={
                    toast.message
                  }
                  type={
                    toast.type
                  }
                  onClose={() =>
                    setToast(
                      null,
                    )
                  }
                  duration={
                    toast.type ===
                    'error'
                      ? 5000
                      : 3000
                  }
                />
              )}
            </div>
          </ChatProvider>
        </BrowserRouter>
      </TelegramWrapper>
    </TelegramProvider>
  );
}

export default App;
