import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useChat } from "../../context/ChatContext";
import ChatTrigger from "./ChatTrigger";
import "./ChatWidget.css";

export default function ChatWidget() {
  const {
    currentConsultationId,
    setCurrentConsultationId,
    messages,
    isWidgetOpen,
    openWidget,
    closeWidget,
    loading,
    error,
    unreadCount,
    isAnonymous,
    loadMessages,
    createConsultation,
    sendMessage,
  } = useChat();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const [newMessage, setNewMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [inputMode, setInputMode] = useState(
    currentConsultationId ? "message" : "question",
  );
  const [questionText, setQuestionText] = useState("");

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load messages when consultation changes
  useEffect(() => {
    if (currentConsultationId && isWidgetOpen && messages.length === 0) {
      loadMessages();
    }
  }, [currentConsultationId, isWidgetOpen, loadMessages, messages.length]);

  const handleToggle = useCallback(() => {
    if (isWidgetOpen) {
      closeWidget();
    } else {
      openWidget();
    }
  }, [isWidgetOpen, openWidget, closeWidget]);

  const handleCreateQuestion = async (e) => {
    e.preventDefault();
    if (!questionText.trim() || loading) return;
    try {
      await createConsultation(questionText.trim());
      setQuestionText("");
      setInputMode("message");
    } catch {
      // Error handled in context
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || sending) return;
    setSending(true);
    try {
      await sendMessage(newMessage.trim());
      setNewMessage("");
    } catch {
      // Error handled by caller
    } finally {
      setSending(false);
    }
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
      case "pending":
        return "В ожидании ответа";
      case "answered":
        return "Получен ответ";
      case "completed":
        return "Завершено";
      case "in_progress":
        return "В работе";
      default:
        return status || "В ожидании";
    }
  };

  const countUnread = messages.filter(
    (m) => m.sender_type !== "user" && !m.read,
  ).length;

  return (
    <div className="chat-widget" data-testid="chat-widget">
      {/* Trigger button */}
      <ChatTrigger
        unreadCount={countUnread || unreadCount}
        onClick={handleToggle}
        isOpen={isWidgetOpen}
      />

      {/* Widget window */}
      {isWidgetOpen && (
        <div className="chat-widget__window">
          {/* Header */}
          <div className="chat-widget__header">
            <div className="chat-widget__header-info">
              <div className="chat-widget__header-icon">Ф</div>
              <div>
                <div className="chat-widget__header-title">Фармацевт</div>
                <div className="chat-widget__header-status">
                  {currentConsultationId ? "В работе" : "Задайте вопрос"}
                </div>
              </div>
            </div>
            <button
              onClick={() => {
                if (currentConsultationId) {
                  navigate(`/chat/${currentConsultationId}`);
                } else {
                  navigate("/chat/new");
                }
              }}
              className="chat-widget__expand-btn"
              title="Открыть в полном окне"
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
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
              </svg>
            </button>
          </div>

          {/* Chat body */}
          <div className="chat-widget__body">
            {!currentConsultationId && inputMode === "question" ? (
              /* New question form */
              <div className="chat-widget__new-form">
                <div className="chat-widget__new-icon">
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <p className="chat-widget__new-text">
                  Задайте вопрос фармацевту — мы ответим в ближайшее время
                </p>
                <form
                  onSubmit={handleCreateQuestion}
                  className="chat-widget__new-form-input"
                >
                  <textarea
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    placeholder="Опишите ваш вопрос..."
                    rows={3}
                    className="chat-widget__textarea"
                  />
                  <button
                    type="submit"
                    disabled={loading || !questionText.trim()}
                    className="chat-widget__send-btn chat-widget__send-btn--primary"
                  >
                    {loading ? (
                      <span className="chat-widget__spinner" />
                    ) : (
                      "Отправить"
                    )}
                  </button>
                </form>
              </div>
            ) : currentConsultationId ? (
              /* Messages list */
              <>
                <div className="chat-widget__messages">
                  {messages.length === 0 && !loading && (
                    <div className="chat-widget__empty">
                      <p>Пока нет сообщений</p>
                      <p className="chat-widget__empty-hint">
                        Напишите свой вопрос фармацевту
                      </p>
                    </div>
                  )}
                  {loading && messages.length === 0 && (
                    <div className="chat-widget__loading">
                      <span className="chat-widget__spinner" />
                    </div>
                  )}
                  {messages.map((message, idx) => {
                    const isUser = message.sender_type === "user";
                    const prevMsg = idx > 0 ? messages[idx - 1] : null;
                    const showAvatar =
                      !isUser && (!prevMsg || prevMsg.sender_type === "user");
                    return (
                      <div
                        key={message.uuid || idx}
                        className={`chat-widget__msg ${isUser ? "chat-widget__msg--user" : "chat-widget__msg--pharmacist"}`}
                      >
                        {!isUser && (
                          <div
                            className={`chat-widget__avatar ${showAvatar ? "" : "chat-widget__avatar--hidden"}`}
                          >
                            Ф
                          </div>
                        )}
                        <div className="chat-widget__bubble">
                          {!isUser && showAvatar && (
                            <div className="chat-widget__name">Фармацевт</div>
                          )}
                          <div className="chat-widget__text">
                            {message.text}
                          </div>
                          <div className="chat-widget__time">
                            {formatTime(message.created_at)}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="chat-widget__input-area">
                  <form
                    onSubmit={handleSendMessage}
                    className="chat-widget__input-form"
                  >
                    <textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Напишите сообщение..."
                      rows={1}
                      className="chat-widget__textarea chat-widget__textarea--inline"
                      disabled={sending}
                    />
                    <button
                      type="submit"
                      disabled={sending || !newMessage.trim()}
                      className="chat-widget__send-btn"
                      aria-label="Отправить"
                    >
                      {sending ? (
                        <span className="chat-widget__spinner" />
                      ) : (
                        <svg
                          width="18"
                          height="18"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <line x1="22" y1="2" x2="11" y2="13" />
                          <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                      )}
                    </button>
                  </form>
                </div>
              </>
            ) : (
              /* Default — show new question form */
              <div className="chat-widget__new-form">
                <p className="chat-widget__new-text">
                  Задайте вопрос фармацевту
                </p>
                <form
                  onSubmit={handleCreateQuestion}
                  className="chat-widget__new-form-input"
                >
                  <textarea
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    placeholder="Опишите ваш вопрос..."
                    rows={3}
                    className="chat-widget__textarea"
                  />
                  <button
                    type="submit"
                    disabled={loading || !questionText.trim()}
                    className="chat-widget__send-btn chat-widget__send-btn--primary"
                  >
                    {loading ? (
                      <span className="chat-widget__spinner" />
                    ) : (
                      "Отправить"
                    )}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
