import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import questionsService from "../../services/questionsService";
import { logger } from "../../../utils/logger";

export default function ConsultationChat() {
  const { questionId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState(null);
  const messagesEndRef = useRef(null);

  // Load question details and dialog history
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Load question details
        const questionData = await questionsService.getQuestionById(questionId);
        setQuestion(questionData);
        
        // Load dialog messages
        const dialogData = await questionsService.getDialog(questionId);
        setMessages(dialogData || []);
      } catch (error) {
        logger.error("Failed to load consultation data:", error);
      } finally {
        setLoading(false);
      }
    };
    
    if (questionId) {
      loadData();
    }
  }, [questionId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!newMsg.trim()) return;
    
    try {
      const sentMsg = await questionsService.sendMessage(questionId, newMsg);
      setMessages((prev) => [...prev, sentMsg]);
      setNewMsg("");
      
      // Haptic feedback for Telegram WebApp
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
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (!question) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Вопрос не найден</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b p-4 bg-gray-50">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-200 rounded-full transition-colors"
          >
            ←
          </button>
          <div className="flex-1">
            <h2 className="font-semibold text-lg">Консультация</h2>
            <p className="text-sm text-gray-600">
              Статус: <span className="font-medium">{question.status}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-8">
            Начните диалог с пользователем
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.uuid}
              className={`flex ${msg.sender === "pharmacist" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  msg.sender === "pharmacist"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
                <span
                  className={`text-xs mt-1 block ${
                    msg.sender === "pharmacist" ? "text-blue-100" : "text-gray-500"
                  }`}
                >
                  {formatTime(msg.created_at)}
                </span>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <textarea
            value={newMsg}
            onChange={(e) => setNewMsg(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Ваше сообщение..."
            rows="2"
            maxLength={2000}
          />
          <button
            onClick={handleSend}
            disabled={!newMsg.trim()}
            className="bg-blue-500 text-white rounded-lg px-6 py-2 font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
          >
            Отправить
          </button>
        </div>
        <div className="text-xs text-gray-400 mt-2 text-right">
          {newMsg.length}/2000
        </div>
      </div>
    </div>
  );
}
