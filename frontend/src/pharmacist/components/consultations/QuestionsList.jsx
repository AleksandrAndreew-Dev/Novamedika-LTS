import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react'
import { questionsService } from '../../services/questionsService'
import websocketService from '../../services/websocketService'

const filterLabels = {
  all: 'Все',
  new: 'Новые',
  in_progress: 'В работе',
  completed: 'Завершенные',
}

export default function QuestionsList({
  filter = 'all',
  selectedQuestionId,
  onSelectQuestion,
  compact = false,
}) {
  const [
    unreadQuestions,
    setUnreadQuestions,
  ] = useState(
    new Set(
      JSON.parse(
        localStorage.getItem(
          'unread_questions',
        ) || '[]',
      ),
    ),
  )
  const [
    questions,
    setQuestions,
  ] = useState([])
  const [
    loading,
    setLoading,
  ] = useState(true)
  const mountedRef =
    useRef(true)
  const lastLoadRef =
    useRef(0)
  const loadThrottleMs = 2000

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    console.log(
      '[QuestionsList] Component mounted with filter:',
      filter,
    )
  }, [filter])

  const loadQuestions =
    useCallback(async () => {
      // Throttle: skip if called within 2s
      const now = Date.now()
      if (
        now -
          lastLoadRef.current <
        loadThrottleMs
      ) {
        console.log(
          '[QuestionsList] Throttled loadQuestions',
        )
        return
      }
      lastLoadRef.current =
        now

      try {
        setLoading(true)
        const params =
          filter === 'all'
            ? {}
            : {
                status:
                  filter,
              }
        const data =
          await questionsService.getQuestions(
            params,
          )

        if (
          !mountedRef.current
        )
          return

        // Backend returns { questions: [...], total, page, limit, pages }
        if (
          Array.isArray(data)
        ) {
          setQuestions(data)
        } else if (
          data &&
          Array.isArray(
            data.questions,
          )
        ) {
          setQuestions(
            data.questions,
          )
        } else {
          console.error(
            '[QuestionsList] Unexpected response format:',
            typeof data,
            data,
          )
          setQuestions([])
        }
      } catch (error) {
        if (
          !mountedRef.current
        )
          return
        console.error(
          '[QuestionsList] Failed to load questions:',
          error,
        )
        setQuestions([])
      } finally {
        if (
          mountedRef.current
        )
          setLoading(false)
      }
    }, [filter])

  // Subscribe to WebSocket for real-time new question notifications
  useEffect(() => {
    websocketService.connect()

    const unsubscribeNew =
      websocketService.on(
        'new_question',
        () => {
          loadQuestions()
        },
      )

    const unsubscribeUpdate =
      websocketService.on(
        'message_update',
        () => {
          loadQuestions()
        },
      )

    const unsubscribeAssigned =
      websocketService.on(
        'question_assigned',
        () => {
          loadQuestions()
        },
      )

    return () => {
      unsubscribeNew()
      unsubscribeUpdate()
      unsubscribeAssigned()
    }
  }, [loadQuestions])

  useEffect(() => {
    loadQuestions()
  }, [loadQuestions])

  const getStatusBadge = (
    status,
  ) => {
    const badges = {
      new: {
        text: 'Новый',
        color:
          'bg-blue-100 text-blue-800',
      },
      in_progress: {
        text: 'В работе',
        color:
          'bg-yellow-100 text-yellow-800',
      },
      completed: {
        text: 'Завершен',
        color:
          'bg-green-100 text-green-800',
      },
    }
    const badge =
      badges[status] ||
      badges.new
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}
      >
        {badge.text}
      </span>
    )
  }

  const handleQuestionClick =
    (questionId) => {
      if (onSelectQuestion) {
        onSelectQuestion(
          questionId,
        )
      }
    }

  // Compact mode: simpler card layout for sidebar
  if (compact) {
    if (loading) {
      return (
        <div className="space-y-2 p-4">
          {[...Array(5)].map(
            (_, i) => (
              <div
                key={i}
                className="h-16 bg-gray-100 rounded-xl animate-pulse"
              ></div>
            ),
          )}
        </div>
      )
    }

    return (
      <div className="divide-y divide-gray-100">
        {questions.length ===
        0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            Нет консультаций
          </div>
        ) : (
          questions.map(
            (question) => {
              const questionId =
                question.uuid ||
                question.id
              const isSelected =
                questionId ===
                selectedQuestionId
              const isUnread =
                question.status ===
                  'pending' ||
                unreadQuestions.has(
                  questionId,
                )

              return (
                <button
                  key={
                    questionId
                  }
                  type="button"
                  onClick={() =>
                    handleQuestionClick(
                      questionId,
                    )
                  }
                  className={`w-full text-left px-4 py-3 transition-colors hover:bg-gray-50 ${
                    isSelected
                      ? 'bg-blue-50 border-l-4 border-blue-500'
                      : 'border-l-4 border-transparent'
                  }`}
                >
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
                          {question.text ||
                            'Без названия'}
                        </p>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {question.created_at
                          ? new Date(
                              question.created_at,
                            ).toLocaleDateString(
                              'ru-RU',
                              {
                                hour: '2-digit',
                                minute:
                                  '2-digit',
                              },
                            )
                          : ''}
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      {getStatusBadge(
                        question.status,
                      )}
                    </div>
                  </div>
                </button>
              )
            },
          )
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map(
          (_, i) => (
            <div
              key={i}
              className="bg-white rounded-3xl shadow-sm p-6 animate-pulse"
            >
              <div className="h-4 bg-gray-200 rounded mb-3"></div>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          ),
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">
            Список вопросов
          </h2>
          <p className="mt-1 text-gray-600">
            Фильтр:{' '}
            {filterLabels[
              filter
            ] || 'Все'}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {questions.length ===
        0 ? (
          <div className="bg-white rounded-3xl shadow-sm p-8 text-center">
            <p className="text-gray-500">
              Нет консультаций
              по выбранному
              фильтру.
            </p>
          </div>
        ) : (
          questions.map(
            (question) => {
              const questionId =
                question.uuid ||
                question.id
              const isSelected =
                questionId ===
                selectedQuestionId

              return (
                <button
                  key={
                    questionId
                  }
                  type="button"
                  onClick={() =>
                    handleQuestionClick(
                      questionId,
                    )
                  }
                  className={`w-full text-left rounded-3xl border p-6 shadow-sm transition-all ${
                    isSelected
                      ? 'border-blue-300 bg-blue-50 shadow-lg'
                      : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
                  }`}
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {question.title ||
                          question.text ||
                          'Без названия'}
                      </h3>
                      <p className="mt-2 text-gray-600 text-sm line-clamp-2">
                        {question.question ||
                          question.text}
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2 text-sm text-gray-500">
                        <span>
                          📅{' '}
                          {question.created_at
                            ? new Date(
                                question.created_at,
                              ).toLocaleDateString(
                                'ru-RU',
                              )
                            : 'N/A'}
                        </span>
                        <span>
                          👤
                          Пользователь
                          #
                          {question.user_id ||
                            question
                              .user
                              ?.telegram_id ||
                            'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-3 sm:items-end">
                      {getStatusBadge(
                        question.status,
                      )}
                      <span className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white">
                        Ответить
                      </span>
                    </div>
                  </div>
                  {question.answer && (
                    <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-600">
                      <strong>
                        Ответ:
                      </strong>{' '}
                      {
                        question.answer
                      }
                    </div>
                  )}
                </button>
              )
            },
          )
        )}
      </div>
    </div>
  )
}
