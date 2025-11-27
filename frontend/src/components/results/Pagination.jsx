import React from "react";

export default function Pagination({ pagination, loading, onPageChange }) {
  if (pagination.totalPages <= 1) return null;

  return (
    <div className="flex justify-center items-center mt-8 space-x-2" role="navigation" aria-label="Навигация по страницам">
      <PaginationButton
        direction="prev"
        disabled={pagination.page === 1 || loading}
        onClick={() => onPageChange(pagination.page - 1)}
      />

      <PageInfo page={pagination.page} totalPages={pagination.totalPages} />

      <PaginationButton
        direction="next"
        disabled={pagination.page === pagination.totalPages || loading}
        onClick={() => onPageChange(pagination.page + 1)}
      />
    </div>
  );
}

function PaginationButton({ direction, disabled, onClick }) {
  const isPrev = direction === "prev";
  const label = isPrev ? "Предыдущая страница" : "Следующая страница";
  const text = isPrev ? "Назад" : "Вперед";

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
      aria-label={label}
    >
      {isPrev && <ArrowIcon direction="left" />}
      {text}
      {!isPrev && <ArrowIcon direction="right" />}
    </button>
  );
}

function ArrowIcon({ direction }) {
  const path = direction === "left"
    ? "M15 19l-7-7 7-7"
    : "M9 5l7 7-7 7";

  return (
    <svg className={`w-5 h-5 ${direction === "left" ? "mr-1" : "ml-1"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
    </svg>
  );
}

function PageInfo({ page, totalPages }) {
  return (
    <div className="bg-white border border-gray-300 rounded-lg px-4 py-3 flex items-center min-h-[44px]">
      <span className="text-sm text-gray-800 font-medium">
        Страница {page} из {totalPages}
      </span>
    </div>
  );
}
