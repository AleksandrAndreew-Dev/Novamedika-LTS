import React from "react";

export default function SearchResultsHeader({
  searchData,
  loading,
  onBackToForms,
  onNewSearch,
}) {
  return (
    <div className="border-b border-telegram-border px-4 md:px-6 py-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-gray-900 tracking-wide leading-relaxed">
            Результаты поиска
          </h2>
          <p className="text-gray-800 mt-1 text-sm md:text-base">
            {searchData.name}
            {searchData.form && ` • ${searchData.form}`}
            {searchData.manufacturer && ` • ${searchData.manufacturer}`}
            {searchData.city && ` • ${searchData.city}`}
          </p>
        </div>

        <div className="flex gap-2 w-full sm:w-auto">
          <ActionButton
            onClick={onBackToForms}
            disabled={loading}
            className="bg-gray-100 hover:bg-gray-200 text-gray-800"
            icon="back"
            label="Изменить форму"
          />

          <ActionButton
            onClick={onNewSearch}
            disabled={loading}
            className="bg-telegram-primary text-gray-900 hover:bg-blue-600 hover:text-gray-900"
            icon="search"
            label="Новый поиск"
          />
        </div>
      </div>
    </div>
  );
}

function ActionButton({ onClick, disabled, className, icon, label }) {
  const getIcon = () => {
    switch (icon) {
      case "back":
        return (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        );
      case "search":
        return (
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        );
      default:
        return null;
    }
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex-1 sm:flex-none font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 ${className}`}
      aria-label={label}
    >
      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        {getIcon()}
      </svg>
      {label}
    </button>
  );
}
