// src/api/client.js
import axios from "axios";
import { NORMALIZED_API_BASE } from "./config";
import { logger } from "../utils/logger";

export const api = axios.create({
  baseURL: NORMALIZED_API_BASE,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor — добавляем API key и Authorization token если есть
api.interceptors.request.use(
  (config) => {
    // Добавляем API key если есть
    const apiKey = import.meta.env.VITE_API_KEY;
    if (apiKey) {
      config.headers["X-API-KEY"] = apiKey;
    }
    
    // Добавляем session token для фармацевта если есть в localStorage
    const pharmacistToken = localStorage.getItem('pharmacist_session_token');
    if (pharmacistToken && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${pharmacistToken}`;
    }
    
    // Log outgoing requests for debugging
    logger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
      baseURL: config.baseURL,
      headers: Object.keys(config.headers || {}).reduce((acc, key) => {
        // Don't log sensitive headers
        if (key.toLowerCase() === 'authorization') {
          acc[key] = '[REDACTED]';
        } else {
          acc[key] = config.headers[key];
        }
        return acc;
      }, {}),
      data: config.data,
    });
    
    return config;
  },
  (error) => {
    logger.error('API Request Error:', error);
    return Promise.reject(error);
  },
);

// Response interceptor — форматируем ошибки
const ERROR_MESSAGES = {
  400: "Неверный запрос. Проверьте введённые данные.",
  401: "Требуется авторизация.",
  403: "Доступ запрещён.",
  404: "Ресурс не найден.",
  413: "Файл слишком большой.",
  429: "Слишком много запросов. Подождите немного.",
  500: "Ошибка сервера. Попробуйте позже.",
  502: "Сервер временно недоступен.",
  503: "Сервер временно недоступен. Попробуйте позже.",
};

function getErrorMessage(error) {
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    // Берём сообщение от сервера если есть
    const serverMsg = data?.detail || data?.message;
    return serverMsg || ERROR_MESSAGES[status] || `Ошибка ${status}`;
  }
  if (error.request) {
    return "Нет соединения с сервером. Проверьте интернет.";
  }
  return error.message || "Неизвестная ошибка";
}

api.interceptors.response.use(
  (response) => {
    // Log successful responses for debugging
    logger.debug(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`, {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  (error) => {
    const message = getErrorMessage(error);
    logger.error(
      `API Error [${error.response?.status || "network"}]: ${message}`,
      {
        url: error.config?.url,
        method: error.config?.method,
        baseURL: error.config?.baseURL,
        status: error.response?.status,
        responseData: error.response?.data,
        errorMessage: error.message,
      }
    );

    // Добавляем human-readable сообщение к объекту ошибки
    error.userMessage = message;
    error.isApiError = !!error.response;

    return Promise.reject(error);
  },
);

// Методы для работы с бронированиями
export const bookingApi = {
  createOrder: async (orderData) => {
    const response = await api.post("/orders", orderData);
    return response.data;
  },
};

// Экспортируем хелпер для получения сообщений ошибок
export { getErrorMessage, ERROR_MESSAGES };

// Экспортируем по умолчанию основной API клиент
export default api;