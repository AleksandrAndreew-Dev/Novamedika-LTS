import React, { useState } from 'react';
import Sidebar from './Sidebar';
import { useAuth } from '../../hooks/useAuth';

export default function MainLayout({ children }) {
  const { user } = useAuth();
  const [isPanelVisible, setIsPanelVisible] = useState(true);

  const togglePanel = () => setIsPanelVisible(!isPanelVisible);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content */}
        <main className="flex-1 overflow-y-auto pt-16 lg:pt-0">
          {/* Header with panel toggle button */}
          <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
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
              <h1 className="text-xl font-bold text-gray-900">
                Привет, {user?.user?.first_name || user?.name || 'Фармацевт'} 👋
              </h1>
              <span className={`flex items-center gap-1 text-sm ${user?.is_online ? 'text-green-600' : 'text-gray-400'}`}>
                {user?.is_online ? '🟢 Онлайн' : '⚫ Офлайн'}
              </span>
              <span className="text-sm text-gray-400">|</span>
              <span className="text-sm text-gray-600">
                {user?.pharmacy_info?.name || 'Аптека'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                📅 {new Date().toLocaleDateString('ru-RU')}
              </span>
            </div>
          </header>

          {/* Content with props passed to children */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {React.cloneElement(children, { isPanelVisible, togglePanel })}
          </div>
        </main>
      </div>
    </div>
  );
}
