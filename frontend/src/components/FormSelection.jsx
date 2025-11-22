import React, { useState } from "react";

export default function FormSelection({
  searchData,
  onFormSelect,
  onBack,
  loading,
  isTelegram,
  availableCombinations = [],
}) {
  const [selectedCombination, setSelectedCombination] = useState("");

  const handleCombinationClick = (combination) => {
    const combinationKey = `${combination.name}|${combination.form}|${combination.manufacturer}|${combination.country}`;
    setSelectedCombination(combinationKey);

    // Передаем всю комбинацию параметров, включая реальное название
    onFormSelect(
      combination.name, // Используем реальное название из БД, а не поисковый запрос
      combination.form,
      combination.manufacturer,
      combination.country
    );
  };

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header */}
        <div className="border-b border-telegram-border px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Выберите форму препарата
              </h2>
              <p className="text-gray-600 text-sm mt-1">
                Найдено вариантов по запросу "
                <span className="font-semibold uppercase">
                  {searchData.name}
                </span>
                "{searchData.city && ` в городе ${searchData.city}`}
              </p>
            </div>
            <div className="flex gap-2">
              {!isTelegram && (
                <button
                  onClick={onBack}
                  disabled={loading}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center text-sm"
                >
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
                      d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    />
                  </svg>
                  Назад
                </button>
              )}
              <button
                onClick={onBack}
                disabled={loading}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center text-sm"
              >
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
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Новый поиск
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-800 mb-2">
              Выберите нужное название, форму, производителя и страну
            </h3>
          </div>

          {/* Combinations Table */}
          <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-100 border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Название
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Форма
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Производитель
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Страна
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Диапазон цен
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {availableCombinations.map((combo, index) => {
                    const comboKey = `${combo.name}|${combo.form}|${combo.manufacturer}|${combo.country}`;
                    return (
                      <tr
                        key={index}
                        className={`hover:bg-telegram-primary hover:bg-opacity-5 transition-colors cursor-pointer ${
                          selectedCombination === comboKey
                            ? "bg-telegram-primary bg-opacity-10"
                            : ""
                        }`}
                        onClick={() => handleCombinationClick(combo)}
                      >
                        {/* Название - показываем реальное название из БД */}
                        <td className="py-3 px-4">
                          <div className="text-sm font-medium text-gray-800">
                            {combo.name || "Не указано"}
                          </div>
                        </td>
                        {/* Форма */}
                        <td className="py-3 px-4">
                          <div className="text-sm text-gray-600">
                            {combo.form || "Не указана"}
                          </div>
                        </td>
                        {/* Производитель */}
                        <td className="py-3 px-4">
                          <div className="text-sm text-gray-600">
                            {combo.manufacturer || "Не указан"}
                          </div>
                        </td>
                        {/* Страна */}
                        <td className="py-3 px-4">
                          <div className="text-sm text-gray-600">
                            {combo.country || "Не указана"}
                          </div>
                        </td>
                        {/* Диапазон цен */}
                        <td className="py-3 px-4">
                          <div className="text-sm text-gray-600">
                            {combo.min_price} - {combo.max_price} Br
                          </div>
                          {loading && selectedCombination === comboKey && (
                            <div className="flex items-center mt-1">
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-telegram-primary mr-2"></div>
                              <span className="text-xs text-gray-500">
                                Загрузка...
                              </span>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {availableCombinations.length === 0 && !loading && (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-500 mb-2">
                Варианты не найдены
              </h3>
              <p className="text-gray-400 text-sm mb-4">
                Попробуйте изменить параметры поиска
              </p>
              {!isTelegram && (
                <button
                  onClick={onBack}
                  className="bg-telegram-primary text-white font-medium py-2 px-6 rounded-lg transition-colors hover:bg-blue-600"
                >
                  Вернуться к поиску
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
