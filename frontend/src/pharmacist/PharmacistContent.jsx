import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import DashboardStats from './components/dashboard/DashboardStats';
import QuestionsList from './components/consultations/QuestionsList';
import ConsultationChat from './components/consultations/ConsultationChat';
import MainLayout from './components/layout/MainLayout';

export default function PharmacistContent() {
  const { isAuthenticated, user, loading } = useAuth();

  // Enhanced debugging - log auth state changes
  React.useEffect(() => {
    console.log('[PharmacistContent] Auth state changed:', {
      isAuthenticated,
      loading,
      user: user ? {
        uuid: user.uuid,
        hasUserField: !!user.user,
        firstName: user.user?.first_name || user.name,
        telegramId: user.user?.telegram_id || user.telegram_id,
        isActive: user.is_active,
        pharmacyInfo: user.pharmacy_info?.name
      } : null
    });
  }, [isAuthenticated, loading, user]);

  // If not authenticated and not loading, this shouldn't be reached due to ProtectedRoute
  // but we add a fallback just in case
  if (!loading && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Требуется авторизация. Перенаправление...</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка панели...</p>
        </div>
      </div>
    );
  }

  // Additional safety check - ensure user object exists before rendering
  if (!user) {
    console.error('[PharmacistContent] User object is null/undefined after loading!');
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
            <svg className="h-8 w-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-gray-600">Ошибка загрузки данных пользователя</p>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Обновить страницу
          </button>
        </div>
      </div>
    );
  }

  return (
    <MainLayout>
      {/* Main Content with Routing */}
      <div className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={
            <div className="p-6">
              <DashboardStats />
              <QuestionsList />
              <div className="bg-white rounded-lg shadow p-6 mt-6">
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
            </div>
          } />
          <Route path="/questions/:questionId" element={<ConsultationChat />} />
        </Routes>
      </div>
    </MainLayout>
  );
}