import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import userAuthService from '../services/userAuthService';
import telegramAuthService from '../services/telegramAuthService';
import Toast from '../components/Toast';

export default function NewConsultation() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    text: '',
    category: 'general',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Try Telegram auto-login if in WebApp
        if (telegramAuthService.canAuthViaWebApp()) {
          console.log('[NewConsultation] Attempting Telegram auto-login');
          const success = await telegramAuthService.autoLogin();

          if (success) {
            console.log('[NewConsultation] ✅ Telegram auto-login successful');
            setAuthChecking(false);
            return;
          }
        }

        // Check if already authenticated
        if (userAuthService.isAuthenticated()) {
          console.log('[NewConsultation] User already authenticated');
          setAuthChecking(false);
          return;
        }

        // Not authenticated and can't do Telegram login
        console.log('[NewConsultation] Not authenticated, redirecting to login');
        navigate('/login');
      } catch (err) {
        console.error('[NewConsultation] Auth check error:', err);
        navigate('/login');
      }
    };

    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (authChecking) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка...</p>
        </div>
      </div>
    );
  }

  const categories = [
    { value: 'general', label: 'Общий вопрос' },
    { value: 'medication', label: 'Лекарства' },
    { value: 'symptoms', label: 'Симптомы' },
    { value: 'prescription', label: 'Рецепты' },
    { value: 'side_effects', label: 'Побочные эффекты' },
    { value: 'other', label: 'Другое' },
  ];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.text.trim()) {
      setError('Пожалуйста, опишите ваш вопрос');
      return;
    }

    try {
      setLoading(true);

      // Create consultation (authentication already checked in useEffect)
      const response = await api.post('/api/consultations/', {
        text: formData.text.trim(),
        category: formData.category,
      });

      setToast({ message: 'Консультация создана!', type: 'success' });

      // Redirect to chat
      setTimeout(() => {
        navigate(`/chat/${response.data.uuid}`);
      }, 1000);
    } catch (err) {
      console.error('Failed to create consultation:', err);
      const errorMessage = err.userMessage || 'Ошибка создания консультации. Попробуйте позже.';
      setError(errorMessage);
      setToast({ message: errorMessage, type: 'error' });
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-gray-600 hover:text-gray-900"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-900">Новая консультация</h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Info Box */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm text-blue-900">
                  Опишите ваш вопрос максимально подробно. Фармацевт ответит вам в ближайшее время.
                </p>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Category Selection */}
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                Категория вопроса
              </label>
              <select
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Question Text */}
            <div>
              <label htmlFor="text" className="block text-sm font-medium text-gray-700 mb-2">
                Ваш вопрос <span className="text-red-500">*</span>
              </label>
              <textarea
                id="text"
                name="text"
                value={formData.text}
                onChange={handleChange}
                rows={8}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="Опишите ваш вопрос подробно..."
                required
                disabled={loading}
              />
              <p className="mt-2 text-sm text-gray-500">
                Минимум 10 символов
              </p>
            </div>

            {/* Submit Button */}
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                disabled={loading}
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={loading || !formData.text.trim()}
                className={`flex-1 font-medium py-3 px-6 rounded-lg transition-all ${
                  loading || !formData.text.trim()
                    ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                    : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg hover:shadow-xl'
                }`}
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Создание...
                  </span>
                ) : (
                  'Отправить вопрос'
                )}
              </button>
            </div>
          </form>
        </div>
      </main>

      {/* Toast Notifications */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
          duration={toast.type === 'error' ? 5000 : 3000}
        />
      )}
    </div>
  );
}
