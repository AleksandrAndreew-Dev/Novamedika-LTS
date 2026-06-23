import api from "../api/client";
import userAuthService from "./userAuthService";
import telegramAuthService from "./telegramAuthService";

/**
 * Unified chat service — extracted from Chat.jsx + AskPharmacist.jsx
 * Handles both authorized (JWT/TMA) and anonymous modes
 *
 * NOTE: JWT Bearer token добавляется автоматически через interceptor в client.js.
 * Явно передаём headers только для TMA auth (Telegram Mini App),
 * так как interceptor не обрабатывает этот тип.
 */

const getTmaHeaders = () => {
  if (telegramAuthService.initData) {
    return { Authorization: `tma ${telegramAuthService.initData}` };
  }
  return {};
};

const generateAnonUserId = () => {
  let anonUserId = localStorage.getItem("anon_user_id");
  if (!anonUserId) {
    anonUserId = crypto.randomUUID
      ? crypto.randomUUID()
      : "anon-" + Date.now() + "-" + Math.random().toString(36).slice(2);
    localStorage.setItem("anon_user_id", anonUserId);
  }
  return anonUserId;
};

const saveToAnonHistory = (uuid, text) => {
  const history = JSON.parse(localStorage.getItem("anon_questions") || "[]");
  history.push({ uuid, text, created_at: new Date().toISOString() });
  localStorage.setItem("anon_questions", JSON.stringify(history));
};

export const chatService = {
  /** Create a new consultation/question */
  createConsultation: async (
    text,
    isAnonymous = false,
    category = "general",
  ) => {
    if (isAnonymous) {
      const anonUserId = generateAnonUserId();
      const response = await api.post(
        "/api/public/questions/",
        { text: text.trim(), category, anon_user_id: anonUserId },
        { headers: { "X-API-KEY": import.meta.env.VITE_API_KEY || "" } },
      );
      saveToAnonHistory(response.data.uuid, response.data.text);
      return response.data;
    }
    const inTelegram = !!telegramAuthService.initData;
    const config = inTelegram ? { headers: getTmaHeaders() } : {};
    const response = await api.post(
      "/api/consultations/",
      { text: text.trim(), category },
      config,
    );
    return response.data;
  },

  /** Load consultation data + messages */
  loadConsultation: async (id, isAnonymous = false, inTelegram = false) => {
    if (isAnonymous) {
      const [consultationRes, messagesRes] = await Promise.all([
        api.get(`/api/public/questions/${id}`),
        api.get(`/api/public/questions/${id}/messages`),
      ]);
      return {
        consultation: consultationRes.data,
        messages: messagesRes.data,
      };
    }
    // JWT добавляется interceptor-ом; явные headers нужны только для TMA
    const config = inTelegram ? { headers: getTmaHeaders() } : {};
    const [consultationRes, messagesRes] = await Promise.all([
      api.get(`/api/consultations/${id}`, config),
      api.get(`/api/consultations/${id}/messages`, config),
    ]);
    return {
      consultation: consultationRes.data,
      messages: messagesRes.data,
    };
  },

  /** Send a message to existing consultation */
  sendMessage: async (id, text, isAnonymous = false, inTelegram = false) => {
    if (isAnonymous) {
      const response = await api.post(`/api/public/questions/${id}/messages`, {
        text: text.trim(),
      });
      return response.data;
    }
    const config = inTelegram ? { headers: getTmaHeaders() } : {};
    const response = await api.post(
      `/api/consultations/${id}/messages`,
      { text: text.trim() },
      config,
    );
    return response.data;
  },

  /** Fetch messages only (for polling) */
  fetchMessages: async (id, isAnonymous = false, inTelegram = false) => {
    if (isAnonymous) {
      const res = await api.get(`/api/public/questions/${id}/messages`);
      return res.data;
    }
    const config = inTelegram ? { headers: getTmaHeaders() } : {};
    const res = await api.get(`/api/consultations/${id}/messages`, config);
    return res.data;
  },

  /** Check if user is anonymous */
  isAnonymous: () => !userAuthService.isAuthenticated(),
};

export default chatService;
