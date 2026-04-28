import React, { useState, useEffect } from 'react';
import { questionsService } from '../../services/questionsService';

export default function DashboardStats() {
  const [stats, setStats] = useState({
    newQuestions: 0,
    inProgress: 0,
    completedToday: 0,
    avgResponseTime: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await questionsService.getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
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

  const statCards = [
    {
      title: 'Новых вопросов',
      value: stats.newQuestions,
      color: 'bg-blue-500',
      icon: '📩'
    },
    {
      title: 'В работе',
      value: stats.inProgress,
      color: 'bg-yellow-500',
      icon: '⏳'
    },
    {
      title: 'Завершено сегодня',
      value: stats.completedToday,
      color: 'bg-green-500',
      icon: '✅'
    },
    {
      title: 'Среднее время ответа',
      value: `${stats.avgResponseTime} мин`,
      color: 'bg-purple-500',
      icon: '⚡'
    }
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Дашборд</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                <p className="text-3xl font-bold text-gray-800">{stat.value}</p>
              </div>
              <div className={`${stat.color} text-white rounded-full p-3 text-2xl`}>
                {stat.icon}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
