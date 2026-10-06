import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  memo,
} from 'react';
import QuestionsList from './QuestionsList';
import ConsultationChat from './ConsultationChat';
import DashboardStats from '../dashboard/DashboardStats';
import { questionsService } from '../../services/questionsService';
import websocketService from '../../services/websocketService';
import { logger } from '../../../utils/logger';

const filterOptions = [
  {
    key: 'new',
    label: 'Новые',
    icon: '🆕',
  },
  {
    key: 'in_progress',
    label: 'В работе',
    icon: '🔄',
  },
  {
    key: 'answered',
    label: 'Отвеченные',
    icon: '💬',
  },
  {
    key: 'all',
    label: 'Все',
    icon: '📋',
  },
];

const MemoizedQuestionsList = memo(QuestionsList);
const MemoizedConsultationChat = memo(ConsultationChat);

export default function ChatDashboard({
  isPanelVisible = true,
}) {
  const [filter, setFilter] = useState('new');
  const [activeQuestionId, setActiveQuestionId] =
    useState(null);
  const [isMobile, setIsMobile] = useState(
    window.innerWidth < 768,
  );
  const [activeTab, setActiveTab] = useState('questions'); // 'questions' | 'stats'
  const [panelWidth, setPanelWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [listRefreshKey, setListRefreshKey] = useState(0);
  // Счётчики для явных бейджей на каждом фильтре + пульс таба при WS-событии
  const [tabCounts, setTabCounts] = useState({
    new: 0,
    in_progress: 0,
    answered: 0,
  });
  const [flashTab, setFlashTab] = useState(null); // 'new' | 'in_progress' | null
  const [toast, setToast] = useState(null); // { id, kind, text, targetFilter }
  const flashTimerRef = useRef(null);
  const toastTimerRef = useRef(null);
  const panelRef = useRef(null);
  const autoSelectDoneRef = useRef(false);
  const activeQuestionIdRef = useRef(activeQuestionId);

  useEffect(() => {
    activeQuestionIdRef.current = activeQuestionId;
  }, [activeQuestionId]);

  const selectNextPendingQuestion =
    useCallback(async () => {
      try {
        const data = await questionsService.getQuestions({
          status: 'pending',
        });
        const questions = data?.questions || data || [];
        if (questions.length > 0) {
          const firstId =
            questions[0].uuid || questions[0].id;
          if (firstId) {
            setActiveQuestionId(firstId);
          } else {
            setActiveQuestionId(null);
          }
        } else {
          setActiveQuestionId(null);
        }
      } catch (_e) {
        // Silently fail — user can select manually
      }
    }, []);

  // Auto-select first new question on mount
  useEffect(() => {
    if (autoSelectDoneRef.current) return;
    autoSelectDoneRef.current = true;

    void selectNextPendingQuestion();
  }, [selectNextPendingQuestion]);

  useEffect(() => {
    const handleResize = () =>
      setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () =>
      window.removeEventListener('resize', handleResize);
  }, []);

  const handleSelectQuestion = useCallback((questionId) => {
    setActiveQuestionId(questionId);
  }, []);

  // Лёгкий счётчик (poll 5с) + тяжёлый stats (30с)
  const fetchPendingCount = useCallback(async (opts = {}) => {
    const silent = opts.silent === true;
    try {
      const data = await questionsService.getUnreadCount();
      const n = data.count || 0;
      setPendingCount(n);
      // Сверка с сервером — перекрывает локальные WS-инкременты,
      // чтобы бейдж не залипал на завышенном числе
      setTabCounts((prev) => ({ ...prev, new: n }));
    } catch (err) {
      // predictability: при ошибке счётчики НЕ трогаем (иначе мигают 0)
      if (!silent) logger.error('Failed to fetch pending count:', err);
    }
  }, []);

  // Мгновенный инкремент от WS (не ждём poll)
  const bumpTabCount = useCallback((key) => {
    setTabCounts((prev) => ({
      ...prev,
      [key]: (prev[key] || 0) + 1,
    }));
    if (key === 'new') {
      setPendingCount((prev) => (prev || 0) + 1);
    }
  }, []);

  const fetchTabCounts = useCallback(async (opts = {}) => {
    const silent = opts.silent === true;
    try {
      const stats =
        await questionsService.getDashboardStats();
      setTabCounts((prev) => ({
        new:
          stats?.newQuestions ??
          stats?.pending_count ??
          prev.new,
        in_progress:
          stats?.inProgress ??
          stats?.in_progress_count ??
          prev.in_progress,
        // answered отдельно не отдаётся stats — доберём ниже
        answered: prev.answered,
      }));
      // answered: один лёгкий запрос, чтобы таб «Отвеченные» тоже имел цифру
      try {
        const answered =
          await questionsService.getQuestions({
            status: 'answered',
            limit: 1,
          });
        const total =
          answered?.total ??
          answered?.pages ??
          (Array.isArray(answered?.questions)
            ? answered.questions.length
            : Array.isArray(answered)
              ? answered.length
              : 0);
        setTabCounts((prev) => ({
          ...prev,
          answered: total,
        }));
      } catch (_) {
        // Не роняем остальные счётчики
      }
    } catch (err) {
      // predictability: при ошибке счётчики НЕ трогаем (иначе мигают 0)
      if (!silent) logger.error('Failed to fetch tab counts:', err);
    }
  }, []);

  // Бейдж во вкладке браузера: (N) Новые
  useEffect(() => {
    const total =
      (tabCounts.new || 0) + (tabCounts.in_progress || 0);
    document.title =
      total > 0
        ? `(${total}) Консультации — фармацевт`
        : 'Консультации — фармацевт';
  }, [tabCounts]);

  const triggerHaptic = useCallback((kind) => {
    try {
      const haptic =
        window.Telegram?.WebApp?.HapticFeedback;
      if (!haptic) return;
      if (kind === 'new') {
        haptic.notificationOccurred?.('success');
      } else {
        haptic.impactOccurred?.('medium');
      }
    } catch (_) {
      // ignore
    }
  }, []);

  const flashFilterTab = useCallback((key, toastText) => {
    setFlashTab(key);
    if (flashTimerRef.current) {
      clearTimeout(flashTimerRef.current);
    }
    flashTimerRef.current = setTimeout(() => {
      setFlashTab(null);
    }, 6000);
    // Тост с кнопкой перехода (без автопереключения фильтра)
    if (toastText) {
      const id = Date.now();
      setToast({
        id,
        kind: key,
        text: toastText,
        targetFilter: key,
      });
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
      toastTimerRef.current = setTimeout(() => {
        setToast((prev) =>
          prev?.id === id ? null : prev,
        );
      }, 8000);
    }
  }, []);

  // Единый интервал 15с: poll счётчиков + рефетч при возврате в WebApp.
  // Раньше «лёгкий» poll шёл каждые 5с, а «тяжёлый» каждые 30с — бейджи
  // обновлялись вразнобой (то число, то старое). Плюс «перезаход лечил»,
  // потому что свежие данные приходили только при монтировании —
  // теперь рефетч идёт сам по visibilitychange.
  useEffect(() => {
    fetchPendingCount({ silent: true });
    fetchTabCounts({ silent: true });
    const interval = setInterval(() => {
      fetchPendingCount({ silent: true });
      fetchTabCounts({ silent: true });
    }, 15000);
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        fetchPendingCount({ silent: true });
        fetchTabCounts({ silent: true });
        setListRefreshKey((k) => k + 1);
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [fetchPendingCount, fetchTabCounts]);

  // Точка соединения WS
  const [wsOnline, setWsOnline] = useState(false);
  useEffect(() => {
    const t = setInterval(() => {
      try {
        setWsOnline(
          websocketService.isConnected?.() ??
            websocketService.isConnected ??
            false,
        );
      } catch (_) {
        setWsOnline(false);
      }
    }, 3000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    websocketService.connect();
    // После (пере)подключения сразу подтягиваем счётчики — закрыть пропуски
    const t = setTimeout(() => {
      fetchPendingCount();
      fetchTabCounts();
    }, 1500);
    const unsubscribeNew = websocketService.on(
      'new_question',
      () => {
        bumpTabCount('new');
        triggerHaptic('new');
        flashFilterTab('new', 'Новый вопрос — показать');
      },
    );
    const unsubscribeUpdate = websocketService.on(
      'message_update',
      () => {
        // Продолжение диалога = «В работе»
        bumpTabCount('in_progress');
        triggerHaptic('reply');
        flashFilterTab(
          'in_progress',
          'Новый ответ в «В работе» — показать',
        );
      },
    );
    return () => {
      clearTimeout(t);
      unsubscribeNew();
      unsubscribeUpdate();
    };
  }, [
    fetchPendingCount,
    fetchTabCounts,
    bumpTabCount,
    triggerHaptic,
    flashFilterTab,
  ]);

  useEffect(
    () => () => {
      if (flashTimerRef.current) {
        clearTimeout(flashTimerRef.current);
      }
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
      document.title = 'Консультации — фармацевт';
    },
    [],
  );

  const handleBackToList = useCallback(() => {
    setActiveQuestionId(null);
  }, []);

  const handleQuestionCompleted = useCallback(() => {
    setActiveQuestionId(null);
    void selectNextPendingQuestion();
  }, [selectNextPendingQuestion]);

  useEffect(() => {
    websocketService.connect();

    const unsubscribeCompleted = websocketService.on(
      'question_completed',
      (payload) => {
        const completedQuestionId =
          payload?.question_id ||
          payload?.questionId ||
          payload?.data?.question_id ||
          payload?.data?.questionId;

        if (
          !completedQuestionId ||
          (activeQuestionIdRef.current &&
            completedQuestionId ===
              activeQuestionIdRef.current)
        ) {
          setActiveQuestionId(null);
        }

        void selectNextPendingQuestion();
      },
    );

    return () => {
      unsubscribeCompleted();
    };
  }, [selectNextPendingQuestion]);

  // Resize handlers
  const startResize = (e) => {
    e.preventDefault();
    setIsResizing(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const onResize = useCallback(
    (e) => {
      if (!isResizing) return;
      const panelRect =
        panelRef.current?.getBoundingClientRect();
      if (!panelRect) return;
      const newWidth = e.clientX - panelRect.left;
      const clamped = Math.max(
        200,
        Math.min(600, newWidth),
      );
      setPanelWidth(clamped);
    },
    [isResizing],
  );

  const stopResize = () => {
    setIsResizing(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };

  useEffect(() => {
    if (isResizing) {
      window.addEventListener('mousemove', onResize);
      window.addEventListener('mouseup', stopResize);
    }
    return () => {
      window.removeEventListener('mousemove', onResize);
      window.removeEventListener('mouseup', stopResize);
    };
  }, [isResizing, onResize]);

  // Desktop layout: side-by-side
  if (!isMobile) {
    return (
      <div className="flex h-[calc(100vh-4rem)] bg-gray-50 rounded-3xl overflow-hidden shadow-sm border border-gray-200 relative">
        {/* Left panel */}
        <div
          ref={panelRef}
          className="bg-white flex flex-col transition-all duration-200"
          style={{
            width: isPanelVisible ? panelWidth : '0px',
            minWidth: isPanelVisible ? '200px' : '0px',
            maxWidth: isPanelVisible ? '600px' : '0px',
            overflow: isPanelVisible ? 'visible' : 'hidden',
            borderRight: isPanelVisible
              ? '1px solid #e5e7eb'
              : 'none',
          }}
        >
          {isPanelVisible && (
            <>
              {/* Tabs */}
              <div className="flex border-b border-gray-200">
                <button
                  className={`flex-1 py-2.5 text-sm font-medium text-center border-b-2 transition-colors relative ${
                    activeTab === 'questions'
                      ? 'text-blue-600 border-blue-600'
                      : 'text-gray-500 border-transparent hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('questions')}
                >
                  📋 Вопросы
                  {pendingCount > 0 && (
                    <span className="absolute -top-1 -right-2 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-sky-600 rounded-full">
                      {pendingCount > 99 ? '99+' : pendingCount}
                    </span>
                  )}
                </button>
                <button
                  className={`flex-1 py-2.5 text-sm font-medium text-center border-b-2 transition-colors ${
                    activeTab === 'stats'
                      ? 'text-blue-600 border-blue-600'
                      : 'text-gray-500 border-transparent hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('stats')}
                >
                  📊 Статистика
                </button>
              </div>

              {/* Questions tab */}
              {activeTab === 'questions' && (
                <>
                  <div className="p-3 border-b border-gray-200">
                    <div className="flex gap-1 overflow-x-auto">
                      {filterOptions.map((item) => {
                        const count =
                          item.key === 'new'
                            ? tabCounts.new || pendingCount
                            : item.key === 'in_progress'
                              ? tabCounts.in_progress
                              : item.key === 'answered'
                                ? tabCounts.answered
                                : 0;
                        const isFlash = flashTab === item.key;
                        const showCount =
                          item.key !== 'all' && count > 0;
                        const badgeColor =
                          item.key === 'new'
                            ? 'bg-sky-600 text-white'
                            : item.key === 'in_progress'
                              ? 'bg-emerald-600 text-white'
                              : 'bg-slate-500 text-white';
                        return (
                          <button
                            key={item.key}
                            onClick={() => {
                              setFilter(item.key);
                              // Клик по подсвеченному табу гасит отметку
                              if (flashTab === item.key) {
                                setFlashTab(null);
                              }
                            }}
                            className={`flex items-center gap-1 whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ring-1 ${
                              filter === item.key
                                ? 'bg-blue-600 text-white ring-blue-600'
                                : isFlash
                                  ? item.key === 'new'
                                    ? 'bg-sky-50 text-sky-800 ring-sky-300'
                                    : 'bg-emerald-50 text-emerald-800 ring-emerald-300'
                                  : 'bg-gray-100 text-gray-600 ring-transparent hover:bg-gray-200'
                            }`}
                          >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                            {showCount && (
                              <span
                                className={`inline-flex items-center gap-1 justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none rounded-full ${
                                  filter === item.key
                                    ? 'bg-white text-blue-700'
                                    : badgeColor
                                }`}
                              >
                                {isFlash && (
                                  <span className="w-1.5 h-1.5 rounded-full bg-current" />
                                )}
                                {count > 99 ? '99+' : count}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    <MemoizedQuestionsList
                      filter={filter}
                      selectedQuestionId={activeQuestionId}
                      onSelectQuestion={
                        handleSelectQuestion
                      }
                      compact={true}
                      onPendingCountChange={setPendingCount}
                      refreshKey={listRefreshKey}
                    />
                  </div>
                </>
              )}

              {/* Stats tab */}
              {activeTab === 'stats' && (
                <div className="flex-1 overflow-y-auto p-4">
                  <DashboardStats compact />
                </div>
              )}
            </>
          )}
        </div>

        {/* Resize handle */}
        {isPanelVisible && (
          <div
            className="w-1 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0"
            onMouseDown={startResize}
          />
        )}

        {/* Right panel */}
        <div className="flex-1 flex flex-col bg-white min-w-0">
          {activeQuestionId ? (
            <MemoizedConsultationChat
              questionId={activeQuestionId}
              onClose={handleBackToList}
              onCompleted={handleQuestionCompleted}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <div className="text-6xl mb-4">💬</div>
                <p className="text-lg font-medium">
                  Выберите консультацию
                </p>
                <p className="text-sm mt-1">
                  Нажмите на вопрос слева, чтобы начать
                  диалог
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Тост: новый вопрос / новый ответ — без автопереключения */}
        {toast && (
          <div className="absolute bottom-4 left-4 z-30 max-w-sm">
            <div className="flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg text-sm font-medium bg-slate-800 text-white">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  toast.kind === 'new'
                    ? 'bg-sky-400'
                    : 'bg-emerald-400'
                }`}
              />
              <span className="flex-1">{toast.text}</span>
              <button
                onClick={() => {
                  setFilter(toast.targetFilter);
                  setFlashTab(null);
                  setToast(null);
                }}
                className="px-3 py-1.5 rounded-full bg-white/20 hover:bg-white/30 font-semibold whitespace-nowrap"
              >
                Показать
              </button>
              <button
                onClick={() => setToast(null)}
                className="px-2 py-1 rounded-full hover:bg-white/20"
                aria-label="Закрыть"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Mobile layout: toggle view
  if (activeQuestionId) {
    return (
      <div className="h-[calc(100vh-4rem)] bg-white">
        <div className="flex items-center gap-3 p-3 border-b border-gray-200 bg-gray-50">
          <button
            onClick={handleBackToList}
            className="p-2 rounded-full hover:bg-gray-200 transition-colors"
            aria-label="Назад к списку"
          >
            <svg
              className="w-5 h-5 text-gray-700"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <span className="font-semibold text-gray-900">
            Консультация
          </span>
        </div>
        <MemoizedConsultationChat
          questionId={activeQuestionId}
          onClose={handleBackToList}
          onCompleted={handleQuestionCompleted}
        />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] bg-white flex flex-col relative">
      {/* Header with filters */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-gray-900">
            Консультации
          </h2>
          <span
            title={wsOnline ? 'Обновления онлайн' : 'Переподключение…'}
            className={`w-2 h-2 rounded-full ${
              wsOnline ? 'bg-emerald-500' : 'bg-gray-300'
            }`}
          />
        </div>
        <div className="flex gap-1 mt-3 overflow-x-auto">
          {filterOptions.map((item) => {
            const count =
              item.key === 'new'
                ? tabCounts.new || pendingCount
                : item.key === 'in_progress'
                  ? tabCounts.in_progress
                  : item.key === 'answered'
                    ? tabCounts.answered
                    : 0;
            const isFlash = flashTab === item.key;
            const badgeColor =
              item.key === 'new'
                ? 'bg-sky-600 text-white'
                : item.key === 'in_progress'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-500 text-white';
            return (
              <button
                key={item.key}
                onClick={() => {
                  setFilter(item.key);
                  if (flashTab === item.key) {
                    setFlashTab(null);
                  }
                }}
                className={`flex items-center gap-1 whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ring-1 ${
                  filter === item.key
                    ? 'bg-blue-600 text-white ring-blue-600'
                    : isFlash
                      ? item.key === 'new'
                        ? 'bg-sky-50 text-sky-800 ring-sky-300'
                        : 'bg-emerald-50 text-emerald-800 ring-emerald-300'
                      : 'bg-gray-100 text-gray-600 ring-transparent hover:bg-gray-200'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
                {item.key !== 'all' && count > 0 && (
                  <span
                    className={`inline-flex items-center gap-1 justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none rounded-full ${
                      filter === item.key
                        ? 'bg-white text-blue-700'
                        : badgeColor
                    }`}
                  >
                    {isFlash && (
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                    )}
                    {count > 99 ? '99+' : count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Questions list */}
      <div className="flex-1 overflow-y-auto">
        <MemoizedQuestionsList
          filter={filter}
          selectedQuestionId={activeQuestionId}
          onSelectQuestion={handleSelectQuestion}
          compact={true}
          onPendingCountChange={setPendingCount}
          refreshKey={listRefreshKey}
        />
      </div>

      {/* Тост: новый вопрос / новый ответ — без автопереключения */}
      {toast && (
        <div className="absolute bottom-4 left-4 right-4 z-20">
          <div className="flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg text-sm font-medium bg-slate-800 text-white">
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${
                toast.kind === 'new'
                  ? 'bg-sky-400'
                  : 'bg-emerald-400'
              }`}
            />
            <span className="flex-1">{toast.text}</span>
            <button
              onClick={() => {
                setFilter(toast.targetFilter);
                setFlashTab(null);
                setToast(null);
              }}
              className="px-3 py-1.5 rounded-full bg-white/20 hover:bg-white/30 font-semibold whitespace-nowrap"
            >
              Показать
            </button>
            <button
              onClick={() => setToast(null)}
              className="px-2 py-1 rounded-full hover:bg-white/20"
              aria-label="Закрыть"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
