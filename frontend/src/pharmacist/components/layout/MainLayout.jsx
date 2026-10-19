import React, { useState } from 'react';
import Sidebar from './Sidebar';
import { useAuth } from '../../hooks/useAuth';

export default function MainLayout({ children }) {
  const { user } = useAuth();
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const [activeTab, setActiveTab] = useState('questions'); // 'questions' | 'stats'
  const [activeQuestionId, setActiveQuestionId] = useState(null);

  const togglePanel = () => setIsPanelVisible(!isPanelVisible);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* На мобильных — обычная вертикальная раскладка (без фикс. высоты, чтобы
          адресная панель браузера и прокрутка страницы работали корректно).
          На десктопе — классический flex со сайдбаром и прокруткой контента. */}
      <div className="flex flex-col lg:flex-row lg:h-screen lg:overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content */}
        <main className="flex-1 lg:overflow-y-auto pt-14 lg:pt-0">
          {/* Header with panel toggle button */}
          <header className="bg-white border-b border-gray-200 px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-3 flex-wrap min-w-0">
              {/* Panel toggle button - always on the left */}
              <button
                onClick={togglePanel}
                className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
                title="Скрыть/показать список"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900 min-w-0">
                Привет, {user?.user?.first_name || user?.name || 'Фармацевт'} 👋
              </h1>
              <span
                className={`flex items-center gap-1 text-sm ${
                  user?.is_online ? 'text-green-600' : 'text-gray-400'
                }`}
              >
                {user?.is_online ? '🟢 Онлайн' : '⚫ Офлайн'}
              </span>
              <span className="hidden sm:inline text-sm text-gray-400">|</span>
              <span className="hidden sm:inline text-sm text-gray-600">
                {user?.pharmacy_info?.name || 'Аптека'}
              </span>
            </div>
            <div className="hidden md:flex items-center gap-3">
              <span className="text-sm text-gray-500">
                📅 {new Date().toLocaleDateString('ru-RU')}
              </span>
            </div>
          </header>

          {/* Content with props passed to children */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
            {React.cloneElement(
              children,
              {
                isPanelVisible,
                togglePanel,
                activeTab,
                setActiveTab,
                activeQuestionId,
                setActiveQuestionId,
              }
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
