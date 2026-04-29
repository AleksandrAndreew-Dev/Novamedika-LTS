import React, { useState, useEffect } from 'react';
import { questionsService } from '../../services/questionsService';
import { useAuth } from '../../hooks/useAuth';

export default function DashboardStats() {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    newQuestions: 0,
    inProgress: 0,
    completedToday: 0,
    avgResponseTime: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Enhanced debugging - log component mount and user data
  useEffect(() => {
    console.log('[DashboardStats] Component mounted with user:', {
      hasUser: !!user,
      userStructure: user ? {
        uuid: user.uuid,
        hasUserField: !!user.user,
        firstName: user.user?.first_name || user.name,
        telegramId: user.user?.telegram_id || user.telegram_id,
        pharmacyInfo: user.pharmacy_info?.name
      } : null
    });
    
    loadStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadStats = async () => {
    try {
      console.log('[DashboardStats] Loading stats...');
      const data = await questionsService.getDashboardStats();
      console.log('[DashboardStats] Stats loaded successfully:', data);
      setStats(data);
      setError(null);
    } catch (error) {
      console.error('[DashboardStats] Failed to load stats:', error);
      console.error('[DashboardStats] Error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message,
        url: error.config?.url,
        baseURL: error.config?.baseURL
      });
      
      // Set user-friendly error message
      if (error.response?.status === 401) {
        setError('Сессия истекла. Пожалуйста, обновите страницу.');
      } else if (error.response?.status === 403) {
        setError('Ошибка доступа к статистике. Обратитесь к администратору.');
      } else if (error.response?.status >= 500) {
        setError('Ошибка сервера. Статистика временно недоступна.');
      } else if (error.request && !error.response) {
        setError('Нет соединения с сервером. Проверьте интернет.');
      } else {
        setError('Не удалось загрузить статистику. Попробуйте позже.');
      }
      
      // Set default stats even on error
      setStats({
        newQuestions: 0,
        inProgress: 0,
        completedToday: 0,
        avgResponseTime: 0
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-8 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  // If there's an error but we have basic stats, show them with error message
  const statCards = [
    {
      title: 'Новых вопросов',
      value: stats.newQuestions ?? 0,
      color: 'bg-blue-500',
      icon: '📩'
    },
    {
      title: 'В работе',
      value: stats.inProgress ?? 0,
      color: 'bg-yellow-500',
      icon: '🔄'
    },
    {
      title: 'Завершено сегодня',
      value: stats.completedToday ?? 0,
      color: 'bg-green-500',
      icon: '✅'
    },
    {
      title: 'Среднее время ответа',
      value: `${stats.avgResponseTime ?? 0} мин`,
      color: 'bg-purple-500',
      icon: '⏱️'
    }
  ];

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{card.title}</p>
                <p className="text-2xl font-bold mt-1">{card.value}</p>
              </div>
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${card.color} text-white text-xl`}>
                {card.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Basic pharmacist info as fallback */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Информация о фармацевте</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Имя</p>
            <p className="font-medium">{user?.user?.first_name || user?.name || 'Не указано'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Telegram ID</p>
            <p className="font-medium">{user?.user?.telegram_id || user?.telegram_id || 'Не указано'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Статус</p>
            <p className="font-medium">
              {user?.is_active ? 'Активен' : 'Не активен'}
              {user?.is_online && ' • Онлайн'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Аптека</p>
            <p className="font-medium">{user?.pharmacy_info?.name || 'Не указана'}</p>
          </div>
        </div>
      </div>

      {/* Retry button */}
      <div className="flex justify-center">
        <button
          onClick={loadStats}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Обновить данные
        </button>
      </div>
    </div>
  );
}