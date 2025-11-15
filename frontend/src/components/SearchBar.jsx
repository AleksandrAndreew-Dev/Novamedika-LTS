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
      className={`bg-white rounded-2xl shadow-sm border border-telegram-border ${
        isTelegram ? "p-4 mb-2" : "p-6 mb-6"
      }`}
    >
      <form onSubmit={handleSubmit} className="w-full">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Город
            </label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent transition-all text-base"
            >
              <option value="">Все города</option>
              {cities.map((cityName) => (
                <option key={cityName} value={cityName}>
                  {cityName}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Название препарата *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: анальгин, парацетамол..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent transition-all text-base"
              required
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="
    w-full bg-telegram-primary text-white font-medium py-3 px-6 rounded-xl
    focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2
    transition-all flex items-center justify-center text-base
    hover:bg-blue-600
    disabled:opacity-100 disabled:cursor-not-allowed disabled:hover:bg-blue-600
  "
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Поиск...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                  Найти
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
