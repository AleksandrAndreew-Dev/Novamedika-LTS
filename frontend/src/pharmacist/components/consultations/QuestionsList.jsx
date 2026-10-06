import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';
import { questionsService } from '../../services/questionsService';
import websocketService from '../../services/websocketService';

const filterLabels = {
  all: 'Все',
  new: 'Новые',
  answered: 'Отвеченные',
  in_progress: 'В работе',
  completed: 'Завершенные',
};

export default function QuestionsList({
  filter = 'all',
  selectedQuestionId,
  onSelectQuestion,
  compact = false,
  onPendingCountChange,
  refreshKey = 0,
}) {
  const [unreadQuestions] = useState(
    new Set(
      JSON.parse(
        localStorage.getItem('unread_questions') || '[]',
      ),
    ),
  );
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [hasNewQuestions, setHasNewQuestions] =
    useState(false);
  // Подсветка конкретных карточек: Map<questionId, { ts, kind: 'new' | 'reply' }>
  const [highlightIds, setHighlightIds] = useState(
    () => new Map(),
  );
  const [searchQuery, setSearchQuery] = useState('');
  const newQuestionsTimerRef = useRef(null);
  const mountedRef = useRef(true);
  const lastLoadRef = useRef(0);
  const requestIdRef = useRef(0);
  const questionsRef = useRef([]);
  const filterRef = useRef(filter);
  const loadThrottleMs = 2000;

  useEffect(() => {
    filterRef.current = filter;
  }, [filter]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Suppress noisy logs in production
  const debugLog = React.useMemo(
    () => (import.meta.env?.DEV ? console.log : () => {}),
    [],
  );

  const loadQuestions = useCallback(
    async (opts = {}) => {
      const force = opts.force === true;
      // Throttle — только для обычных вызовов; WS-события идут с force
      const now = Date.now();
      if (
        !force &&
        now - lastLoadRef.current < loadThrottleMs &&
        lastLoadRef.current > 0
      ) {
        debugLog('[QuestionsList] Throttled loadQuestions');
        return;
      }
      lastLoadRef.current = now;

      // Предсказуемое поведение: при смене фильтра показываем индикатор,
      // но НЕ очищаем старый список (нет «пустого» мигания).
      // Скелетон — только при первой загрузке, далее — тихий рефетч.
      const isFirstLoad = questionsRef.current.length === 0;
      if (isFirstLoad) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setLoadError(null);
      const requestId = ++requestIdRef.current;

      try {
        const params =
          filter === 'all'
            ? {}
            : {
                status: filter,
              };
        if (searchQuery.trim()) {
          params.search = searchQuery.trim();
        }
        // Пробрасываем внешний refreshKey (кнопка «Обновить» / смена таба сверху)
        if (opts.refreshKey !== undefined) {
          params._rk = opts.refreshKey;
        }
        const data =
          await questionsService.getQuestions(params);

        if (!mountedRef.current) return;
        // Отбрасываем устаревшие ответы (гонка filter A -> filter B)
        if (requestId !== requestIdRef.current) return;

        // Backend returns { questions: [...], total, page, limit, pages }
        if (Array.isArray(data)) {
          setQuestions(data);
          questionsRef.current = data;
        } else if (data && Array.isArray(data.questions)) {
          setQuestions(data.questions);
          questionsRef.current = data.questions;
        } else {
          debugLog(
            '[QuestionsList] Unexpected response format:',
            typeof data,
            data,
          );
          setQuestions([]);
          questionsRef.current = [];
        }
      } catch (error) {
        if (!mountedRef.current) return;
        if (requestId !== requestIdRef.current) return;
        debugLog(
          '[QuestionsList] Failed to load questions:',
          error,
        );
        // При ошибке список НЕ затираем — показываем баннер с ретраем
        setLoadError(error);
      } finally {
        if (mountedRef.current && requestId === requestIdRef.current) {
          setLoading(false);
          setRefreshing(false);
          lastLoadRef.current = Date.now();
        }
      }
    },
    [filter, searchQuery, debugLog],
  );

  const extractQuestionId = (payload) => {
    if (!payload || typeof payload !== 'object')
      return null;
    const inner = payload?.data || payload;
    return (
      payload?.question_id ||
      payload?.questionId ||
      inner?.question_id ||
      inner?.questionId ||
      inner?.uuid ||
      payload?.uuid ||
      null
    );
  };

  const markHighlight = useCallback((questionId, kind) => {
    if (!questionId) return;
    const ts = Date.now();
    setHighlightIds((prev) => {
      const next = new Map(prev);
      next.set(String(questionId), { ts, kind });
      return next;
    });
    // Спокойная подсветка 60с, без мигания
    setTimeout(() => {
      setHighlightIds((prev) => {
        const cur = prev.get(String(questionId));
        if (!cur || cur.ts !== ts) return prev;
        const next = new Map(prev);
        next.delete(String(questionId));
        return next;
      });
    }, 60000);
  }, []);

  const formatHlTime = (ts) => {
    try {
      return new Date(ts).toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return '';
    }
  };

  // Subscribe to WebSocket once (стабильно, без переподписок при смене фильтра).
  // Актуальный фильтр читаем через filterRef — иначе при каждом клике по табу
  // эффект пересоздавал 4 подписки и мог пропускать/дублировать события.
  useEffect(() => {
    websocketService.connect();

    const unsubscribeNew = websocketService.on(
      'new_question',
      (payload) => {
        debugLog(
          '[QuestionsList] New question received via WebSocket',
        );
        // Тихий общий флаг (без пульса всего списка)
        setHasNewQuestions(true);
        if (newQuestionsTimerRef.current) {
          clearTimeout(newQuestionsTimerRef.current);
        }
        newQuestionsTimerRef.current = setTimeout(() => {
          setHasNewQuestions(false);
        }, 5000);
        // Подсветить конкретную карточку (новый вопрос)
        const qid = extractQuestionId(payload);
        if (!qid && import.meta.env?.DEV) {
          debugLog(
            '[QuestionsList] new_question without id:',
            payload,
          );
        }
        markHighlight(qid, 'new');
        // Notify parent about pending count change
        if (typeof onPendingCountChange === 'function') {
          onPendingCountChange((prev) => (prev || 0) + 1);
        }
        // WS-событие всегда force — throttle не должен съедать показ
        const f = filterRef.current;
        if (f === 'new' || f === 'all') {
          loadQuestions({ force: true });
        }
      },
    );

    const unsubscribeUpdate = websocketService.on(
      'message_update',
      (payload) => {
        debugLog(
          '[QuestionsList] Message update received via WebSocket',
        );
        // Подсветить конкретную карточку (продолжение в «В работе»)
        const qid = extractQuestionId(payload);
        if (!qid && import.meta.env?.DEV) {
          debugLog(
            '[QuestionsList] message_update without id:',
            payload,
          );
        }
        markHighlight(qid, 'reply');
        const f = filterRef.current;
        if (f === 'in_progress' || f === 'all') {
          loadQuestions({ force: true });
        }
      },
    );

    const unsubscribeAssigned = websocketService.on(
      'question_assigned',
      () => {
        debugLog(
          '[QuestionsList] Question assigned received via WebSocket',
        );
        loadQuestions({ force: true });
      },
    );

    const unsubscribeCompleted = websocketService.on(
      'question_completed',
      () => {
        debugLog(
          '[QuestionsList] Question completed received via WebSocket',
        );
        loadQuestions({ force: true });
      },
    );

    return () => {
      unsubscribeNew();
      unsubscribeUpdate();
      unsubscribeAssigned();
      unsubscribeCompleted();
      if (newQuestionsTimerRef.current) {
        clearTimeout(newQuestionsTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Первичная загрузка + смена фильтра/поиска/refreshKey.
  // Смена фильтра идёт с force (throttle её НЕ блокирует — иначе таб
  // периодически показывал пустой/старый список).
  // Поиск дебаунсим 400мс, чтобы не дёргать API на каждую букву.
  useEffect(() => {
    lastLoadRef.current = 0;
    if (searchQuery.trim()) {
      const t = setTimeout(() => {
        loadQuestions({ force: true, refreshKey });
      }, 400);
      return () => clearTimeout(t);
    }
    loadQuestions({ force: true, refreshKey });
  }, [loadQuestions, filter, searchQuery, refreshKey]);

  // Фоновый поллинг каждые 30с (без мигания — тихий рефетч).
  // Первичную загрузку делает эффект выше; здесь только интервал,
  // иначе при монтировании уходят 2 параллельных запроса и побеждает
  // устаревший ответ (пустой список).
  useEffect(() => {
    const interval = setInterval(() => {
      loadQuestions({ force: true });
    }, 30000);
    return () => clearInterval(interval);
  }, [loadQuestions]);

  const getStatusBadge = (status) => {
    // Единый map статусов (как в ConsultationChat)
    const badges = {
      pending: {
        text: 'Ожидает ответа',
        color: 'bg-yellow-100 text-yellow-800',
      },
      new: {
        text: 'Ожидает ответа',
        color: 'bg-yellow-100 text-yellow-800',
      },
      in_progress: {
        text: 'В работе',
        color: 'bg-blue-100 text-blue-800',
      },
      answered: {
        text: 'Есть ответ',
        color: 'bg-green-100 text-green-800',
      },
      completed: {
        text: 'Завершен',
        color: 'bg-gray-100 text-gray-800',
      },
    };
    const badge = badges[status] || badges.pending;
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}
      >
        {badge.text}
      </span>
    );
  };

  const handleQuestionClick = (questionId) => {
    if (onSelectQuestion) {
      onSelectQuestion(questionId);
    }
  };

  // Compact mode: simpler card layout for sidebar
  if (compact) {
    // Скелетон — только пока список ни разу не загружен.
    // Иначе при смене таба был «пустой миг» вместо старых данных.
    if (loading && questions.length === 0) {
      return (
        <div className="space-y-2 p-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-16 bg-gray-100 rounded-xl animate-pulse"
            ></div>
          ))}
        </div>
      );
    }

    return (
      <div className="divide-y divide-gray-100">
        {loadError && questions.length > 0 && (
          <div className="m-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2">
            <span className="flex-1">
              Не удалось обновить список. Показаны сохранённые данные.
            </span>
            <button
              type="button"
              onClick={() => loadQuestions({ force: true })}
              className="px-2.5 py-1 rounded-full bg-amber-600 text-white font-semibold hover:bg-amber-700"
            >
              Повторить
            </button>
          </div>
        )}
        {refreshing && (
          <div className="px-4 py-1.5 text-[11px] text-gray-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            Обновление…
          </div>
        )}
        {questions.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            {loadError ? (
              <>
                <p className="mb-2">Не удалось загрузить список.</p>
                <button
                  type="button"
                  onClick={() => loadQuestions({ force: true })}
                  className="px-3 py-1.5 rounded-full bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700"
                >
                  Повторить
                </button>
              </>
            ) : searchQuery ? (
              'Ничего не найдено'
            ) : (
              'Нет консультаций'
            )}
          </div>
        ) : (
          questions.map((question) => {
            const questionId = question.uuid || question.id;
            const isSelected =
              questionId === selectedQuestionId;
            const isUnread =
              question.status === 'pending' ||
              unreadQuestions.has(questionId);
            const hl = highlightIds.get(String(questionId));
            const isHlNew = hl?.kind === 'new';
            const isHlReply = hl?.kind === 'reply';

            return (
              <button
                key={questionId}
                type="button"
                onClick={() =>
                  handleQuestionClick(questionId)
                }
                className={`w-full text-left px-4 py-3 transition-colors hover:bg-gray-50 relative ring-1 ring-inset ${
                  isSelected
                    ? 'bg-blue-50 ring-blue-200 border-l-4 border-blue-500'
                    : isHlNew
                      ? 'bg-sky-50 ring-sky-200 border-l-4 border-sky-400'
                      : isHlReply
                        ? 'bg-emerald-50 ring-emerald-200 border-l-4 border-emerald-400'
                        : 'border-l-4 border-transparent ring-transparent'
                }`}
              >
                {hl && (
                  <span
                    className={`inline-flex items-center gap-1 mb-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      isHlNew
                        ? 'bg-sky-600 text-white'
                        : 'bg-emerald-600 text-white'
                    }`}
                  >
                    {isHlNew
                      ? `Новый • ${formatHlTime(hl.ts)}`
                      : `Новый ответ • ${formatHlTime(hl.ts)}`}
                  </span>
                )}
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {isUnread && (
                        <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"></span>
                      )}
                      <p
                        className={`text-sm truncate ${
                          isUnread
                            ? 'font-semibold text-gray-900'
                            : 'text-gray-700'
                        }`}
                      >
                        {question.text || 'Без названия'}
                      </p>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {question.created_at
                        ? new Date(
                            question.created_at,
                          ).toLocaleDateString('ru-RU', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    {getStatusBadge(question.status)}
                  </div>
                </div>
                {hasNewQuestions && (
                  <span className="absolute top-2 right-2 inline-flex items-center justify-center w-2 h-2 rounded-full bg-sky-500" />
                )}
              </button>
            );
          })
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-3xl shadow-sm p-6 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded mb-3"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-semibold text-gray-900">
              Список вопросов
            </h2>
            {hasNewQuestions && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
                Новые
              </span>
            )}
          </div>
          <p className="mt-1 text-gray-600">
            Фильтр: {filterLabels[filter] || 'Все'}
          </p>
        </div>
      </div>

      {/* Search input */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Поиск по вопросам..."
          className="w-full px-4 py-2 pl-10 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
        />
        <svg
          className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      <div className="space-y-4">
        {questions.length === 0 ? (
          <div className="bg-white rounded-3xl shadow-sm p-8 text-center">
            <p className="text-gray-500">
              {searchQuery
                ? 'Ничего не найдено по вашему запросу.'
                : 'Нет консультаций по выбранному фильтру.'}
            </p>
          </div>
        ) : (
          questions.map((question) => {
            const questionId = question.uuid || question.id;
            const isSelected =
              questionId === selectedQuestionId;
            // Заголовок показываем только если он реально отличается
            // от текста вопроса (иначе текст дублировался в карточке)
            const hasSeparateTitle =
              Boolean(question.title) &&
              question.title !== question.text;
            const bodyText =
              question.question || question.text || 'Без названия';

            return (
              <button
                key={questionId}
                type="button"
                onClick={() =>
                  handleQuestionClick(questionId)
                }
                className={`w-full text-left rounded-3xl border p-6 shadow-sm transition-all ${
                  isSelected
                    ? 'border-blue-300 bg-blue-50 shadow-lg'
                    : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
                }`}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    {hasSeparateTitle && (
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {question.title}
                      </h3>
                    )}
                    <p
                      className={`line-clamp-2 ${
                        hasSeparateTitle
                          ? 'mt-2 text-gray-600 text-sm'
                          : 'text-lg font-semibold text-gray-900'
                      }`}
                    >
                      {bodyText}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2 text-sm text-gray-500">
                      <span>
                        📅{' '}
                        {question.created_at
                          ? new Date(
                              question.created_at,
                            ).toLocaleDateString('ru-RU')
                          : 'N/A'}
                      </span>
                      <span>
                        👤 Пользователь #
                        {question.user_id ||
                          question.user?.telegram_id ||
                          'N/A'}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-start gap-3 sm:items-end">
                    {getStatusBadge(question.status)}
                    <span className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white">
                      Ответить
                    </span>
                  </div>
                </div>
                {question.answer && (
                  <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-600">
                    <strong>Ответ:</strong>{' '}
                    {question.answer}
                  </div>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
