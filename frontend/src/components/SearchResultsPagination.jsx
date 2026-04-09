import React from "react";

export default function SearchResultsPagination({ pagination, onPageChange, loading }) {
  if (pagination.totalPages <= 1) return null;

  return (
    <div className="flex justify-center items-center mt-8 space-x-2" role="navigation" aria-label="Навигация по страницам">
      <button
        onClick={() => onPageChange(pagination.page - 1)}
        disabled={pagination.page === 1 || loading}
        className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
        aria-label="Предыдущая страница"
      >
        <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Назад
      </button>

      <div className="bg-white border border-gray-300 rounded-lg px-4 py-3 flex items-center min-h-[44px]">
        <span className="text-sm text-gray-800 font-medium">
          Страница {pagination.page} из {pagination.totalPages}
        </span>
      </div>

      <button
        onClick={() => onPageChange(pagination.page + 1)}
        disabled={pagination.page === pagination.totalPages || loading}
        className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
        aria-label="Следующая страница"
      >
        Вперед
        <svg className="w-5 h-5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}
