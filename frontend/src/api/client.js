// src/api/client.js
import axios from "axios";
import { NORMALIZED_API_BASE } from "./config";
import { logger } from "../utils/logger";

export const api = axios.create({
  baseURL: NORMALIZED_API_BASE,
  timeout: 15000,
});

// Добавляем интерцептор для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    logger.error("API Error:", error);

    if (error.response) {
      logger.error(
        "Response error:",
        error.response.status,
        error.response.data,
      );
    } else if (error.request) {
      logger.error("Request error:", error.request);
    } else {
      logger.error("Error:", error.message);
    }

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

// Экспортируем по умолчанию основной API клиент
export default api;
