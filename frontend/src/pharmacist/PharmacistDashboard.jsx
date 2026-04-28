import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import DashboardStats from './components/dashboard/DashboardStats';
import QuestionsList from './components/consultations/QuestionsList';
import Sidebar from './components/layout/Sidebar';
import MainLayout from './components/layout/MainLayout';

export default function PharmacistDashboard() {
  const { isAuthenticated, user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

  // Если не авторизован - показываем страницу входа
  if (!loading && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
          <h2 className="text-2xl font-bold text-center mb-6">Вход для фармацевтов</h2>
          <p className="text-gray-600 text-center mb-4">
            Для доступа к панели фармацевта необходимо авторизоваться через Telegram
          </p>
          <button
            onClick={() => window.Telegram?.WebApp?.close()}
            className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 transition"
          >
            Закрыть
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
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
