import React, { useState, useEffect, useCallback } from 'react';
import { questionsService } from '../../services/questionsService';

export default function QuestionsList() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, new, in_progress, completed

  const loadQuestions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await questionsService.getQuestions(filter);
      setQuestions(data);
    } catch (error) {
      console.error('Failed to load questions:', error);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const getStatusBadge = (status) => {
    const badges = {
      new: { text: 'Новый', color: 'bg-blue-100 text-blue-800' },
      in_progress: { text: 'В работе', color: 'bg-yellow-100 text-yellow-800' },
      completed: { text: 'Завершен', color: 'bg-green-100 text-green-800' }
    };
    const badge = badges[status] || badges.new;
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-800">Консультации</h2>
        
        <div className="flex space-x-2">
          {['all', 'new', 'in_progress', 'completed'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filter === f
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {f === 'all' && 'Все'}
              {f === 'new' && 'Новые'}
              {f === 'in_progress' && 'В работе'}
              {f === 'completed' && 'Завершенные'}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {questions.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">Нет консультаций</p>
          </div>
        ) : (
          questions.map((question) => (
            <div key={question.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    {question.title || 'Без названия'}
                  </h3>
                  <p className="text-gray-600 text-sm mb-2">{question.question}</p>
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <span>📅 {new Date(question.created_at).toLocaleDateString('ru-RU')}</span>
                    <span>👤 Пользователь #{question.user_id}</span>
                  </div>
                </div>
                <div className="ml-4">
                  {getStatusBadge(question.status)}
                </div>
              </div>
              
              {question.answer && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600">
                    <strong>Ответ:</strong> {question.answer}
                  </p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
