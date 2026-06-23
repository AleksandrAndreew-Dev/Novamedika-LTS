import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from "react";
import chatService from "../services/chatService";

const ChatContext = createContext(null);

/**
 * ChatContext — глобальное состояние для управления чат-виджетом
 * Хранит: currentConsultationId, messages, isWidgetOpen
 * Предоставляет: sendMessage, loadMessages, createConsultation, openWidget, closeWidget
 */
export function ChatProvider({ children }) {
  const [currentConsultationId, setCurrentConsultationId] = useState(
    () => localStorage.getItem("current_chat_id") || null,
  );
  const [messages, setMessages] = useState([]);
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isAnonymous, setIsAnonymous] = useState(() =>
    chatService.isAnonymous(),
  );
  const pollingRef = useRef(null);

  // Sync anonymous status on auth change
  useEffect(() => {
    setIsAnonymous(chatService.isAnonymous());
  }, []);

  // Save current chat ID to localStorage
  useEffect(() => {
    if (currentConsultationId) {
      localStorage.setItem("current_chat_id", currentConsultationId);
    } else {
      localStorage.removeItem("current_chat_id");
    }
  }, [currentConsultationId]);

  // Reset unread when widget opens
  useEffect(() => {
    if (isWidgetOpen) {
      setUnreadCount(0);
    }
  }, [isWidgetOpen]);

  // Polling for new messages when widget is open and has active consultation
  useEffect(() => {
    if (!currentConsultationId) return;

    const poll = async () => {
      try {
        const newMessages = await chatService.fetchMessages(
          currentConsultationId,
          isAnonymous,
          false,
        );
        setMessages((prev) => {
          // Check if we have new messages
          const prevIds = new Set(prev.map((m) => m.uuid || m.id));
          const added = newMessages.filter((m) => !prevIds.has(m.uuid || m.id));
          if (added.length === 0) return prev;
          const updated = [...prev, ...added];
          updated.sort(
            (a, b) => new Date(a.created_at) - new Date(b.created_at),
          );
          return updated;
        });
      } catch {
        // Silent fail
      }
    };

    // Initial fetch
    if (messages.length === 0) {
      poll();
    }

    // Start polling
    pollingRef.current = setInterval(poll, 5000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [currentConsultationId, isAnonymous, messages.length]);

  const loadMessages = useCallback(async () => {
    if (!currentConsultationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await chatService.fetchMessages(
        currentConsultationId,
        isAnonymous,
        false,
      );
      setMessages(data);
    } catch (err) {
      setError("Не удалось загрузить сообщения");
    } finally {
      setLoading(false);
    }
  }, [currentConsultationId, isAnonymous]);

  const createConsultation = useCallback(async (text) => {
    setLoading(true);
    setError(null);
    try {
      const data = await chatService.createConsultation(
        text,
        chatService.isAnonymous(),
      );
      setCurrentConsultationId(data.uuid);
      setMessages([]);
      return data;
    } catch (err) {
      setError("Не удалось создать консультацию");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!currentConsultationId || !text.trim()) return;
      try {
        const data = await chatService.sendMessage(
          currentConsultationId,
          text,
          isAnonymous,
          false,
        );
        setMessages((prev) => [...prev, data]);
      } catch (err) {
        throw err;
      }
    },
    [currentConsultationId, isAnonymous],
  );

  const openWidget = useCallback(() => {
    setIsWidgetOpen(true);
  }, []);

  const closeWidget = useCallback(() => {
    setIsWidgetOpen(false);
  }, []);

  const value = {
    currentConsultationId,
    setCurrentConsultationId,
    messages,
    setMessages,
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
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used within ChatProvider");
  }
  return ctx;
}

export default ChatContext;
