import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import userAuthService from "../services/userAuthService";
import telegramAuthService from "../services/telegramAuthService";

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  // Auto-login via Telegram WebApp if available
  useEffect(() => {
    const tryTelegramLogin = async () => {
      if (telegramAuthService.canAuthViaWebApp()) {
        setLoading(true);
        const success = await telegramAuthService.autoLogin();
        if (success) {
          navigate("/dashboard");
          return;
        }
        setLoading(false);
      } else {
        setLoading(false);
      }
    };

    tryTelegramLogin();
  }, [navigate]);

  // If already authenticated, go to dashboard
  useEffect(() => {
    if (userAuthService.isAuthenticated() && !loading) {
      navigate("/dashboard");
    }
  }, [navigate, loading]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500 text-sm">Авторизация через Telegram...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-lg p-8 max-w-sm w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">НоваМедика</h1>
          <p className="text-gray-500 mt-1 text-sm">Справочная служба аптек</p>
        </div>

        <p className="text-center text-gray-500 text-sm mb-6">
          Для входа используйте Telegram. Нажмите кнопку ниже, чтобы открыть бота.
        </p>

        <a
          href="https://t.me/Novamedika_bot"
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-2xl text-center transition-colors"
        >
          Открыть Telegram бота
        </a>

        <p className="mt-4 text-center text-xs text-gray-400">
          Бот @Novamedika_bot
        </p>
      </div>
    </div>
  );
}
