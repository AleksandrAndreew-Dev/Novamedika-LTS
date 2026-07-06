import React from 'react'
import { useAuth } from './hooks/useAuth'
import ChatDashboard from './components/consultations/ChatDashboard'
import MainLayout from './components/layout/MainLayout'

export default function PharmacistContent({
  isPanelVisible,
  togglePanel,
}) {
  const {
    isAuthenticated,
    user,
    loading,
  } = useAuth()

  if (
    !loading &&
    !isAuthenticated
  ) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">
            Требуется
            авторизация.
            Перенаправление...
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            Загрузка панели...
          </p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
            <svg
              className="h-8 w-8 text-yellow-600"
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
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <p className="text-gray-600">
            Ошибка загрузки
            данных
            пользователя
          </p>
          <button
            onClick={() =>
              window.location.reload()
            }
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Обновить страницу
          </button>
        </div>
      </div>
    )
  }

  return (
    <MainLayout>
      <ChatDashboard
        isPanelVisible={
          isPanelVisible
        }
        togglePanel={
          togglePanel
        }
      />
    </MainLayout>
  )
}
