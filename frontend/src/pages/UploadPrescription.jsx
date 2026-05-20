import React, { useState, useEffect } from 'react';
import axios from 'axios';

const UploadPrescription = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [token, setToken] = useState(null);

  // Получаем JWT токен из localStorage или URL params
  useEffect(() => {
    // Проверяем URL параметры (если пользователь перешел по ссылке)
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    
    if (urlToken) {
      setToken(urlToken);
      localStorage.setItem('jwt_token', urlToken);
    } else {
      // Проверяем localStorage
      const storedToken = localStorage.getItem('jwt_token');
      if (storedToken) {
        setToken(storedToken);
      } else {
        // Перенаправляем на страницу входа
        window.location.href = '/login?redirect=/prescriptions/upload';
      }
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    if (!selectedFile) {
      return;
    }
    
    // Проверка типа файла
    if (!selectedFile.type.startsWith('image/')) {
      setError('Пожалуйста, выберите изображение (JPEG, PNG)');
      return;
    }
    
    // Проверка размера (макс 10 MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('Файл слишком большой. Максимальный размер: 10 MB');
      return;
    }
    
    setFile(selectedFile);
    setError('');
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Пожалуйста, выберите файл');
      return;
    }

    if (!token) {
      setError('Необходима авторизация');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        '/api/prescriptions/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      setSuccess(true);
      
      // Показываем сообщение об успехе
      setTimeout(() => {
        window.location.href = '/prescriptions/history';
      }, 3000);

    } catch (err) {
      console.error('[UploadPrescription] Upload error:', err);
      const errorMessage = err.response?.data?.detail || 'Ошибка при загрузке. Попробуйте позже.';
      setError(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-4">✅</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Рецепт успешно загружен!
          </h2>
          <p className="text-gray-600 mb-6">
            Фармацевт получит уведомление и ответит вам в ближайшее время.
          </p>
          <p className="text-sm text-gray-500">
            Перенаправление в историю рецептов...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">📸</div>
          <h1 className="text-xl font-bold text-gray-800">
            Загрузка рецепта
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Безопасная загрузка на серверы Республики Беларусь
          </p>
        </div>

        {/* Security Info */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-3 mb-5 rounded text-sm">
          <h3 className="font-semibold text-blue-900 mb-2">🔒 Защита данных:</h3>
          <ul className="text-blue-800 space-y-1 text-xs">
            <li>✓ Прямая загрузка на серверы РБ (не через Telegram)</li>
            <li>✓ Шифрование AES-256</li>
            <li>✓ Автоудаление через 48 часов</li>
            <li>✓ Доступ только у фармацевтов</li>
            <li>✓ Просмотр только в режиме «глазок» (без скачивания)</li>
          </ul>
        </div>

        {/* File Selection */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Выберите фото рецепта
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
          {file && (
            <p className="mt-2 text-xs text-gray-600">
              Выбран: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-3 mb-5 rounded">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-colors text-sm ${
            !file || uploading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {uploading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Загрузка...
            </span>
          ) : (
            '📤 Загрузить рецепт'
          )}
        </button>

        {/* Note */}
        <p className="mt-3 text-xs text-gray-500 text-center">
          Поддерживаемые форматы: JPEG, PNG. Максимальный размер: 10 MB
        </p>

        {/* Link to history */}
        <div className="mt-4 text-center">
          <a href="/prescriptions/history" className="text-sm text-blue-600 hover:text-blue-800">
            📋 История рецептов →
          </a>
        </div>
      </div>
    </div>
  );
};

export default UploadPrescription;
