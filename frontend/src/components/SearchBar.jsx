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
      className={`rounded-2xl shadow-sm border ${
        isTelegram ? "p-4 mb-2" : "p-6 mb-6"
      } bg-gray-800 border-gray-700 text-gray-100`}
    >
      <form onSubmit={handleSubmit} className="w-full">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-200 mb-2">
              Город
            </label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent transition-all text-base text-gray-100"
            >
              <option value="" className="bg-gray-900 text-gray-100">
                Все города
              </option>
              {cities.map((cityName) => (
                <option
                  key={cityName}
                  value={cityName}
                  className="bg-gray-900 text-gray-100"
                >
                  {cityName}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-200 mb-2">
              Название препарата *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: анальгин, парацетамол..."
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent transition-all text-base text-gray-100 placeholder-gray-400"
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
