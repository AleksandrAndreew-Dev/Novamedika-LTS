// src/api/client.js
import axios from 'axios';
import { NORMALIZED_API_BASE } from './config';

export const api = axios.create({
  baseURL: NORMALIZED_API_BASE,
  timeout: 15000,
});

// Добавляем интерцептор для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);

    if (error.response) {
      // Сервер ответил с ошибкой
      console.error('Response error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Запрос был сделан, но ответ не получен
      console.error('Request error:', error.request);
    } else {
      // Что-то пошло не так при настройке запроса
      console.error('Error:', error.message);
    }

    return Promise.reject(error);
  }
);
