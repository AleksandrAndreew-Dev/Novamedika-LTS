import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import DashboardStats from './components/dashboard/DashboardStats';
import QuestionsList from './components/consultations/QuestionsList';
import Sidebar from './components/layout/Sidebar';
import MainLayout from './components/layout/MainLayout';

export default function PharmacistContent() {
  const { isAuthenticated, user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

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