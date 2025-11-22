import React from "react";

export default function SearchResults({
  results,
  searchData,
  pagination,
  onPageChange,
  onNewSearch,
  onBackToForms,
  loading,
  isTelegram,
}) {
  // SearchResults.jsx - обновляем функцию getGroupedResults и добавляем время работы
  const getGroupedResults = () => {
    const grouped = {};

    results.forEach((item) => {
      const key = `${item.pharmacy_number}-${item.name}-${item.form}-${item.manufacturer}`;

      if (!grouped[key]) {
        grouped[key] = {
          ...item,
          quantity: parseFloat(item.quantity) || 0,
          working_hours:
            item.working_hours || item.opening_hours || "9:00-21:00", // добавляем время работы
        };
      } else {
        grouped[key].quantity += parseFloat(item.quantity) || 0;

        const currentDate = new Date(grouped[key].updated_at);
        const newDate = new Date(item.updated_at);
        if (newDate > currentDate) {
          grouped[key].updated_at = item.updated_at;
          // Обновляем время работы, если есть более актуальные данные
          if (item.working_hours || item.opening_hours) {
            grouped[key].working_hours =
              item.working_hours || item.opening_hours;
          }
        }
      }
    });

    return Object.values(grouped);
  };

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return "0";

    const formatted = Math.round(num * 1000) / 1000;
    return formatted.toString().replace(/\.?0+$/, "");
  };

  const groupedResults = getGroupedResults();

  const formatDate = (dateString) => {
    if (!dateString) return "Недавно";

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} мин назад`;
    } else if (diffHours < 24) {
      return `${diffHours} ч назад`;
    } else {
      return `${diffDays} дн назад`;
    }
  };

  const handleCardKeyPress = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      // Можно добавить дополнительное действие при активации карточки
    }
  };

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header */}
        <div className="border-b border-telegram-border px-4 md:px-6 py-4">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900">
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
              <button
                onClick={onBackToForms}
                disabled={loading}
                className="flex-1 sm:flex-none bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                aria-label="Вернуться к выбору формы препарата"
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
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
                Изменить форму
              </button>

              <button
                onClick={onNewSearch}
                disabled={loading}
                className="flex-1 sm:flex-none bg-telegram-primary text-gray-900 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-sm hover:bg-blue-600 hover:text-gray-900 min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                aria-label="Начать новый поиск"
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
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                Новый поиск
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 md:p-6">
          <div className="mb-4 md:mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Найдено результатов: {pagination.total}
            </h3>
            <p className="text-gray-800 text-sm">
              <span className="mr-1">{searchData.name}</span>
              {searchData.form}
              {searchData.manufacturer && ` - ${searchData.manufacturer}`}
              {searchData.country && ` (${searchData.country})`}
            </p>
          </div>

          {loading && (
            <div className="space-y-4 mb-6" aria-live="polite">
              {/* Скелетон-заглушки для загрузки */}
              {[1, 2, 3].map((item) => (
                <div
                  key={item}
                  className="bg-white border border-gray-200 rounded-xl p-6"
                >
                  <div className="animate-pulse space-y-4">
                    <div className="flex space-x-4">
                      <div className="rounded-full bg-gray-300 h-12 w-12"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-300 rounded w-3/4"></div>
                        <div className="h-3 bg-gray-300 rounded w-1/2"></div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="h-4 bg-gray-300 rounded"></div>
                      <div className="h-4 bg-gray-300 rounded w-5/6"></div>
                    </div>
                  </div>
                </div>
              ))}
              <div className="text-center text-gray-800 text-sm">
                Загрузка результатов...
              </div>
            </div>
          )}

          {/* Content: Telegram list view OR Web card view */}
          {isTelegram ? (
            <div
              className="space-y-3"
              role="list"
              aria-label="Результаты поиска лекарств"
            >
              {groupedResults.map((item, index) => (
                <div
                  key={index}
                  className="border border-gray-300 rounded-lg p-4 hover:border-telegram-primary transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                  tabIndex={0}
                  role="button"
                  aria-label={`${item.name} в аптеке ${
                    item.pharmacy_name
                  }. Цена: ${item.price} рублей. Количество: ${formatQuantity(
                    item.quantity
                  )} упаковок. Адрес: ${item.pharmacy_address}. Телефон: ${
                    item.pharmacy_phone
                  }`}
                  onKeyDown={handleCardKeyPress}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">
                        {item.name}
                      </h3>
                      <p className="text-sm text-gray-800">{item.form}</p>
                    </div>
                    <span className="bg-telegram-primary text-gray-900 text-sm font-medium py-2 px-3 rounded-full ml-2 min-h-[32px] flex items-center">
                      {item.price} Br
                    </span>
                  </div>
                  <div className="text-sm text-gray-800 space-y-2">
                    <div className="flex items-start">
                      <svg
                        className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                      </svg>
                      <span>
                        {item.pharmacy_name} №{item.pharmacy_number},{" "}
                        {item.pharmacy_address}
                      </span>
                    </div>
                    <div className="flex items-center">
                      <svg
                        className="w-5 h-5 mr-2 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                        />
                      </svg>
                      <span>{item.pharmacy_phone}</span>
                    </div>

                    <div className="flex items-center text-sm text-gray-800">
                      <svg
                        className="w-4 h-4 mr-2 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span>
                        Время работы: {item.working_hours || "Уточняйте в аптеке"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-medium">
                        Количество: {formatQuantity(item.quantity)} уп.
                      </span>
                      <span className="text-xs text-gray-700 bg-gray-100 py-1 px-2 rounded">
                        {formatDate(item.updated_at)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className="space-y-4"
              role="list"
              aria-label="Результаты поиска лекарств"
            >
              {groupedResults.map((item, index) => (
                <div
                  key={index}
                  className="bg-white border border-gray-300 rounded-xl p-4 md:p-6 hover:shadow-md transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                  tabIndex={0}
                  role="article"
                  aria-label={`${item.name}, ${item.form} от ${
                    item.manufacturer || "неизвестного производителя"
                  } в аптеке ${item.pharmacy_name}`}
                  onKeyDown={handleCardKeyPress}
                >
                  <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4 mb-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 text-lg md:text-xl">
                        {item.name}
                      </h3>
                      <p className="text-gray-800 text-sm md:text-base mt-1">
                        {item.form} •{" "}
                        {item.manufacturer || "Производитель не указан"}
                      </p>
                    </div>
                    <div className="text-left lg:text-right">
                      <div className="text-xl md:text-2xl font-bold text-telegram-primary">
                        {item.price} Br
                      </div>
                      <div className="text-sm md:text-base text-gray-800 mt-1 font-medium">
                        {formatQuantity(item.quantity)} уп.
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm md:text-base">
                    <div>
                      <div className="flex items-center text-gray-800 mb-2">
                        <svg
                          className="w-5 h-5 mr-2 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                          />
                        </svg>
                        <div>
                          <strong className="text-gray-900">
                            {item.pharmacy_name}
                          </strong>{" "}
                          №{item.pharmacy_number}
                        </div>
                      </div>
                      <div className="text-gray-800 ml-7">
                        {item.pharmacy_address}, {item.pharmacy_city}
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center text-gray-800 mb-2">
                        <svg
                          className="w-5 h-5 mr-2 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                          />
                        </svg>
                        <span className="text-gray-900 font-medium">
                          Телефон:
                        </span>{" "}
                        {item.pharmacy_phone}
                      </div>

                      <div className="flex items-center text-gray-800">
                        <svg
                          className="w-5 h-5 mr-2 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <div>
                          <span className="text-gray-900 font-medium">
                            Время работы:
                          </span>{" "}
                          {item.working_hours || "Уточняйте в аптеке"}
                        </div>
                      </div>
                      <div className="text-gray-700 text-xs md:text-sm ml-7 bg-gray-100 inline-block py-1 px-2 rounded">
                        Обновлено: {formatDate(item.updated_at)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {groupedResults.length === 0 && !loading && (
            <div className="text-center py-12" role="status">
              <div className="text-gray-600 mb-4">
                <svg
                  className="w-16 h-16 md:w-20 md:h-20 mx-auto"
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
                Результаты не найдены
              </h3>
              <p className="text-gray-800 text-sm mb-6">
                Попробуйте изменить параметры поиска или выбрать другую форму
                препарата
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={onBackToForms}
                  className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
                >
                  Изменить форму
                </button>
                <button
                  onClick={onNewSearch}
                  className="bg-gray-100 text-gray-800 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
                >
                  Новый поиск
                </button>
              </div>
            </div>
          )}

          {/* Пагинация */}
          {pagination.totalPages > 1 && (
            <div
              className="flex justify-center items-center mt-8 space-x-2"
              role="navigation"
              aria-label="Навигация по страницам"
            >
              <button
                onClick={() => onPageChange(pagination.page - 1)}
                disabled={pagination.page === 1 || loading}
                className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                aria-label="Предыдущая страница"
              >
                <svg
                  className="w-5 h-5 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
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
                <svg
                  className="w-5 h-5 ml-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            </div>
          )}

          {loading && pagination.totalPages > 1 && (
            <div className="text-center mt-4" aria-live="polite">
              <div className="inline-flex items-center text-sm text-gray-800 bg-gray-100 py-2 px-4 rounded-lg">
                <div
                  className="animate-spin rounded-full h-4 w-4 border-b-2 border-telegram-primary mr-2"
                  aria-hidden="true"
                ></div>
                Загрузка страницы...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
