import {
  useEffect,
  useState,
  useCallback,
  useRef,
} from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import questionsService from '../../services/questionsService';
import websocketService from '../../services/websocketService';
import { logger } from '../../../utils/logger';

export default function ConsultationChat({
  questionId: propQuestionId,
  onClose,
}) {
  const params = useParams();
  const navigate = useNavigate();
  const questionId = propQuestionId || params?.questionId;
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [question, setQuestion] = useState(null);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Subscribe to WebSocket for real-time message updates
  useEffect(() => {
    // Connect WebSocket on mount
    websocketService.connect();

    // Listen for new messages in this consultation
    const unsubscribe = websocketService.on(
      'message_update',
      (payload) => {
        if (payload && payload.question_id === questionId) {
          setMessages((prev) => {
            const prevIds = new Set(
              prev.map(
                (m) =>
                  m.uuid ||
                  m.id ||
                  m.data?.uuid ||
                  m.data?.id,
              ),
            );
            const msgId =
              payload.uuid ||
              payload.id ||
              payload.data?.uuid ||
              payload.data?.id;
            // Проверка по UUID
            if (msgId && prevIds.has(msgId)) return prev;
            const newMsg = payload.data || payload;
            // Дополнительная проверка по комбинации полей (защита от дублей при тайминге)
            const isDuplicate = prev.some(
              (m) =>
                m.text === newMsg.text &&
                m.sender_type === newMsg.sender_type &&
                Math.abs(
                  new Date(m.created_at) -
                    new Date(newMsg.created_at),
                ) < 1000,
            );
            if (isDuplicate) return prev;
            const updated = [...prev, newMsg];
            updated.sort(
              (a, b) =>
                new Date(a.created_at) -
                new Date(b.created_at),
            );
            return updated;
          });
        }
      },
    );

    return () => {
      unsubscribe();
    };
  }, [questionId]);

  useEffect(() => {
    const loadData = async () => {
      if (!questionId) {
        setQuestion(null);
        setMessages([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const questionData =
          await questionsService.getQuestionById(
            questionId,
          );
        setQuestion(questionData);
        const dialogData =
          await questionsService.getDialog(questionId);
        setMessages(dialogData || []);
      } catch (error) {
        logger.error(
          'Failed to load consultation data:',
          error,
        );
        setError(
          'Не удалось загрузить данные консультации',
        );
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [questionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!newMsg.trim() || !questionId) return;

    try {
      setSending(true);
      const sentMsg = await questionsService.sendMessage(
        questionId,
        newMsg,
      );
      setMessages((prev) => [...prev, sentMsg]);
      setNewMsg('');

      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred(
          'success',
        );
      }
    } catch (error) {
      logger.error('Failed to send message:', error);
      setError('Не удалось отправить сообщение');
    } finally {
      setSending(false);
    }
  }, [newMsg, questionId]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString(
      'ru-RU',
      {
        hour: '2-digit',
        minute: '2-digit',
      },
    );
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
    setIsAtBottom(true);
  };

  const handleScroll = (e) => {
    const el = e.currentTarget;
    const threshold = 80;
    const atBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight <
      threshold;
    setIsAtBottom(atBottom);
  };

  const handleBack = () => {
    if (onClose) onClose();
    else navigate('/pharmacist'); // Явный переход на главную страницу вместо navigate(-1)
  };

  const getUserName = () => {
    if (!question) return 'Пользователь';
    const user = question.user;
    return (
      user?.first_name ||
      user?.telegram_username ||
      `Пользователь #${user?.telegram_id?.toString().slice(-4) || ''}`
    );
  };

  const getUserAvatar = () => {
    return getUserName().charAt(0).toUpperCase();
  };

  const getUserColor = () => {
    const colors = [
      '#16a34a',
      '#ea580c',
      '#7c3aed',
      '#ec4899',
      '#2563eb',
      '#0891b2',
      '#65a30d',
    ];
    const user = question?.user;
    const seed = user?.telegram_id || user?.uuid || 0;
    // Convert to number for color selection
    const num =
      typeof seed === 'string'
        ? seed
            .split('')
            .reduce((a, c) => a + c.charCodeAt(0), 0)
        : Number(seed);
    return colors[num % colors.length];
  };

  const getStatusBadge = () => {
    if (!question) return null;
    const badges = {
      pending: {
        text: 'В ожидании',
        class: 'bg-yellow-100 text-yellow-700',
      },
      answered: {
        text: 'Отвечено',
        class: 'bg-green-100 text-green-700',
      },
      completed: {
        text: 'Завершено',
        class: 'bg-gray-100 text-gray-500',
      },
      in_progress: {
        text: 'В работе',
        class: 'bg-blue-100 text-blue-700',
      },
    };
    const badge = badges[question.status] || badges.pending;
    return (
      <span
        className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium ${badge.class}`}
      >
        {badge.text}
      </span>
    );
  };

  // Empty state
  if (!questionId) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-gray-50 p-6 text-center">
        <svg
          width="160"
          height="112"
          viewBox="0 0 200 140"
          fill="none"
          className="opacity-30 mb-4"
        >
          <rect
            x="10"
            y="20"
            width="180"
            height="100"
            rx="12"
            stroke="#d1d5db"
            strokeWidth="2"
            fill="#f9fafb"
          />
          <rect
            x="25"
            y="35"
            width="60"
            height="8"
            rx="4"
            fill="#e5e7eb"
          />
          <rect
            x="25"
            y="50"
            width="100"
            height="6"
            rx="3"
            fill="#e5e7eb"
          />
          <rect
            x="25"
            y="62"
            width="80"
            height="6"
            rx="3"
            fill="#e5e7eb"
          />
          <rect
            x="140"
            y="80"
            width="40"
            height="8"
            rx="4"
            fill="#3b82f6"
            opacity="0.3"
          />
        </svg>
        <p className="text-base font-semibold text-gray-800">
          Выберите консультацию
        </p>
        <p className="mt-1.5 text-sm text-gray-500">
          Чат откроется в этой панели
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-50 p-6">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
          <span className="text-sm">
            Загрузка диалога...
          </span>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !question) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-red-50 p-6 text-center">
        <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-3">
          <svg
            className="w-6 h-6 text-red-500"
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
        <p className="text-sm font-semibold text-red-700">
          {error}
        </p>
        <button
          onClick={handleBack}
          className="mt-3 px-4 py-1.5 text-xs font-medium bg-white border border-red-200 rounded-full text-red-600 hover:bg-red-50"
        >
          Вернуться
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-gray-100 rounded-2xl border border-gray-200 shadow-sm">
      {/* ===== HEADER ===== */}
      <div className="bg-white px-4 py-3 flex items-center gap-3 border-b border-gray-200 flex-shrink-0">
        <button
          onClick={handleBack}
          className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors flex-shrink-0"
          aria-label="Назад"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0 relative"
          style={{
            background: `linear-gradient(135deg, ${getUserColor()}, ${getUserColor()}dd)`,
          }}
        >
          {getUserAvatar()}
          {question?.status === 'pending' && (
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"></span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 text-sm tracking-wide truncate">
            {getUserName()}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[11px] text-gray-400">
              {question?.status === 'pending'
                ? 'ожидает ответа'
                : question?.status === 'answered'
                  ? 'есть ответ'
                  : question?.status}
            </span>
            {getStatusBadge()}
          </div>
        </div>
        <button
          onClick={async () => {
            if (confirm('Завершить консультацию?')) {
              try {
                await questionsService.completeQuestion(
                  questionId,
                );
                if (onClose) onClose();
              } catch (e) {
                logger.error('Failed to complete:', e);
              }
            }
          }}
          className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-full transition-colors"
          aria-label="Завершить"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="8" y1="12" x2="16" y2="12"></line>
          </svg>
        </button>
      </div>

      {/* ===== MESSAGES ===== */}
      <div
        className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-0.5 scroll-smooth"
        onScroll={handleScroll}
      >
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <svg
                className="w-14 h-14 mx-auto text-gray-300 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="text-gray-500 text-sm">
                Диалог пока пуст
              </p>
              <p className="text-gray-400 text-xs mt-1">
                Напишите первое сообщение
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isPharmacist =
              msg.sender_type === 'pharmacist';
            const prevMsg =
              idx > 0 ? messages[idx - 1] : null;
            const showAvatar =
              !isPharmacist &&
              (!prevMsg ||
                prevMsg.sender_type === 'pharmacist');

            return (
              <div
                key={msg.uuid || idx}
                className={`flex ${isPharmacist ? 'justify-end' : 'justify-start'} mb-0.5 animate-fadeIn`}
              >
                {!isPharmacist && (
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-semibold flex-shrink-0 mt-1 ${showAvatar ? 'mr-2' : 'mr-2 invisible'}`}
                    style={{
                      background: `linear-gradient(135deg, ${getUserColor()}, ${getUserColor()}dd)`,
                    }}
                  >
                    {getUserAvatar()}
                  </div>
                )}
                <div
                  className={`max-w-[82%] ${isPharmacist ? 'order-1' : 'order-2'}`}
                >
                  {!isPharmacist && showAvatar && (
                    <div className="text-[11px] font-semibold text-blue-600 mb-0.5 tracking-wide">
                      {getUserName()}
                    </div>
                  )}
                  <div
                    className={`px-3.5 py-2.5 rounded-2xl ${
                      isPharmacist
                        ? 'bg-green-100 text-gray-900 rounded-br-md'
                        : 'bg-white text-gray-900 rounded-bl-md shadow-sm border border-gray-100'
                    }`}
                  >
                    <div className="text-[14px] leading-relaxed whitespace-pre-wrap break-words">
                      {msg.text}
                    </div>
                    <div
                      className={`flex items-center justify-end gap-1 mt-1 ${isPharmacist ? 'text-gray-400' : 'text-gray-400'}`}
                    >
                      <span className="text-[10px] opacity-70">
                        {formatTime(msg.created_at)}
                      </span>
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
        <button
          onClick={scrollToBottom}
          className="absolute bottom-24 right-6 w-8 h-8 bg-white border border-gray-200 rounded-full shadow-md flex items-center justify-center z-10 hover:shadow-lg"
          aria-label="Вниз"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      )}

      {/* ===== INPUT ===== */}
      <div className="bg-white px-3 py-2.5 border-t border-gray-200 flex-shrink-0">
        {error && (
          <div className="mb-2 px-3 py-1.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-400 hover:text-red-600"
            >
              ✕
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <div className="flex-1 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-1 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
            <textarea
              value={newMsg}
              onChange={(e) => setNewMsg(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Напишите ответ..."
              rows={1}
              className="w-full bg-transparent border-none outline-none resize-none text-[14px] py-2 max-h-24 leading-relaxed text-gray-900 placeholder:text-gray-400"
              style={{
                fontFamily: 'inherit',
              }}
              disabled={
                sending || question?.status === 'completed'
              }
            />
          </div>
          <button
            onClick={handleSend}
            disabled={
              sending ||
              !newMsg.trim() ||
              question?.status === 'completed'
            }
            className="w-9 h-9 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center flex-shrink-0 transition-colors active:scale-90"
            aria-label="Отправить"
          >
            {sending ? (
              <svg
                className="animate-spin h-4 w-4 text-white"
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
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                ></path>
              </svg>
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4 fill-white"
              >
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
              </svg>
            )}
          </button>
        </div>
        {question?.status === 'completed' && (
          <p className="text-xs text-gray-400 text-center mt-2">
            Консультация завершена
          </p>
        )}
      </div>

      {/* ===== STYLES ===== */}
      <style>{`
        .animate-fadeIn { animation: fadeIn 0.2s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}
