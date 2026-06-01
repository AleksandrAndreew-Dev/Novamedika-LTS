import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import questionsService from "../../services/questionsService";
import { logger } from "../../../utils/logger";

export default function ConsultationChat({
  questionId: propQuestionId,
  onClose,
}) {
  const params = useParams();
  const navigate = useNavigate();
  const questionId = propQuestionId || params?.questionId;
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState(null);
  const messagesEndRef = useRef(null);

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
        const questionData = await questionsService.getQuestionById(questionId);
        setQuestion(questionData);
        const dialogData = await questionsService.getDialog(questionId);
        setMessages(dialogData || []);
      } catch (error) {
        logger.error("Failed to load consultation data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [questionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!newMsg.trim() || !questionId) return;

    try {
      const sentMsg = await questionsService.sendMessage(questionId, newMsg);
      setMessages((prev) => [...prev, sentMsg]);
      setNewMsg("");

      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
      }
    } catch (error) {
      logger.error("Failed to send message:", error);
      alert("Не удалось отправить сообщение. Попробуйте еще раз.");
    }
  }, [newMsg, questionId]);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleBack = () => {
    if (onClose) {
      onClose();
    } else {
      navigate(-1);
    }
  };

  if (!questionId) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
        <p className="text-lg font-semibold text-gray-900">
          Выберите вопрос слева
        </p>
        <p className="mt-2 text-gray-600">
          Чат откроется сразу, без дополнительных переходов.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center rounded-3xl border border-gray-200 bg-gray-50 p-6">
        <div className="text-gray-500">Загрузка диалога...</div>
      </div>
    );
  }

  if (!question) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-lg font-semibold text-red-700">Вопрос не найден</p>
        <button
          type="button"
          onClick={handleBack}
          className="mt-4 rounded-full bg-white px-4 py-2 text-sm font-semibold text-red-700 border border-red-200 hover:bg-red-100"
        >
          Вернуться
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-4 border-b px-5 py-4 bg-gray-50">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Консультация</h3>
          <p className="text-sm text-gray-600">
            Статус: <span className="font-medium">{question.status}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={handleBack}
          className="rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100"
        >
          {onClose ? "Закрыть" : "Назад"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
            Диалог пока пуст. Напишите первое сообщение.
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.uuid}
              className={`flex ${msg.sender === "pharmacist" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-3xl p-4 ${msg.sender === "pharmacist" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"}`}
              >
                <p className="whitespace-pre-wrap wrap-break-word">
                  {msg.text}
                </p>
                <div className="mt-2 text-right text-xs opacity-80">
                  {formatTime(msg.created_at)}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t p-4 bg-white">
        <textarea
          value={newMsg}
          onChange={(e) => setNewMsg(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Напишите ответ фармацевту..."
          rows={2}
          className="w-full resize-none rounded-3xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-xs text-gray-500">{newMsg.length}/2000</span>
          <button
            type="button"
            onClick={handleSend}
            disabled={!newMsg.trim()}
            className="rounded-3xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
}
