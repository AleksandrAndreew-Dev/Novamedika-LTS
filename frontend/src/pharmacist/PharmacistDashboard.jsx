import React, { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import DashboardStats from './components/dashboard/DashboardStats';
import QuestionsList from './components/consultations/QuestionsList';
import Sidebar from './components/layout/Sidebar';
import MainLayout from './components/layout/MainLayout';

export default function PharmacistDashboard() {
  const { isAuthenticated, user, loading, loginWithToken } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [tokenProcessed, setTokenProcessed] = useState(false);

  // Проверяем наличие токена в URL при загрузке
  useEffect(() => {
    const processUrlToken = async () => {
      if (tokenProcessed || isAuthenticated) {
        console.log('[PharmacistDashboard] Skipping token processing - already processed or authenticated');
        return;
      }

      // Получаем токен из URL параметров
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');

      console.log('[PharmacistDashboard] Checking for token in URL...');
      console.log('[PharmacistDashboard] Token found:', !!token);
      console.log('[PharmacistDashboard] isAuthenticated:', isAuthenticated);
      console.log('[PharmacistDashboard] tokenProcessed:', tokenProcessed);

      if (token) {
        try {
          console.log('[PharmacistDashboard] Found JWT token in URL, attempting to login...');
          console.log('[PharmacistDashboard] Token length:', token.length);

          await loginWithToken(token);

          // Удаляем токен из URL для безопасности
          window.history.replaceState({}, document.title, window.location.pathname);
          setTokenProcessed(true);
          console.log('[PharmacistDashboard] ✅ Token login successful, URL cleaned');
        } catch (error) {
          console.error('[PharmacistDashboard] ❌ Failed to login with token from URL:', error);
          console.error('[PharmacistDashboard] Error response:', error.response?.status, error.response?.data);
          console.error('[PharmacistDashboard] Error message:', error.message);
          setTokenProcessed(true);
        }
      } else {
        console.log('[PharmacistDashboard] No token in URL, checking localStorage...');
        const storedToken = localStorage.getItem('pharmacist_access_token');
        if (storedToken) {
          console.log('[PharmacistDashboard] ✅ Found token in localStorage (length:', storedToken.length + ')');
          console.log('[PharmacistDashboard] useAuth hook will handle auto-login');
        } else {
          console.log('[PharmacistDashboard] ⚠️ No token found in localStorage either');
        }
        setTokenProcessed(true);
      }
    };

    processUrlToken();
  }, [isAuthenticated, loginWithToken, tokenProcessed]);

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

  if (loading || !tokenProcessed) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <MainLayout>
      <div className="flex h-screen bg-gray-50">
        {/* Sidebar */}
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Main Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-6">
            {activeTab === 'dashboard' && <DashboardStats />}
            {activeTab === 'questions' && <QuestionsList />}
            {activeTab === 'profile' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-4">Профиль фармацевта</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Имя</label>
                    <p className="mt-1 text-lg">{user?.name || 'Не указано'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Telegram ID</label>
                    <p className="mt-1 text-lg">{user?.telegram_id || 'Не указано'}</p>
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
