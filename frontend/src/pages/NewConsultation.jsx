import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import userAuthService from '../services/userAuthService';
import telegramAuthService from '../services/telegramAuthService';
import Toast from '../components/Toast';

export default function NewConsultation() {
  const navigate = useNavigate();
  const [questionText, setQuestionText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const createdRef = useRef(false);

  const getAnonUserId = () => {
    let anonId = localStorage.getItem('anon_user_id');
    if (!anonId) {
      anonId = crypto.randomUUID();
      localStorage.setItem('anon_user_id', anonId);
    }
    return anonId;
  };

  const autoCreateChat = async () => {
    if (createdRef.current) return;
    createdRef.current = true;

    try {
      setLoading(true);

      if (telegramAuthService.canAuthViaWebApp()) {
        console.log(
          '[NewConsultation] Attempting Telegram auto-login',
        );
        const success =
          await telegramAuthService.autoLogin();
        if (success) {
          console.log(
            '[NewConsultation] Telegram auto-login successful',
          );
        } else {
          console.log(
            '[NewConsultation] Telegram auto-login failed',
          );
        }
      }

      if (userAuthService.isAuthenticated()) {
        console.log(
          '[NewConsultation] Creating consultation via JWT',
        );
        try {
          const jwtResponse = await api.post(
            '/api/consultations/',
            {
              text: questionText.trim() || 'Новый вопрос',
              category: 'general',
            },
            {
              headers: {
                'X-API-KEY':
                  window.APP_CONFIG?.API_KEY ||
                  import.meta.env?.VITE_API_KEY ||
                  '',
              },
            },
          );
          console.log(
            '[NewConsultation] Consultation created:',
            jwtResponse.data.uuid,
          );
          navigate(`/chat/${jwtResponse.data.uuid}`, {
            replace: true,
            state: { from: '/' },
          });
          return;
        } catch (jwtErr) {
          console.warn(
            '[NewConsultation] JWT consultation failed, falling back to public:',
            jwtErr.response?.status,
          );
        }
      }

      console.log(
        '[NewConsultation] Creating public question (anonymous)',
      );
      const anonResponse = await api.post(
        '/api/public/questions/',
        {
          text: questionText.trim() || 'Новый вопрос',
          category: 'general',
          anon_user_id: getAnonUserId(),
        },
        {
          headers: {
            'X-API-KEY':
              window.APP_CONFIG?.API_KEY ||
              import.meta.env?.VITE_API_KEY ||
              '',
          },
        },
      );
      console.log(
        '[NewConsultation] Public question created:',
        anonResponse.data.uuid,
      );
      // Force anonymous mode in Chat by passing ?anon=1
      navigate(`/chat/${anonResponse.data.uuid}?anon=1`, {
        replace: true,
        state: { from: '/' },
      });
    } catch (err) {
      console.error(
        '[NewConsultation] Failed to create consultation:',
        err,
      );
      setError(
        err.response?.data?.detail ||
          err.userMessage ||
          'Не удалось создать чат. Попробуйте ещё раз.',
      );
      setToast({
        message:
          'Не удалось создать чат. Проверьте подключение и попробуйте снова.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    if (!questionText.trim()) {
      setToast({
        message: 'Пожалуйста, введите ваш вопрос',
        type: 'error',
      });
      return;
    }
    createdRef.current = false;
    autoCreateChat();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      {loading ? (
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            Открываем чат с фармацевтом...
          </p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4 text-center">
          <div className="text-red-500 mb-4">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Ошибка
          </h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium py-3 px-6 rounded-lg transition-all"
          >
            Попробовать снова
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Новый вопрос фармацевту
          </h2>
          <textarea
            value={questionText}
            onChange={(e) =>
              setQuestionText(e.target.value)
            }
            placeholder="Опишите ваш вопрос..."
            rows={4}
            className="w-full border border-gray-300 rounded-lg p-3 mb-4 resize-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
          />
          <button
            onClick={handleCreate}
            disabled={!questionText.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-medium py-3 px-6 rounded-lg transition-colors"
          >
            Создать чат
          </button>
        </div>
      )}

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
