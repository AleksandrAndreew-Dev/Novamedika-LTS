import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import { AuthProvider } from './components/auth/AuthProvider';
import { useAuth } from './hooks/useAuth';
import Dashboard from './pharmacist/pages/Dashboard';
import Login from './pharmacist/components/auth/Login';
import ProtectedRoute from './pharmacist/components/auth/ProtectedRoute';
import { logger } from './utils/logger';

// Component to handle URL token authentication
function TokenAuthHandler() {
  const [searchParams] = useSearchParams();
  const { loginWithToken, isAuthenticated } = useAuth();
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    const token = searchParams.get('token');
    
    console.log('[TokenAuthHandler] Checking for token in URL...');
    console.log('[TokenAuthHandler] Token found:', !!token);
    console.log('[TokenAuthHandler] Already authenticated:', isAuthenticated);
    
    if (token && !isAuthenticated) {
      logger.info('Found token in URL, attempting auto-login');
      
      // Attempt to login with the token from URL
      loginWithToken(token)
        .then(() => {
          logger.info('Auto-login successful');
          // Clear the token from URL by navigating to root
          window.history.replaceState({}, document.title, window.location.pathname);
          setAuthError(null);
        })
        .catch((err) => {
          logger.error('Auto-login failed:', err);
          console.error('[TokenAuthHandler] Error details:', {
            status: err.response?.status,
            data: err.response?.data,
            message: err.message
          });
          
          // Determine specific error type for better user feedback
          let errorMessage = 'Ошибка аутентификации. ';
          
          if (err.response?.status === 401) {
            if (err.response?.data?.detail?.includes('expired')) {
              errorMessage += 'Срок действия ссылки истёк. Пожалуйста, откройте панель заново из Telegram.';
            } else if (err.response?.data?.detail?.includes('not found') || err.response?.data?.detail?.includes('Фармацевт не найден')) {
              errorMessage += 'Фармацевт не найден в системе. Обратитесь к администратору.';
            } else {
              errorMessage += 'Ссылка недействительна или фармацевт не найден. Пожалуйста, откройте панель заново из Telegram.';
            }
          } else if (err.response?.status === 0) {
            errorMessage += 'Ошибка сети. Проверьте подключение к интернету и попробуйте снова.';
          } else {
            errorMessage += (err.userMessage || err.response?.data?.detail || 'Попробуйте открыть панель заново из Telegram.');
          }
          
          setAuthError(errorMessage);
          
          // Don't redirect immediately - let the user see the error and decide
          // They can click "На главную" or refresh to get a new token from Telegram
        });
    } else if (!token && !isAuthenticated) {
      console.log('[TokenAuthHandler] No token in URL and not authenticated - waiting for manual login or token');
    }
  }, [searchParams, loginWithToken, isAuthenticated]);

  // If we have an auth error, show it to the user
  if (authError) {
    return (
      <div className="min-h-screen bg-telegram-bg flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Ошибка аутентификации
          </h2>
          <p className="text-gray-600 text-sm mb-6">
            {authError}
          </p>
          <div className="flex flex-col gap-3">
            <button
              onClick={() => window.location.reload()}
              className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 min-h-[44px]"
            >
              Обновить страницу
            </button>
            <button
              onClick={() => {
                // Redirect to main Telegram bot
                window.open('https://t.me/novamedika_bot', '_blank');
              }}
              className="bg-gray-100 text-gray-800 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-gray-200 min-h-[44px]"
            >
              Открыть Telegram бота
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null; // This component doesn't render anything when no error
}

export default function PharmacistApp() {
  return (
    <AuthProvider>
      <TokenAuthHandler />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}