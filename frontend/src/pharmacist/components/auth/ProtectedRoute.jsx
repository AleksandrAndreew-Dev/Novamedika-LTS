import React from "react";
import { useAuth } from "../../hooks/useAuth";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading, error, checkAuth } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка...</p>
        </div>
      </div>
    );
  }

  // Show auth error with retry button instead of redirect to login
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-yellow-600"
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
            Требуется авторизация
          </h2>
          <p className="text-gray-600 text-sm mb-6">
            {error ||
              'Нажмите кнопку "Панель фармацевта" в Telegram боте для входа.'}
          </p>
          <button
            onClick={() => {
              window.location.reload();
            }}
            className="bg-blue-600 text-white font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-700 min-h-[44px]"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  // Render protected content
  return children;
}
