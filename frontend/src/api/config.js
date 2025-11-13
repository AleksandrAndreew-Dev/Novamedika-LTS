// src/api/config.js
export const API_BASE_URL =
  window.APP_CONFIG?.API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  (import.meta.env.MODE === 'development' ? 'http://localhost:8000' : 'https://api.spravka.novamedika.com');

// Убедимся, что baseURL не заканчивается на лишний слеш
export const NORMALIZED_API_BASE = API_BASE_URL.replace(/\/$/, '');
