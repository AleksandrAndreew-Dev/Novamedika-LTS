import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react'
import QuestionsList from './QuestionsList'
import ConsultationChat from './ConsultationChat'
import { questionsService } from '../../services/questionsService'

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
]

export default function ChatDashboard() {
  const [filter, setFilter] =
    useState('new')
  const [
    activeQuestionId,
    setActiveQuestionId,
  ] = useState(null)
  const [
    isMobile,
    setIsMobile,
  ] = useState(
    window.innerWidth < 768,
  )
  const autoSelectDoneRef =
    useRef(false)

  // Auto-select first new question on mount
  useEffect(() => {
    if (
      autoSelectDoneRef.current
    )
      return
    autoSelectDoneRef.current = true

    const autoSelectFirst =
      async () => {
        try {
          const data =
            await questionsService.getQuestions(
              {
                status:
                  'pending',
              },
            )
          const questions =
            data?.questions ||
            data ||
            []
          if (
            questions.length >
            0
          ) {
            const firstId =
              questions[0]
                .uuid ||
              questions[0].id
            if (firstId) {
              setActiveQuestionId(
                firstId,
              )
            }
          }
        } catch (_e) {
          // Silently fail — user can select manually
        }
      }

    autoSelectFirst()
  }, [])

  useEffect(() => {
    const handleResize = () =>
      setIsMobile(
        window.innerWidth <
          768,
      )
    window.addEventListener(
      'resize',
      handleResize,
    )
    return () =>
      window.removeEventListener(
        'resize',
        handleResize,
      )
  }, [])

  const handleSelectQuestion =
    useCallback(
      (questionId) => {
        setActiveQuestionId(
          questionId,
        )
      },
      [],
    )

  // Reset active question when filter changes (question may not be in new filter)
  useEffect(() => {
    setActiveQuestionId(null)
  }, [filter])

  const handleBackToList =
    useCallback(() => {
      setActiveQuestionId(
        null,
      )
    }, [])

  // Desktop layout: side-by-side
  if (!isMobile) {
    return (
      <div className="flex h-[calc(100vh-4rem)] bg-gray-50 rounded-3xl overflow-hidden shadow-sm border border-gray-200">
        {/* Left panel */}
        <div className="w-[380px] min-w-[320px] border-r border-gray-200 bg-white flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">
              Консультации
            </h2>
            <div className="flex gap-1 mt-3 overflow-x-auto">
              {filterOptions.map(
                (item) => (
                  <button
                    key={
                      item.key
                    }
                    onClick={() =>
                      setFilter(
                        item.key,
                      )
                    }
                    className={`flex items-center gap-1 whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      filter ===
                      item.key
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    <span>
                      {
                        item.icon
                      }
                    </span>
                    <span>
                      {
                        item.label
                      }
                    </span>
                  </button>
                ),
              )}
            </div>
          </div>

          {/* Scrollable list */}
          <div className="flex-1 overflow-y-auto">
            <QuestionsList
              filter={filter}
              selectedQuestionId={
                activeQuestionId
              }
              onSelectQuestion={
                handleSelectQuestion
              }
              compact={true}
            />
          </div>
        </div>

        {/* Right panel */}
        <div className="flex-1 flex flex-col bg-white">
          {activeQuestionId ? (
            <ConsultationChat
              questionId={
                activeQuestionId
              }
              onClose={
                handleBackToList
              }
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <div className="text-6xl mb-4">
                  💬
                </div>
                <p className="text-lg font-medium">
                  Выберите
                  консультацию
                </p>
                <p className="text-sm mt-1">
                  Нажмите на
                  вопрос
                  слева, чтобы
                  начать
                  диалог
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Mobile layout: toggle view
  if (activeQuestionId) {
    return (
      <div className="h-[calc(100vh-4rem)] bg-white">
        <div className="flex items-center gap-3 p-3 border-b border-gray-200 bg-gray-50">
          <button
            onClick={
              handleBackToList
            }
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
                strokeWidth={
                  2
                }
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <span className="font-semibold text-gray-900">
            Консультация
          </span>
        </div>
        <ConsultationChat
          questionId={
            activeQuestionId
          }
          onClose={
            handleBackToList
          }
        />
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] bg-white flex flex-col">
      {/* Header with filters */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-900">
          Консультации
        </h2>
        <div className="flex gap-1 mt-3 overflow-x-auto">
          {filterOptions.map(
            (item) => (
              <button
                key={item.key}
                onClick={() =>
                  setFilter(
                    item.key,
                  )
                }
                className={`flex items-center gap-1 whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  filter ===
                  item.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <span>
                  {item.icon}
                </span>
                <span>
                  {item.label}
                </span>
              </button>
            ),
          )}
        </div>
      </div>

      {/* Questions list */}
      <div className="flex-1 overflow-y-auto">
        <QuestionsList
          filter={filter}
          selectedQuestionId={
            activeQuestionId
          }
          onSelectQuestion={
            handleSelectQuestion
          }
          compact={true}
        />
      </div>
    </div>
  )
}
