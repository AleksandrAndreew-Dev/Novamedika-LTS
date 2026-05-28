import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { logger } from '../../../utils/logger';

export default function LoginForm() {
  const [telegramId, setTelegramId] = useState('');
  const [consents, setConsents] = useState({
    privacyPolicy: false,
    dataProcessing: false,
    securityProtection: false,
  });
  const { login, isLoading, error } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!telegramId) {
      return;
    }

    // Проверка всех согласий
    if (!consents.privacyPolicy || !consents.dataProcessing || !consents.securityProtection) {
      return;
    }

    try {
      await login({
        telegram_id: parseInt(telegramId),
      });
      
      logger.info('Login successful, redirecting to dashboard');
      navigate('/dashboard');
    } catch (err) {
      // Error is handled by useAuth hook
      logger.error('Login failed:', err);
    }
  };

  const handleConsentChange = (field) => {
    setConsents(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const allConsentsGiven = consents.privacyPolicy && consents.dataProcessing && consents.securityProtection;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-2xl shadow-xl">
        {/* Logo and Title */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-gray-900">NovaMedika</h2>
          <p className="mt-2 text-sm text-gray-600">
            Панель управления фармацевта
          </p>
        </div>

        {/* Login Form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* Telegram ID Field */}
            <div>
              <label
                htmlFor="telegram-id"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Telegram ID
              </label>
              <input
                id="telegram-id"
                name="telegram_id"
                type="number"
                required
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
                className="appearance-none block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="Введите ваш Telegram ID"
              />
              <p className="mt-2 text-xs text-gray-500">
                Ваш Telegram ID можно узнать у @userinfobot в Telegram
              </p>
            </div>
          </div>

          {/* Согласия на обработку персональных данных */}
          <div className="pt-4 border-t border-gray-200 space-y-3">
            <p className="text-sm font-semibold text-gray-700 mb-2">
              Согласие на обработку персональных данных *
            </p>
            
            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={consents.privacyPolicy}
                onChange={() => handleConsentChange('privacyPolicy')}
                required
                disabled={isLoading}
                className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span className="text-sm text-gray-700 leading-relaxed">
                Я согласен на обработку моих персональных данных (Telegram ID, имя, 
                фамилия, телефон) в соответствии с{" "}
                <a
                  href="/privacy-policy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline font-medium"
                >
                  Политикой конфиденциальности
                </a>
                . Срок хранения: 1 год после прекращения сотрудничества.
              </span>
            </label>

            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={consents.dataProcessing}
                onChange={() => handleConsentChange('dataProcessing')}
                required
                disabled={isLoading}
                className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span className="text-sm text-gray-700 leading-relaxed">
                Я согласен на обработку моих данных для проведения онлайн-консультаций 
                и предоставления фармацевтических услуг пользователям сервиса.
              </span>
            </label>

            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={consents.securityProtection}
                onChange={() => handleConsentChange('securityProtection')}
                required
                disabled={isLoading}
                className="mt-1 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span className="text-sm text-gray-700 leading-relaxed">
                Я подтверждаю, что ознакомлен с тем, что мои данные будут зашифрованы 
                и защищены в соответствии с требованиями ОАЦ РБ (класс ИС 3-ин).
              </span>
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !telegramId || !allConsentsGiven}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <div className="flex items-center">
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
                Вход...
              </div>
            ) : (
              'Войти'
            )}
          </button>

          {/* Help Text */}
          <div className="text-center">
            <p className="text-xs text-gray-500">
              Если у вас нет доступа, обратитесь к администратору
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
