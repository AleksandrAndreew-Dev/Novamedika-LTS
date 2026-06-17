import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import userAuthService from "../services/userAuthService";
import telegramAuthService from "../services/telegramAuthService";
import Toast from "../components/Toast";

export default function Chat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [consultation, setConsultation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isTelegramUser, setIsTelegramUser] = useState(false);

  useEffect(() => {
    const initChat = async () => {
      try {
        // 1. Попытка Telegram WebApp auto-login (если в Telegram)
        const inTelegram = telegramAuthService.canAuthViaWebApp();
        setIsTelegramUser(inTelegram);

        if (inTelegram) {
          const success = await telegramAuthService.autoLogin();
          if (success) {
            console.log("[Chat] ✅ Telegram auto-login successful");
          } else {
            console.log("[Chat] ⚠️ Telegram auto-login failed, using initData as fallback");
            // Продолжаем без JWT — backend может идентифицировать пользователя
            // через initData в заголовке Authorization: tma <initData>
          }
        }

        // 2. Загружаем данные консультации
        await loadConsultationData(inTelegram);
      } catch (err) {
        console.error("[Chat] Init error:", err);
        setError("Не удалось загрузить консультацию");
      } finally {
        setLoading(false);
      }
    };

    initChat();
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getAuthHeaders = (inTelegram) => {
    const token = userAuthService.getAccessToken();
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    // Fallback для Telegram WebApp без JWT — используем initData
    if (inTelegram && telegramAuthService.initData) {
      return { Authorization: `tma ${telegramAuthService.initData}` };
    }
    return {};
  };

  const loadConsultationData = async (inTelegram = false) => {
    try {
      setLoading(true);

      const headers = getAuthHeaders(inTelegram);

      const [consultationRes, messagesRes] = await Promise.all([
        api.get(`/api/consultations/${id}`, { headers }).catch(() => null),
        api.get(`/api/consultations/${id}/messages`, { headers }).catch(() => null),
      ]);

      if (consultationRes) setConsultation(consultationRes.data);
      if (messagesRes) setMessages(messagesRes.data);

      // Если не удалось загрузить — пробуем создать новую консультацию
      if (!consultationRes && inTelegram) {
        const createRes = await api.post("/api/consultations/", {
          text: "Новый вопрос фармацевту",
          category: "general",
        }, { headers });
        // Редирект на новую консультацию
        navigate(`/chat/${createRes.data.uuid}`, { replace: true });
      }
    } catch (err) {
      console.error("Failed to load consultation:", err);
      if (err.response?.status === 401) {
        if (!inTelegram) {
          navigate("/login");
        }
        // В Telegram — показываем ошибку, но не редиректим
        setError("Не удалось загрузить консультацию. Попробуйте позже.");
      } else if (err.response?.status === 404) {
        setError("Консультация не найдена");
      } else {
        setError("Не удалось загрузить консультацию");
      }
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    const inTelegram = isTelegramUser;
    const headers = getAuthHeaders(inTelegram);

    try {
      setSending(true);
      const response = await api.post(`/api/consultations/${id}/messages`, {
        text: newMessage.trim(),
      }, { headers });
      setMessages((prev) => [...prev, response.data]);
      setNewMessage("");
    } catch (err) {
      setToast({
        message: err.userMessage || "Ошибка отправки сообщения",
        type: "error",
      });
    } finally {
      setSending(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    setIsAtBottom(true);
  };

  const handleScroll = () => {
    const el = document.querySelector(".messages-scroll");
    if (!el) return;
    const threshold = 100;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setIsAtBottom(atBottom);
  };

  const formatTime = (dateString) => {
    if (!dateString) return "";
    return new Date(dateString).toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusText = (status) => {
    switch (status) {
      case "pending": return "В ожидании ответа";
      case "answered": return "Получен ответ";
      case "completed": return "Завершено";
      case "in_progress": return "В работе";
      default: return status || "В ожидании";
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500 text-sm">Загрузка консультации...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка</h2>
          <p className="text-gray-500 mb-6">{error}</p>
          <button onClick={() => navigate(isTelegramUser ? "/" : "/dashboard")}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-6 rounded-full transition-colors">
            {isTelegramUser ? "На главную" : "Вернуться в кабинет"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100 max-w-lg mx-auto shadow-lg relative overflow-hidden">
      {/* ===== HEADER ===== */}
      <header className="bg-white px-4 py-3 flex items-center gap-3 border-b border-gray-200 flex-shrink-0 z-10">
        <button onClick={() => navigate(isTelegramUser ? "/" : "/dashboard")}
          className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors" aria-label="Назад">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-500 flex items-center justify-center text-white font-semibold text-lg flex-shrink-0 relative">
          Ф
          {(consultation?.status === "pending" || consultation?.status === "in_progress") && (
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 text-[15px] tracking-wide">Фармацевт</div>
          <div className="text-xs flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${
              consultation?.status === "pending" || consultation?.status === "in_progress"
                ? "bg-green-500" : "bg-gray-400"
            }`}></span>
            <span className={consultation?.status === "completed" ? "text-gray-500" : "text-green-600"}>
              {getStatusText(consultation?.status)}
            </span>
          </div>
        </div>
        <button onClick={() => setToast({ message: "Консультация", type: "success" })}
          className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-full transition-colors" aria-label="Информация">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
        </button>
      </header>

      {/* ===== MESSAGES ===== */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-1 scroll-smooth messages-scroll" onScroll={handleScroll}>
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-gray-300 mb-3">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                </svg>
              </div>
              <p className="text-gray-500 text-sm">Пока нет сообщений</p>
              <p className="text-gray-400 text-xs mt-1">Напишите свой вопрос фармацевту</p>
            </div>
          </div>
        ) : (
          messages.map((message, idx) => {
            const isUser = message.sender_type === "user";
            const prevMsg = idx > 0 ? messages[idx - 1] : null;
            const showAvatar = !isUser && (!prevMsg || prevMsg.sender_type === "user");

            return (
              <div key={message.uuid || idx} className={`flex ${isUser ? "justify-end" : "justify-start"} mb-0.5 animate-fadeIn`}>
                {!isUser && (
                  <div className={`w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-indigo-500 flex items-center justify-center text-white text-[10px] font-semibold flex-shrink-0 mt-1 ${showAvatar ? "mr-2" : "mr-2 invisible"}`}>
                    Ф
                  </div>
                )}
                <div className={`max-w-[82%] ${isUser ? "order-1" : "order-2"}`}>
                  {!isUser && showAvatar && (
                    <div className="text-[11px] font-semibold text-blue-600 mb-0.5 tracking-wide">Фармацевт</div>
                  )}
                  <div className={`px-3.5 py-2.5 rounded-2xl ${
                    isUser
                      ? "bg-blue-600 text-white rounded-br-md"
                      : "bg-white text-gray-900 rounded-bl-md shadow-sm border border-gray-100"
                  }`}>
                    <div className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">{message.text}</div>
                    <div className={`flex items-center justify-end gap-1 mt-1 ${isUser ? "text-blue-200" : "text-gray-400"}`}>
                      <span className="text-[10px] opacity-70">{formatTime(message.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to bottom */}
      {!isAtBottom && messages.length > 0 && (
        <button onClick={scrollToBottom}
          className="absolute bottom-24 right-5 w-9 h-9 bg-white border border-gray-200 rounded-full shadow-md flex items-center justify-center z-10 hover:shadow-lg transition-shadow"
          aria-label="Вниз">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      )}

      {/* ===== INPUT ===== */}
      <div className="bg-white px-3 py-3 border-t border-gray-200 flex-shrink-0">
        <form onSubmit={sendMessage} className="flex items-end gap-2">
          <div className="flex-1 flex items-end bg-gray-50 border border-gray-200 rounded-2xl px-4 py-1 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Напишите сообщение..."
              rows={1}
              className="flex-1 bg-transparent border-none outline-none resize-none text-[15px] py-2 max-h-24 leading-relaxed text-gray-900 placeholder:text-gray-400"
              style={{ fontFamily: 'inherit' }}
              disabled={sending || consultation?.status === "completed"}
            />
          </div>
          <button
            type="submit"
            disabled={sending || !newMessage.trim() || consultation?.status === "completed"}
            className="w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center flex-shrink-0 transition-colors active:scale-90"
            aria-label="Отправить"
          >
            {sending ? (
              <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
              </svg>
            )}
          </button>
        </form>
        {consultation?.status === "completed" && (
          <p className="text-xs text-gray-400 text-center mt-2">Консультация завершена. Создайте новую для других вопросов.</p>
        )}
      </div>

      {/* ===== TOAST ===== */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} duration={toast.type === "error" ? 5000 : 2000} />}

      {/* ===== STYLES ===== */}
      <style>{`
        .animate-fadeIn { animation: fadeIn 0.25s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}
