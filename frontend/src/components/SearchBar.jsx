import React, { useState } from "react";

export default function SearchBar({
  cities,
  onSearch,
  loading,
  currentCity,
  isTelegram,
}) {
  const [name, setName] = useState("");
  const [city, setCity] = useState(currentCity || "");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) {
      alert("Пожалуйста, введите название препарата");
      return;
    }
    onSearch(name, city);
  };

  return (
    <div
      className={`bg-white rounded-2xl shadow-sm border border-gray-200 ${
        isTelegram ? "p-3 mb-2" : "p-4 md:p-6 mb-4"
      }`}
    >
      <form onSubmit={handleSubmit} className="w-full">
        <div className="space-y-3 md:space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-800 mb-1 md:mb-2">
              Город
            </label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full px-3 md:px-4 py-3 md:py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 focus:border-transparent transition-all text-sm md:text-base min-h-[44px]"
              aria-describedby="city-description"
            >
              <option value="">Все города</option>
              {cities.map((cityName) => (
                <option key={cityName} value={cityName}>
                  {cityName}
                </option>
              ))}
            </select>
            <div id="city-description" className="sr-only">
              Выберите город для поиска лекарств
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-800 mb-1 md:mb-2">
              Название препарата
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: анальгин, парацетамол..."
              className="w-full px-3 md:px-4 py-3 md:py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 focus:border-transparent transition-all text-sm md:text-base min-h-[44px]"
              required
              aria-required="true"
              aria-describedby="name-description"
            />
            <div id="name-description" className="sr-only">
              Введите название лекарственного препарата для поиска
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="
                w-full bg-telegram-primary text-white font-medium py-3 md:py-4 px-4 rounded-xl
                focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2
                transition-all flex items-center justify-center text-sm md:text-base
                hover:bg-blue-600
                disabled:opacity-50 disabled:cursor-not-allowed
                shadow-md hover:shadow-lg
                min-h-[44px]
                aria-disabled={loading}
              "
              aria-label={loading ? "Выполняется поиск..." : "Найти лекарства"}
            >
              {loading ? (
                <>
                  <div
                    className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"
                    aria-hidden="true"
                  ></div>
                  <span>Поиск...</span>
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                  <span>Найти</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
