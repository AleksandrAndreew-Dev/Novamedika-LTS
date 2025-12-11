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

    onFormSelect(
      combination.name,
      combination.form,
      combination.manufacturer,
      combination.country
    );
  };

  const handleKeyPress = (combination, event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleCombinationClick(combination);
    }
  };

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header - показываем только если есть варианты или идет загрузка */}
        {(availableCombinations.length > 0 || loading) && (
          <div className="border-b border-telegram-border px-4 md:px-6 py-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-gray-900 tracking-wide leading-relaxed">
                  По вашему запросу
                  <span className="font-semibold uppercase">
                    {searchData.name}
                    {searchData.city && ` в городе ${searchData.city}`}
                  </span> найдено
                </h2>
                {/* <p className="text-gray-800 text-sm mt-1">
                  По запросу "
                  <span className="font-semibold uppercase">
                    {searchData.name}
                  </span>"
                  {searchData.city && ` в городе ${searchData.city}`}
                </p> */}
              </div>

              <button
                onClick={onBack}
                disabled={loading}
                className="bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-sm w-full sm:w-auto min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                aria-label="Вернуться к поиску"
              >
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
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                {isTelegram ? "Назад" : "Вернуться к поиску"}
              </button>
            </div>
          </div>
        )}

        <div className="p-4 md:p-6">
          {/* Заголовок и описание - показываем только если есть варианты */}
          {availableCombinations.length > 0 && (
            <div className="mb-4 md:mb-6">
              <h3 className="text-base md:text-lg font-medium text-gray-900 mb-2">
                Выберите нужное название, форму, производителя и страну
              </h3>
              {/* <p className="text-gray-800 text-sm">
                Найдено {availableCombinations.length} вариантов
              </p> */}
            </div>
          )}

          {/* Combinations as Cards */}
          {availableCombinations.length > 0 && (
            <div className="space-y-3" role="list" aria-label="Доступные варианты препаратов">
              {availableCombinations.map((combo, index) => {
                const comboKey = `${combo.name}|${combo.form}|${combo.manufacturer}|${combo.country}`;
                const isSelected = selectedCombination === comboKey;

                return (
                  <div
                    key={index}
                    className={`border rounded-xl p-4 transition-all cursor-pointer min-h-[60px] ${
                      isSelected
                        ? 'border-telegram-primary bg-blue-50 shadow-sm ring-2 ring-telegram-primary'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    } focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2`}
                    onClick={() => handleCombinationClick(combo)}
                    onKeyDown={(e) => handleKeyPress(combo, e)}
                    tabIndex={0}
                    role="button"
                    aria-label={`Выбрать ${combo.name}, форма: ${combo.form || "не указана"}, производитель: ${combo.manufacturer || "не указан"}`}
                    aria-pressed={isSelected}
                  >
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-base md:text-lg">{combo.name}</h3>
                        <div className="flex flex-wrap gap-1 md:gap-2 mt-2">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 min-h-[24px]">
                            {combo.form || "Не указана"}
                          </span>
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 min-h-[24px]">
                            {combo.manufacturer || "Не указан"}
                          </span>
                          {combo.country && (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 min-h-[24px]">
                              {combo.country}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="text-left sm:text-right">
                        <div className="text-base md:text-lg font-bold text-telegram-primary">
                          {combo.min_price} - {combo.max_price} Br
                        </div>
                        {isSelected && loading && (
                          <div className="flex items-center justify-start sm:justify-end mt-2" aria-live="polite">
                            <div
                              className="animate-spin rounded-full h-5 w-5 border-b-2 border-telegram-primary"
                              aria-hidden="true"
                            ></div>
                            <span className="text-sm text-gray-700 ml-2">Загрузка результатов...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {availableCombinations.length === 0 && !loading && (
            <div className="text-center py-8 md:py-12">
              <div className="text-gray-500 mb-4">
                <svg
                  className="w-12 h-12 md:w-16 md:h-16 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Ничего не найдено
              </h3>
              <p className="text-gray-800 text-sm mb-4">
                Попробуйте изменить название препарата или город поиска
              </p>
              <button
                onClick={onBack}
                className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
              >
                Изменить поиск
              </button>
            </div>
          )}

          {loading && availableCombinations.length === 0 && (
            <div className="text-center py-8" aria-live="polite">
              <div className="flex justify-center items-center space-x-2">
                <div
                  className="animate-spin rounded-full h-8 w-8 border-b-2 border-telegram-primary"
                  aria-hidden="true"
                ></div>
                <span className="text-gray-800">Загрузка вариантов...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
