import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
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
  const [isExpanded, setIsExpanded] = useState(false);
  const [consents, setConsents] = useState({
    privacyPolicy: false,
    dataProcessing: false,
    securityProtection: false,
  });
  const [cookieConsents, setCookieConsents] = useState({
    technical: true,
    analytics: false,
  });
  const firstCheckboxRef = useRef(null);
  const modalRef = useRef(null);

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
    } catch {
      setShowCookieBanner(true);
    }
  };

  const handleConsentChange = (field) => {
    setConsents((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleCookieConsentChange = (field) => {
    setCookieConsents((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const allPdConsentsGiven = useMemo(
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

  const areAllConsentsReady = useMemo(
    () => allPdConsentsGiven && cookieConsents.technical,
    [allPdConsentsGiven, cookieConsents.technical],
  );

  // Фокус на первый чекбокс при разворачивании
  useEffect(() => {
    if (isExpanded && firstCheckboxRef.current) {
      firstCheckboxRef.current.focus();
    }
  }, [isExpanded]);

  const handleAcceptAll = () => {
    setCookieConsents({
      technical: true,
      analytics: true,
    });
    setConsents({
      privacyPolicy: true,
      dataProcessing: true,
      securityProtection: true,
    });
    setIsExpanded(false);
    setShowCookieBanner(false);
    localStorage.setItem('cookiesAccepted', 'true');
    document.cookie =
      'cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax';

    setToast({
      message: 'Настройки сохранены. Добро пожаловать!',
      type: 'success',
    });
  };

  const handleDeclineAll = () => {
    setCookieConsents({
      technical: true,
      analytics: false,
    });
    setConsents({
      privacyPolicy: false,
      dataProcessing: false,
      securityProtection: false,
    });
    setIsExpanded(false);
    setShowCookieBanner(false);
    localStorage.setItem('cookiesAccepted', 'false');
    document.cookie =
      'cookies_accepted=false; max-age=31536000; path=/; Secure; SameSite=Lax';

    setToast({
      message:
        'Вы отказались от необязательных согласий. Часть функционала будет ограничена.',
      type: 'warning',
    });
  };

  const handleSavePreferences = () => {
    setIsExpanded(false);
    setShowCookieBanner(false);
    localStorage.setItem('cookiesAccepted', 'true');
    document.cookie =
      'cookies_accepted=true; max-age=31536000; path=/; Secure; SameSite=Lax';

    setToast({
      message: 'Ваши предпочтения сохранены.',
      type: 'success',
    });
  };

  const handleCloseExpanded = () => {
    setIsExpanded(false);
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

              {/* Баннер cookie + ПД: collapsed bottom bar + expanded modal */}
              {showCookieBanner && (
                <>
                  {/* Collapsed: нижний баннер */}
                  <div className="fixed bottom-0 left-0 right-0 z-40 pointer-events-none">
                    <div className="bg-white shadow-2xl rounded-t-2xl pointer-events-auto">
                      <div className="px-4 sm:px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
                        <div className="flex items-center gap-3 flex-1 min-w-[200px]">
                          <svg
                            width="64"
                            height="64"
                            viewBox="0 0 64 64"
                            fill="none"
                            className="hidden sm:block flex-shrink-0"
                          >
                            <path
                              d="M22.8596 34.2851V34.308M32 43.4255V43.4484M32 32V32.0229M41.1404 36.5702V36.5931M29.7149 22.8596V22.8824M34.6233 12.5218L40.7177 15.0445C39.5098 16.6336 38.8554 18.5744 38.8542 20.5705C38.8531 22.5665 39.5054 24.508 40.7115 26.0985C41.9175 27.6889 43.611 28.8409 45.5333 29.3784C47.4556 29.9159 49.501 29.8093 51.3571 29.0751L51.4782 29.3767C52.1739 31.0564 52.1739 32.9436 51.4782 34.6233C50.3433 36.4209 49.5633 37.8316 49.1383 38.8553C48.7072 39.8973 48.2044 41.5852 47.6301 43.9191C46.9338 45.5985 45.5989 46.9326 43.9191 47.6278C41.5243 48.228 39.8364 48.7315 38.8553 49.1383C37.7706 49.5877 36.36 50.3677 34.6233 51.4782C32.9436 52.1739 31.0564 52.1739 29.3767 51.4782C27.544 50.3296 26.1334 49.5496 25.1447 49.1383C24.0676 48.6934 22.3797 48.1907 20.0809 47.6301C18.4015 46.9338 17.0674 45.5989 16.3722 43.9191C15.7674 41.5167 15.2639 39.8288 14.8617 38.8553C14.4078 37.7615 13.6278 36.3508 12.5218 34.6233C11.8261 32.9436 11.8261 31.0564 12.5218 29.3767C13.6171 27.6766 14.3971 26.2659 14.8617 25.1447C15.2532 24.2002 15.756 22.5123 16.3699 20.0809C17.0662 18.4015 18.4011 17.0674 20.0809 16.3722C22.4376 15.7872 24.1255 15.2837 25.1447 14.8617C26.1913 14.4276 27.6019 13.6476 29.3767 12.5218C31.0564 11.8261 32.9436 11.8261 34.6233 12.5218Z"
                              stroke="#6B7280"
                              strokeWidth="1.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                          <p className="text-sm text-gray-700">
                            Для корректной работы сайта мы
                            используем файлы cookie. Для
                            использования сервиса требуется
                            согласие на обработку
                            персональных данных.
                            <button
                              type="button"
                              onClick={() =>
                                setIsExpanded(true)
                              }
                              className="text-blue-600 underline ml-2"
                            >
                              Настроить файлы cookie
                            </button>
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={handleAcceptAll}
                            className="px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow hover:from-blue-600 hover:to-purple-700"
                          >
                            Принять все
                          </button>
                          <button
                            onClick={handleDeclineAll}
                            className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
                          >
                            Отклонить все
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded: модальное окно настроек */}
                  {isExpanded && (
                    <div
                      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
                      onClick={handleCloseExpanded}
                    >
                      <div
                        ref={modalRef}
                        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold text-gray-900">
                              Настройка параметров
                              использования файлов cookie и
                              согласий
                            </h2>
                            <button
                              onClick={handleCloseExpanded}
                              className="p-2 rounded-full hover:bg-gray-100"
                              aria-label="Закрыть"
                            >
                              <svg
                                width="20"
                                height="20"
                                viewBox="0 0 20 20"
                                fill="none"
                              >
                                <path
                                  fillRule="evenodd"
                                  clipRule="evenodd"
                                  d="M4.19526 4.19526C4.45561 3.93491 4.87772 3.93491 5.13807 4.19526L10 9.05719L14.8619 4.19526C15.1223 3.93491 15.5444 3.93491 15.8047 4.19526C16.0651 4.45561 16.0651 4.87772 15.8047 5.13807L10.9428 10L15.8047 14.8619C16.0651 15.1223 16.0651 15.5444 15.8047 15.8047C15.5444 16.0651 15.1223 16.0651 14.8619 15.8047L10 10.9428L5.13807 15.8047C4.87772 16.0651 4.45561 16.0651 4.19526 15.8047C3.93491 15.5444 3.93491 15.1223 4.19526 14.8619L9.05719 10L4.19526 5.13807C3.93491 4.87772 3.93491 4.45561 4.19526 4.19526Z"
                                  fill="#6b7280"
                                />
                              </svg>
                            </button>
                          </div>

                          <div className="flex items-start gap-3 p-4 rounded-xl bg-yellow-50 border border-yellow-200 mb-6">
                            <svg
                              width="20"
                              height="20"
                              viewBox="0 0 20 20"
                              fill="none"
                              className="flex-shrink-0 mt-0.5"
                            >
                              <path
                                d="M10.781 14.75C10.781 14.9572 10.6987 15.156 10.5522 15.3025C10.4057 15.449 10.207 15.5313 9.99977 15.5313C9.79257 15.5313 9.59386 15.449 9.44735 15.3025C9.30083 15.156 9.21852 14.9572 9.21852 14.75C9.21852 14.5428 9.30083 14.3441 9.44735 14.1976C9.59386 14.0511 9.79257 13.9688 9.99977 13.9688C10.207 13.9688 10.4057 14.0511 10.5522 14.1976C10.6987 14.3441 10.781 14.5428 10.781 14.75ZM9.99977 6.62504C9.83401 6.62504 9.67504 6.69089 9.55783 6.8081C9.44062 6.92531 9.37477 7.08428 9.37477 7.25004V12.25C9.37477 12.4158 9.44062 12.5748 9.55783 12.692C9.67504 12.8092 9.83401 12.875 9.99977 12.875C10.1655 12.875 10.3245 12.8092 10.4417 12.692C10.5589 12.5748 10.6248 12.4158 10.6248 12.25V7.25004C10.6248 7.08428 10.5589 6.92531 10.4417 6.8081C10.3245 6.69089 10.1655 6.62504 9.99977 6.62504ZM8.08477 3.38066C8.91727 1.87441 11.0823 1.87441 11.9148 3.38066L18.4729 15.255C19.2785 16.7125 18.2235 18.5 16.5585 18.5H3.44165C1.77602 18.5 0.721648 16.7125 1.52665 15.255L8.08477 3.38066ZM10.8204 3.98504C10.7394 3.83835 10.6205 3.71607 10.4762 3.63091C10.3319 3.54576 10.1673 3.50084 9.99977 3.50084C9.8322 3.50084 9.66769 3.54576 9.52336 3.63091C9.37903 3.71607 9.26017 3.83835 9.17915 3.98504L2.62102 15.8594C2.54222 16.0021 2.502 16.163 2.50434 16.326C2.50668 16.489 2.55149 16.6486 2.63434 16.789C2.7172 16.9294 2.83525 17.0458 2.97682 17.1266C3.1184 17.2075 3.27861 17.25 3.44165 17.25H16.5585C16.7216 17.25 16.8818 17.2075 17.0233 17.1266C17.1649 17.0458 17.283 16.9294 17.3658 16.789C17.4487 16.6486 17.4935 16.489 17.4958 16.326C17.4982 16.163 17.4579 16.0021 17.3791 15.8594L10.8204 3.98504Z"
                                fill="#EC9F04"
                              />
                            </svg>
                            <p className="text-sm text-gray-700">
                              Вы можете настроить
                              использование каждого типа
                              файлов cookie, за исключением
                              типа «функциональные
                              (технические)», без которых
                              невозможно корректное
                              функционирование сайта.
                            </p>
                          </div>

                          <p className="text-sm text-gray-700 mb-6">
                            Перед тем как совершить выбор
                            настроек параметров
                            использования файлов cookie Вы
                            можете ознакомиться с{' '}
                            <a
                              href="/privacy-policy"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 underline"
                            >
                              Политикой обработки файлов
                              cookie
                            </a>
                            .
                          </p>

                          {/* Cookie чекбоксы */}
                          <div className="space-y-4 mb-6">
                            <label className="flex items-start gap-3">
                              <input
                                type="checkbox"
                                checked={
                                  cookieConsents.technical
                                }
                                disabled
                                className="mt-1 w-5 h-5"
                              />
                              <div>
                                <span className="text-sm font-medium text-gray-900">
                                  Функциональные
                                  (технические)
                                </span>
                                <p className="text-xs text-gray-600">
                                  Данный тип cookie-файлов
                                  требуется для обеспечения
                                  функционирования Сайта и
                                  не подлежит отключению.
                                </p>
                              </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={
                                  cookieConsents.analytics
                                }
                                onChange={() =>
                                  handleCookieConsentChange(
                                    'analytics',
                                  )
                                }
                                className="mt-1 w-5 h-5"
                              />
                              <div>
                                <span className="text-sm font-medium text-gray-900">
                                  Аналитические
                                </span>
                                <p className="text-xs text-gray-600">
                                  Данные cookie-файлы
                                  необходимы в
                                  статистических целях и
                                  помогают улучшать
                                  производительность сайта.
                                </p>
                              </div>
                            </label>
                          </div>

                          {/* ПД чекбоксы */}
                          <div className="border-t border-gray-200 pt-4 mb-6">
                            <h3 className="text-sm font-semibold text-gray-900 mb-3">
                              Согласия на обработку
                              персональных данных
                            </h3>
                            <div className="space-y-3">
                              <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={
                                    consents.privacyPolicy
                                  }
                                  onChange={() =>
                                    handleConsentChange(
                                      'privacyPolicy',
                                    )
                                  }
                                  className="mt-1 w-5 h-5"
                                />
                                <span className="text-sm text-gray-700">
                                  Я согласен на обработку
                                  моих персональных данных в
                                  соответствии с{' '}
                                  <a
                                    href="/privacy-policy"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 underline"
                                  >
                                    Политикой
                                    конфиденциальности
                                  </a>
                                  .
                                </span>
                              </label>
                              <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={
                                    consents.dataProcessing
                                  }
                                  onChange={() =>
                                    handleConsentChange(
                                      'dataProcessing',
                                    )
                                  }
                                  className="mt-1 w-5 h-5"
                                />
                                <span className="text-sm text-gray-700">
                                  Я согласен на обработку
                                  данных для поиска лекарств
                                  и проведения
                                  онлайн-консультаций.
                                </span>
                              </label>
                              <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={
                                    consents.securityProtection
                                  }
                                  onChange={() =>
                                    handleConsentChange(
                                      'securityProtection',
                                    )
                                  }
                                  className="mt-1 w-5 h-5"
                                />
                                <span className="text-sm text-gray-700">
                                  Я подтверждаю, что
                                  ознакомлен с мерами защиты
                                  данных в соответствии с
                                  ОАЦ РБ (класс ИС 3-ин).
                                </span>
                              </label>
                            </div>
                          </div>

                          <div className="flex items-center justify-end gap-3">
                            <button
                              onClick={
                                handleSavePreferences
                              }
                              disabled={
                                !areAllConsentsReady
                              }
                              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                                areAllConsentsReady
                                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow hover:from-blue-600 hover:to-purple-700'
                                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                              }`}
                            >
                              Сохранить мой выбор
                            </button>
                            <button
                              onClick={handleCloseExpanded}
                              className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
                            >
                              Отменить
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
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

              {/* ChatWidgetOrLink скрыт при активном баннере согласий */}
              {!showCookieBanner && <ChatWidgetOrLink />}

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
