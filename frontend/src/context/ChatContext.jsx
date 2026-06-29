/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from 'react';
import chatService from '../services/chatService';

const ChatContext =
  createContext(null);

/**
 * ChatContext — глобальное состояние для управления чат-виджетом
 * Хранит: currentConsultationId, messages, isWidgetOpen
 * Предоставляет: sendMessage, loadMessages, createConsultation, openWidget, closeWidget
 * Использует WebSocket для получения сообщений в реальном времени (с fallback на polling)
 */
export function ChatProvider({
  children,
}) {
  const [
    currentConsultationId,
    setCurrentConsultationId,
  ] = useState(
    () =>
      localStorage.getItem(
        'current_chat_id',
      ) || null,
  );
  const [
    messages,
    setMessages,
  ] = useState([]);
  const [
    isWidgetOpen,
    setIsWidgetOpen,
  ] = useState(false);
  const [
    loading,
    setLoading,
  ] = useState(false);
  const [error, setError] =
    useState(null);
  const [
    unreadCount,
    setUnreadCount,
  ] = useState(0);
  const [
    isAnonymous,
    setIsAnonymous,
  ] = useState(() =>
    chatService.isAnonymous(),
  );
  const pollingRef =
    useRef(null);
  const wsRef = useRef(null);
  const wsReconnectRef =
    useRef(null);

  // WebSocket protocol
  const isSecure =
    window.location
      .protocol === 'https:';
  const wsBaseUrl = `${isSecure ? 'wss' : 'ws'}://${window.location.host}/api/pharmacist`;
  const reconnectDelay = 3000;

  // Sync anonymous status on auth change
  useEffect(() => {
    setIsAnonymous(
      chatService.isAnonymous(),
    );
  }, []);

  // Save current chat ID to localStorage
  useEffect(() => {
    if (
      currentConsultationId
    ) {
      localStorage.setItem(
        'current_chat_id',
        currentConsultationId,
      );
    } else {
      localStorage.removeItem(
        'current_chat_id',
      );
    }
  }, [currentConsultationId]);

  // Reset unread when widget opens
  useEffect(() => {
    if (isWidgetOpen) {
      setUnreadCount(0);
    }
  }, [isWidgetOpen]);

  // WebSocket connection for real-time message updates
  // Анонимные пользователи используют polling (см. pollingFallback ниже)
  useEffect(() => {
    if (
      !currentConsultationId
    ) {
      // Close WebSocket if no consultation
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    let mounted = true;

    const connectWs = () => {
      if (
        !mounted ||
        wsRef.current
          ?.readyState ===
          WebSocket.OPEN
      )
        return;

      try {
        const ws =
          new WebSocket(
            `${wsBaseUrl}/ws/chat/${currentConsultationId}`,
          );
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(
            `[ChatContext] WebSocket connected for ${currentConsultationId}`,
          );
          // Send initial ping
          ws.send('ping');
        };

        ws.onmessage = (
          event,
        ) => {
          try {
            const data =
              JSON.parse(
                event.data,
              );
            if (
              data.type ===
              'message_update'
            ) {
              const msg =
                data.data;
              if (!msg)
                return;

              setMessages(
                (prev) => {
                  const prevIds =
                    new Set(
                      prev.map(
                        (m) =>
                          m.uuid ||
                          m.id,
                      ),
                    );
                  if (
                    prevIds.has(
                      msg.uuid,
                    )
                  )
                    return prev;
                  const updated =
                    [
                      ...prev,
                      msg,
                    ];
                  updated.sort(
                    (a, b) =>
                      new Date(
                        a.created_at,
                      ) -
                      new Date(
                        b.created_at,
                      ),
                  );
                  return updated;
                },
              );

              // Increment unread if widget is closed
              if (
                !isWidgetOpen
              ) {
                setUnreadCount(
                  (prev) =>
                    prev + 1,
                );
              }
            }
          } catch {
            // Not JSON — might be "pong" or other text
          }
        };

        ws.onclose = () => {
          wsRef.current =
            null;
          if (!mounted)
            return;
          // Reconnect after delay
          wsReconnectRef.current =
            setTimeout(
              connectWs,
              reconnectDelay,
            );
        };

        ws.onerror = () => {
          // onclose will fire after onerror, so reconnect is handled there
        };

        // Ping every 30s to keep connection alive
        const pingInterval =
          setInterval(() => {
            if (
              ws.readyState ===
              WebSocket.OPEN
            ) {
              ws.send('ping');
            }
          }, 30000);

        // Store interval on ws object for cleanup
        ws._pingInterval =
          pingInterval;
      } catch (err) {
        console.error(
          `[ChatContext] WebSocket connection error: ${err}`,
        );
        // Fallback to polling will handle it
      }
    };

    connectWs();

    return () => {
      mounted = false;
      if (
        wsReconnectRef.current
      ) {
        clearTimeout(
          wsReconnectRef.current,
        );
        wsReconnectRef.current =
          null;
      }
      if (wsRef.current) {
        clearInterval(
          wsRef.current
            ._pingInterval,
        );
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [
    currentConsultationId,
    isAnonymous,
    isWidgetOpen,
    wsBaseUrl,
  ]);

  // Flag to ensure we only do initial load once per consultation
  const initialLoadDoneRef =
    useRef(false);

  // Polling fallback (used when WebSocket is not available or for anonymous users)
  useEffect(() => {
    if (
      !currentConsultationId
    )
      return;

    initialLoadDoneRef.current = false;

    const poll = async () => {
      try {
        const newMessages =
          await chatService.fetchMessages(
            currentConsultationId,
            isAnonymous,
            false,
          );
        setMessages(
          (prev) => {
            const prevIds =
              new Set(
                prev.map(
                  (m) =>
                    m.uuid ||
                    m.id,
                ),
              );
            const added =
              newMessages.filter(
                (m) =>
                  !prevIds.has(
                    m.uuid ||
                      m.id,
                  ),
              );
            if (
              added.length ===
              0
            )
              return prev;
            const updated = [
              ...prev,
              ...added,
            ];
            updated.sort(
              (a, b) =>
                new Date(
                  a.created_at,
                ) -
                new Date(
                  b.created_at,
                ),
            );
            return updated;
          },
        );
      } catch {
        // Silent fail
      }
    };

    // Only set up polling if WebSocket is not available or for anonymous
    // For anonymous users — always poll
    if (isAnonymous) {
      poll();
      pollingRef.current =
        setInterval(
          poll,
          5000,
        );
    } else {
      // For non-anonymous: still poll as fallback, but less frequently
      poll();
      // Poll every 30s as safety fallback (WebSocket is primary)
      pollingRef.current =
        setInterval(
          poll,
          30000,
        );
    }

    return () => {
      if (
        pollingRef.current
      ) {
        clearInterval(
          pollingRef.current,
        );
        pollingRef.current =
          null;
      }
    };
  }, [
    currentConsultationId,
    isAnonymous,
  ]);

  const loadMessages =
    useCallback(async () => {
      if (
        !currentConsultationId
      )
        return;
      setLoading(true);
      setError(null);
      try {
        const data =
          await chatService.fetchMessages(
            currentConsultationId,
            isAnonymous,
            false,
          );
        setMessages(data);
      } catch {
        setError(
          'Не удалось загрузить сообщения',
        );
      } finally {
        setLoading(false);
      }
    }, [
      currentConsultationId,
      isAnonymous,
    ]);

  const createConsultation =
    useCallback(
      async (text) => {
        setLoading(true);
        setError(null);
        try {
          const data =
            await chatService.createConsultation(
              text,
              chatService.isAnonymous(),
            );
          setCurrentConsultationId(
            data.uuid,
          );
          setMessages([]);
          return data;
        } catch (e) {
          setError(
            'Не удалось создать консультацию',
          );
          throw e;
        } finally {
          setLoading(false);
        }
      },
      [],
    );

  const sendMessage =
    useCallback(
      async (text) => {
        if (
          !currentConsultationId ||
          !text.trim()
        )
          return;
        const data =
          await chatService.sendMessage(
            currentConsultationId,
            text,
            isAnonymous,
            false,
          );
        setMessages(
          (prev) => [
            ...prev,
            data,
          ],
        );
      },
      [
        currentConsultationId,
        isAnonymous,
      ],
    );

  const openWidget =
    useCallback(() => {
      setIsWidgetOpen(true);
    }, []);

  const closeWidget =
    useCallback(() => {
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

  return (
    <ChatContext.Provider
      value={value}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(
    ChatContext,
  );
  if (!ctx) {
    throw new Error(
      'useChat must be used within ChatProvider',
    );
  }
  return ctx;
}
