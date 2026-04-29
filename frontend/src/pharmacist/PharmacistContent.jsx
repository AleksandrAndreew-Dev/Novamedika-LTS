import React, { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth.js';
import DashboardStats from './components/dashboard/DashboardStats';
import QuestionsList from './components/consultations/QuestionsList';
import Sidebar from './components/layout/Sidebar';
import MainLayout from './components/layout/MainLayout';

// Simple Error Boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error: error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[PharmacistContent] ErrorBoundary caught error:', error);
    console.error('[PharmacistContent] Error info:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <svg className="h-8 w-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ошибка загрузки панели</h3>
            <p className="text-gray-600 mb-4">
              Не удалось загрузить статистику. Панель фармацевта доступна, но некоторые данные временно недоступны.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
            >
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Перезагрузить панель
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default function PharmacistContent() {
  const { isAuthenticated, user, loading, loginWithToken, error } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [tokenProcessed, setTokenProcessed] = useState(false);
  const [tokenProcessingError, setTokenProcessingError] = useState(null);

  // Проверяем наличие токена в URL при загрузке
  useEffect(() => {
    const processUrlToken = async () => {
      if (tokenProcessed || isAuthenticated) {
        console.log('[PharmacistContent] Skipping token processing - already processed or authenticated');
        return;
      }

      // Получаем токен из URL параметров
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');

      console.log('[PharmacistContent] Checking for token in URL...');
      console.log('[PharmacistContent] Token found:', !!token);
      console.log('[PharmacistContent] isAuthenticated:', isAuthenticated);
      console.log('[PharmacistContent] tokenProcessed:', tokenProcessed);

      if (token) {
        try {
          console.log('[PharmacistContent] Found JWT token in URL, attempting to login...');
          console.log('[PharmacistContent] Token length:', token.length);

          await loginWithToken(token);

          // Удаляем токен из URL для безопасности
          window.history.replaceState({}, document.title, window.location.pathname);
          setTokenProcessed(true);
          setTokenProcessingError(null);
          console.log('[PharmacistContent] ✅ Token login successful, URL cleaned');
        } catch (error) {
          console.error('[PharmacistContent] ❌ Failed to login with token from URL:', error);
          console.error('[PharmacistContent] Error response:', error.response?.status, error.response?.data);
          console.error('[PharmacistContent] Error message:', error.message);
          
          // Set specific error for token processing failure
          const errorMessage = error.userMessage || error.response?.data?.detail || 'Ошибка аутентификации. Токен недействителен или фармацевт не найден.';
          setTokenProcessingError(errorMessage);
          setTokenProcessed(true);
        }
      } else {
        console.log('[PharmacistContent] No token in URL, checking localStorage...');
        const storedToken = localStorage.getItem('pharmacist_access_token');
        if (storedToken) {
          console.log('[PharmacistContent] ✅ Found token in localStorage (length:', storedToken.length + ')');
          console.log('[PharmacistContent] useAuth hook will handle auto-login');
        } else {
          console.log('[PharmacistContent] ⚠️ No token found in localStorage either');
        }
        setTokenProcessed(true);
        setTokenProcessingError(null);
      }
    };

    processUrlToken();
  }, [isAuthenticated, loginWithToken, tokenProcessed]);

  // Determine the actual error to display
  const displayError = tokenProcessingError || error;

  // Если есть ошибка аутентификации - показываем сообщение об ошибке
  if (!loading && displayError && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full border-l-4 border-red-500">
          <div className="text-center mb-6">
            <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <svg
                className="h-8 w-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Ошибка аутентификации
            </h2>
            <p className="text-gray-600 text-sm mb-4">
              {displayError}
            </p>
          </div>

          <div className="space-y-3">
            <button
              onClick={() => {
                // Try to reload and reprocess token
                window.location.reload();
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              <svg
                className="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Повторить попытку
            </button>
            
            <button
              onClick={() => {
                // Close WebApp and go back to Telegram
                if (window.Telegram?.WebApp) {
                  window.Telegram.WebApp.close();
                } else {
                  window.location.href = '/';
                }
              }}
              className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              <svg
                className="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                />
              </svg>
              Вернуться в Telegram
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Если не авторизован и токен обработан - показываем страницу входа
  if (!loading && !isAuthenticated && tokenProcessed) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
          <div className="text-center mb-6">
            <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
              <svg
                className="h-8 w-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Вход для фармацевтов</h2>
          </div>

          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-800 mb-3">
                <strong>✅ Автоматический вход через Telegram</strong>
              </p>
              <ol className="text-sm text-green-700 space-y-2 list-decimal list-inside">
                <li>Откройте бота NovaMedika в Telegram</li>
                <li>Нажмите кнопку "💼 Панель фармацевта"</li>
                <li>WebApp откроется автоматически с вашим токеном</li>
              </ol>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800 mb-2">
                <strong>Если автоматический вход не сработал:</strong>
              </p>
              <p className="text-xs text-blue-700">
                Попробуйте перезагрузить страницу или нажмите кнопку ниже, чтобы закрыть WebApp и попробовать снова.
              </p>
            </div>

            <button
              onClick={() => window.Telegram?.WebApp?.close()}
              className="w-full bg-gray-200 text-gray-700 py-3 rounded-lg hover:bg-gray-300 transition mt-4"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show basic loading state
  if (loading || !tokenProcessed) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // If authenticated, show the dashboard even if verification is pending
  // The DashboardStats component now handles its own errors gracefully
  return (
    <MainLayout>
      <div className="flex h-screen bg-gray-50">
        {/* Sidebar */}
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Main Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-6">
            {activeTab === 'dashboard' && (
              <ErrorBoundary>
                <DashboardStats />
              </ErrorBoundary>
            )}
            {activeTab === 'questions' && <QuestionsList />}
            {activeTab === 'profile' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-4">Профиль фармацевта</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Имя</label>
                    <p className="mt-1 text-lg">{user?.user?.first_name || user?.name || 'Не указано'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Telegram ID</label>
                    <p className="mt-1 text-lg">{user?.user?.telegram_id || user?.telegram_id || 'Не указано'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Статус</label>
                    <p className="mt-1 text-lg">
                      {user?.is_active ? 'Активен' : 'Не активен'}
                      {user?.is_online && ' • Онлайн'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Аптека</label>
                    <p className="mt-1 text-lg">{user?.pharmacy_info?.name || 'Не указана'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}