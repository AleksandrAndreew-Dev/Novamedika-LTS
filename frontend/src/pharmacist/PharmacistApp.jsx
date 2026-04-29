import React, { useEffect, useState, useRef } from 'react';
import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import { AuthProvider } from './components/auth/AuthProvider';
import { useAuth } from './hooks/useAuth';
import Dashboard from './pharmacist/pages/Dashboard';
import Login from './pharmacist/components/auth/Login';
import ProtectedRoute from './pharmacist/components/auth/ProtectedRoute';
import { logger } from './utils/logger';
import { telegramWebApp } from '../utils/telegramWebApp';

// Component to handle URL token authentication (Legacy)
function TokenAuthHandler() {
  const [searchParams] = useSearchParams();
  const { loginWithToken, isAuthenticated } = useAuth();
  const [authError, setAuthError] = useState(null);
  const loginInProgressRef = useRef(false);

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token && !isAuthenticated && !loginInProgressRef.current) {
      loginInProgressRef.current = true;
      
      logger.info('Found legacy token in URL, attempting auto-login');
      
      loginWithToken(token)
        .then(() => {
          logger.info('Legacy auto-login successful');
          window.history.replaceState({}, document.title, window.location.pathname);
          setAuthError(null);
        })
        .catch((err) => {
          logger.error('Legacy auto-login failed:', err);
          let errorMessage = 'Ошибка аутентификации по ссылке. ';
          
          if (err.response?.status === 401) {
            errorMessage += 'Ссылка недействительна или истекла.';
          } else {
            errorMessage += err.userMessage || 'Попробуйте войти через Telegram.';
          }
          
          setAuthError(errorMessage);
        })
        .finally(() => {
          loginInProgressRef.current = false;
        });
    }
  }, [searchParams, loginWithToken, isAuthenticated]);

  if (authError) {
    return (
      <div className="min-h-screen bg-telegram-bg flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка входа</h2>
          <p className="text-gray-600 text-sm mb-6">{authError}</p>
          <button
            onClick={() => window.location.href = '/'}
            className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 min-h-[44px]"
          >
            На главную
          </button>
        </div>
      </div>
    );
  }

  return null;
}

export default function PharmacistApp() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <TokenAuthHandler />
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}