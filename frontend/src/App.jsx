import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  lazy,
  Suspense,
} from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  useLocation,
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
import { ChatProvider } from './context/ChatContext';
import ChatWidget from './components/ChatWidget/ChatWidget';

// Lazy-loaded page components for code splitting
const PharmacistDashboard = lazy(
  () => import('./pharmacist/PharmacistDashboard'),
);
const UploadPrescription = lazy(
  () => import('./pages/UploadPrescription'),
);
const Login = lazy(() => import('./pages/Login'));
const UserDashboard = lazy(
  () => import('./pages/UserDashboard'),
);
const Chat = lazy(() => import('./pages/Chat'));
const NewConsultation = lazy(
  () => import('./pages/NewConsultation'),
);

// Loading fallback shown during lazy component load
function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
        <p className="text-gray-500 text-sm">Загрузка...</p>
      </div>
    </div>
  );
}

/**
 * Отдельный компонент для ChatWidget / Telegram-ссылки.
 * Вынесен из App, так как useLocation() требует контекста BrowserRouter.
 * Скрывает виджет на страницах /chat/*, /pharmacist/*, /dashboard.
 */
function ChatWidgetOrLink() {
  const location = useLocation();
  const isChatPage = location.pathname.startsWith('/chat');
  const isExcludedPage =
    isChatPage ||
    location.pathname.startsWith('/pharmacist') ||
    location.pathname.startsWith('/dashboard');

  // На страницах чата/дашборда не показываем ничего
  if (isExcludedPage) return null;

  // В Telegram WebApp — ссылка на создание чата
  if (window.Telegram?.WebApp?.initData) {
    return (
      <a
        href={
          window.Telegram.WebApp.initDataUnsafe?.start_param
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
    );
  }

  // Веб-версия — ChatWidget
  return <ChatWidget />;
}

function App() {
  const [toast, setToast] = useState(null); // { message, type }
  const [showCookieBanner, setShowCookieBanner] =
    useState(false);
  const [consents, setConsents] = useState({
    privacyPolicy: false,
    dataProcessing: false,
    securityProtection: false,
  });

  // Кешируем проверку Telegram в sessionStorage для ускорения
  const isInTelegramCached = useMemo(() => {
    const cached = sessionStorage.getItem('isInTelegram');
    if (cached !== null) return cached === 'true';

    const result = !!(
      window.Telegram?.WebApp?.initData &&
      window.Telegram.WebApp.initData.length > 0
    );
    sessionStorage.setItem('isInTelegram', String(result));
    return result;
  }, []);

  // Проверяем, это pharmacist dashboard или обычный поиск
  // Определяем по поддомену ИЛИ по пути ИЛИ по наличию токена в URL (для WebApp)
  const hostname = window.location.hostname;
  const isPharmacistSubdomain =
    hostname.startsWith('pharmacist.') ||
    hostname === 'pharmacist.spravka.novamedika.com';
  const isPharmacistPath =
    window.location.pathname.startsWith('/pharmacist');

  // Проверяем наличие JWT токена в URL (WebApp authentication)
  const urlParams = new URLSearchParams(
    window.location.search,
  );
  const hasAuthToken = urlParams.has('token');

  // Проверяем наличие session token в localStorage (фармацевт уже залогинен)
  const hasPharmacistSession = !!localStorage.getItem(
    'pharmacist_session_token',
  );

  // Кешируем isPharmacistMode
  const isPharmacistMode = useMemo(
    () =>
      isPharmacistSubdomain ||
      isPharmacistPath ||
      (hasAuthToken && isInTelegramCached) ||
      hasPharmacistSession,
    [
      isPharmacistSubdomain,
      isPharmacistPath,
      hasAuthToken,
      hasPharmacistSession,
      isInTelegramCached,
    ],
  );

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
  const { showWarning, secondsLeft, extendSession } =
    useSessionTimeout(30);

  // Глобальный обработчик API ошибок
  const handleError = useCallback((error) => {
    const message = error.userMessage || error.message;
    setToast({
      message,
      type: 'error',
    });
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
    return () =>
      api.interceptors.response.eject(interceptor);
  }, [handleError]);

  useEffect(() => {
    const cookiesAccepted = localStorage.getItem(
      'cookiesAccepted',
    );

    const showConsentBanner = () => {
      if (!isPharmacistMode) {
        setShowCookieBanner(true);
      }
    };

    // Не блокируем рендер приложения на долгой проверке consent.
    // Сначала показываем интерфейс сразу, а проверку выполняем асинхронно.
    if (!isPharmacistMode) {
      if (cookiesAccepted) {
        setShowCookieBanner(false);
      } else {
        showConsentBanner();
      }
    }

    if (isInTelegramCached && !isPharmacistMode) {
      void checkTelegramConsent();
    }
  }, [isInTelegramCached, isPharmacistMode]);

  // Функция проверки согласия через API для Telegram WebApp с timeout
  const checkTelegramConsent = async () => {
    try {
      const tgUser =
        window.Telegram?.WebApp?.initDataUnsafe?.user;

      if (!tgUser) {
        return;
      }

      console.log(
        '[Telegram Consent] Checking consent for user:',
        tgUser.id,
      );

      // Ограничиваем время ожидания, чтобы не тормозить первый вход.
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        1500,
      );

      try {
        const response = await fetch(
          'https://api.spravka.novamedika.com/webapp/check-consent',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              telegram_id: tgUser.id,
              first_name: tgUser.first_name,
              last_name: tgUser.last_name,
              username: tgUser.username,
            }),
            signal: controller.signal,
          },
        );
        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(
            `HTTP error! status: ${response.status}`,
          );
        }

        const data = await response.json();

        if (data.needs_webapp_consent) {
          setShowCookieBanner(true);
        } else {
          localStorage.setItem('cookiesAccepted', 'true');
          setShowCookieBanner(false);
        }
      } catch (fetchError) {
        clearTimeout(timeoutId);
        if (fetchError.name === 'AbortError') {
          setShowCookieBanner(true);
          return;
        }
        throw fetchError;
      }
    } catch (error) {
      setShowCookieBanner(true);
    }
  };

  const handleConsentChange = (field) => {
    setConsents((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const allConsentsGiven = useMemo(
    () =>
      consents.privacyPolicy &&
      consents.dataProcessing &&
      consents.securityProtection,
    [
      consents.privacyPolicy,
      consents.dataProcessing,
      consents.securityProtection,
    ],
  );

  const handleAcceptCookies = () => {
    // Проверяем все согласия
    if (!allConsentsGiven) {
      setToast({
        message:
          'Пожалуйста, отметьте все необходимые согласия',
        type: 'error',
      });
      return;
    }

    setShowCookieBanner(false);
    localStorage.setItem('cookiesAccepted', 'true');
    document.cookie =
      'cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax';

    // Показываем success toast
    setToast({
      message: 'Настройки сохранены. Добро пожаловать!',
      type: 'success',
    });
  };

  // Если режим фармацевта - показываем dashboard (с Suspense для lazy)
  if (isPharmacistMode) {
    return (
      <Suspense fallback={<PageLoader />}>
        <PharmacistDashboard />
      </Suspense>
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
                showWarning={showWarning}
                secondsLeft={secondsLeft}
                onExtend={extendSession}
              />

              {/* Баннер cookies и согласий - НЕ блокирует контент */}
              {showCookieBanner && (
                <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-40 pointer-events-none">
                  <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto overscroll-behavior-contain touch-manipulation pointer-events-auto">
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
                              strokeWidth={2}
                              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                            />
                          </svg>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                          Защита персональных данных
                        </h2>
                        <p className="text-gray-600 text-sm">
                          Для использования сервиса
                          необходимо дать согласие на
                          обработку персональных данных
                        </p>
                      </div>

                      <div className="space-y-4 mb-6">
                        <div
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors relative z-10 min-h-[44px] touch-action-manipulation"
                          onClick={() =>
                            handleConsentChange(
                              'privacyPolicy',
                            )
                          }
                          role="checkbox"
                          aria-checked={
                            consents.privacyPolicy
                          }
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (
                              e.key === 'Enter' ||
                              e.key === ' '
                            ) {
                              e.preventDefault();
                              handleConsentChange(
                                'privacyPolicy',
                              );
                            }
                          }}
                        >
                          <input
                            id="consent-privacy"
                            type="checkbox"
                            checked={consents.privacyPolicy}
                            onChange={() => {}}
                            required
                            className="mt-1 w-[22px] h-[22px] text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                            readOnly
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я согласен на обработку моих
                            персональных данных в
                            соответствии с{' '}
                            <a
                              href="/privacy-policy"
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) =>
                                e.stopPropagation()
                              }
                              className="text-blue-600 hover:text-blue-800 underline font-medium"
                            >
                              Политикой конфиденциальности
                            </a>
                            . Срок хранения: 1 год после
                            последнего обращения.
                          </span>
                        </div>

                        <div
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors relative z-10 min-h-[44px] touch-action-manipulation"
                          onClick={() =>
                            handleConsentChange(
                              'dataProcessing',
                            )
                          }
                          role="checkbox"
                          aria-checked={
                            consents.dataProcessing
                          }
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (
                              e.key === 'Enter' ||
                              e.key === ' '
                            ) {
                              e.preventDefault();
                              handleConsentChange(
                                'dataProcessing',
                              );
                            }
                          }}
                        >
                          <input
                            id="consent-processing"
                            type="checkbox"
                            checked={
                              consents.dataProcessing
                            }
                            onChange={() => {}}
                            required
                            className="mt-1 w-[22px] h-[22px] text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                            readOnly
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я согласен на обработку данных
                            для поиска лекарств и проведения
                            онлайн-консультаций с
                            фармацевтами.
                          </span>
                        </div>

                        <div
                          className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 transition-colors relative z-10 min-h-[44px] touch-action-manipulation"
                          onClick={() =>
                            handleConsentChange(
                              'securityProtection',
                            )
                          }
                          role="checkbox"
                          aria-checked={
                            consents.securityProtection
                          }
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (
                              e.key === 'Enter' ||
                              e.key === ' '
                            ) {
                              e.preventDefault();
                              handleConsentChange(
                                'securityProtection',
                              );
                            }
                          }}
                        >
                          <input
                            id="consent-security"
                            type="checkbox"
                            checked={
                              consents.securityProtection
                            }
                            onChange={() => {}}
                            required
                            className="mt-1 w-[22px] h-[22px] text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                            readOnly
                          />
                          <span className="text-sm text-gray-700 leading-relaxed">
                            Я подтверждаю, что ознакомлен с
                            тем, что мои данные будут
                            зашифрованы и защищены в
                            соответствии с требованиями ОАЦ
                            РБ (класс ИС 3-ин).
                          </span>
                        </div>
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
                          Подробнее о политике
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
                  element={<PrivacyPolicy />}
                />
                <Route path="/login" element={<Login />} />
                <Route
                  path="/register"
                  element={
                    <div className="min-h-screen flex items-center justify-center">
                      Registration page coming soon
                    </div>
                  }
                />
                <Route
                  path="/dashboard"
                  element={<UserDashboard />}
                />
                <Route
                  path="/chat/new"
                  element={<NewConsultation />}
                />
                <Route
                  path="/chat/:id"
                  element={<Chat />}
                />
                <Route
                  path="/prescriptions/upload"
                  element={<UploadPrescription />}
                />
                <Route path="/*" element={<Search />} />
              </Routes>

              <ChatWidgetOrLink />

              {/* Toast уведомления */}
              {toast && (
                <Toast
                  message={toast.message}
                  type={toast.type}
                  onClose={() => setToast(null)}
                  duration={
                    toast.type === 'error' ? 5000 : 3000
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
