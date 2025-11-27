import React from "react";

export default function EmptyResults({ onBackToForms, onNewSearch }) {
  return (
    <div className="text-center py-12" role="status">
      <div className="text-gray-600 mb-4">
        <svg className="w-16 h-16 md:w-20 md:h-20 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        В выбранной аптеке нет этого препарата
      </h3>
      <p className="text-gray-800 text-sm mb-6">
        Попробуйте выбрать другую форму или изменить параметры поиска
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={onBackToForms}
          className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
        >
          Выбрать другую форму
        </button>
        <button
          onClick={onNewSearch}
          className="bg-gray-100 text-gray-800 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
        >
          Новый поиск
        </button>
      </div>
    </div>
  );
}
