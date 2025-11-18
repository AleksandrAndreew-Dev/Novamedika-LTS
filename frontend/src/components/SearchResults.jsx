import React from "react";

export default function SearchResults({
  results,
  searchData,
  pagination,
  onPageChange,
  onNewSearch,
  loading,
  isTelegram,
}) {
  // Функция для группировки и суммирования количества одинаковых продуктов в одной аптеке
  const getGroupedResults = () => {
    const grouped = {};

    results.forEach((item) => {
      // Ключ группировки: аптека + название + форма + производитель (без страны)
      const key = `${item.pharmacy_number}-${item.name}-${item.form}-${item.manufacturer}`;

      if (!grouped[key]) {
        // Первое вхождение - создаем новую запись
        grouped[key] = {
          ...item,
          quantity: parseFloat(item.quantity) || 0,
        };
      } else {
        // Уже существует - суммируем количество
        grouped[key].quantity += parseFloat(item.quantity) || 0;

        // Берем самую свежую дату обновления
        const currentDate = new Date(grouped[key].updated_at);
        const newDate = new Date(item.updated_at);
        if (newDate > currentDate) {
          grouped[key].updated_at = item.updated_at;
        }
      }
    });

    return Object.values(grouped);
  };

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return "0";

    // Округляем до 3 знаков после запятой и убираем лишние нули
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

  // Функция для генерации номеров страниц
  const generatePageNumbers = () => {
    const pages = [];
    const current = pagination.page;
    const total = pagination.totalPages;

    // Всегда показываем первую страницу
    pages.push(1);

    // Показываем эллипсис если нужно
    if (current > 3) {
      pages.push("...");
    }

    // Показываем страницы вокруг текущей
    for (
      let i = Math.max(2, current - 1);
      i <= Math.min(total - 1, current + 1);
      i++
    ) {
      pages.push(i);
    }

    // Показываем эллипсис если нужно
    if (current < total - 2) {
      pages.push("...");
    }

    // Всегда показываем последнюю страницу если есть больше 1 страницы
    if (total > 1) {
      pages.push(total);
    }

    return pages;
  };

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header */}
        <div className="border-b border-telegram-border px-4 py-3">
          <div
            className={
              isTelegram ? "space-y-3" : "flex justify-between items-start"
            }
          >
            <div className={isTelegram ? "space-y-2" : "flex-1"}>
              <h2 className="text-lg font-semibold text-gray-800">
                Результаты поиска:
              </h2>
              <p className="text-telegram-primary font-bold text-sm uppercase">
                {searchData.name} {searchData.form}
                {searchData.manufacturer && ` - ${searchData.manufacturer}`}
                {searchData.country && ` (${searchData.country})`}
              </p>
              <p className="text-gray-600 text-sm">
                Найдено {pagination.total} результатов
              </p>
            </div>

            {/* Кнопки для веб-версии */}
            {!isTelegram && (
              <div className="flex gap-2">
                <button
                  onClick={onNewSearch}
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
            )}
          </div>
        </div>

        {/* Для мобильных - упрощенная таблица */}
        {isTelegram ? (
          <div className="p-4">
            {/* Кнопка "Новый поиск" для Telegram */}
            <div className="mb-4">
              <button
                onClick={onNewSearch}
                disabled={loading}
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-sm"
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

            <div className="space-y-3">
              {groupedResults.map((item, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-3"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-800">
                        {item.name}
                      </h3>
                      <p className="text-sm text-gray-600">{item.form}</p>
                    </div>
                    <span className="bg-telegram-primary text-white text-sm font-medium py-1 px-2 rounded-full">
                      {item.price} Br
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>
                      <strong>Аптека:</strong> {item.pharmacy_name} №
                      {item.pharmacy_number}
                    </p>
                    <p>
                      <strong>Адрес:</strong> {item.pharmacy_city},{" "}
                      {item.pharmacy_address}
                    </p>
                    <p>
                      <strong>Телефон:</strong> {item.pharmacy_phone}
                    </p>
                    <p>
                      <strong>Количество:</strong>{" "}
                      {formatQuantity(item.quantity)} уп.
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Обновлено: {formatDate(item.updated_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Пагинация для Telegram */}
            {pagination.totalPages > 1 && (
              <div className="flex justify-center items-center mt-6 space-x-2">
                <button
                  onClick={() => onPageChange(pagination.page - 1)}
                  disabled={pagination.page === 1 || loading}
                  className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-medium py-2 px-3 rounded-lg transition-colors flex items-center text-sm"
                >
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
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

                <span className="text-sm text-gray-600">
                  Страница {pagination.page} из {pagination.totalPages}
                </span>

                <button
                  onClick={() => onPageChange(pagination.page + 1)}
                  disabled={
                    pagination.page === pagination.totalPages || loading
                  }
                  className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-medium py-2 px-3 rounded-lg transition-colors flex items-center text-sm"
                >
                  Вперед
                  <svg
                    className="w-4 h-4 ml-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
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
          </div>
        ) : (
          <div className="p-6">
            {/* Results Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Аптека
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Город
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Адрес
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Телефон
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Название
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Форма
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Цена
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Количество
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Производитель
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {groupedResults.map((item, index) => (
                    <tr
                      key={index}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div>
                          <div className="text-sm font-medium text-gray-800">
                            {item.pharmacy_name} №{item.pharmacy_number}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            Обновлено: {formatDate(item.updated_at)}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {item.pharmacy_city}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {item.pharmacy_address}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {item.pharmacy_phone}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-800">
                        {item.name}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {item.form}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-block bg-telegram-primary text-white text-sm font-medium py-1 px-3 rounded-full">
                          {item.price} Br
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div>
                          <div className="text-sm text-gray-800">
                            {formatQuantity(item.quantity)} уп.
                          </div>
                          <div className="text-xs text-gray-500">
                            Уточняйте в аптеке
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {item.manufacturer}, {item.country}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination для веб-версии */}
            {pagination.totalPages > 1 && (
              <div className="flex justify-center items-center mt-6 space-x-2">
                <button
                  onClick={() => onPageChange(pagination.page - 1)}
                  disabled={pagination.page === 1 || loading}
                  className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-medium py-2 px-3 rounded-lg transition-colors flex items-center text-sm"
                >
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
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

                {/* Номера страниц */}
                {generatePageNumbers().map((page, index) =>
                  page === "..." ? (
                    <span key={index} className="px-2 py-1 text-gray-500">
                      ...
                    </span>
                  ) : (
                    <button
                      key={index}
                      onClick={() => onPageChange(page)}
                      disabled={page === pagination.page || loading}
                      className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                        page === pagination.page
                          ? "bg-telegram-primary text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {page}
                    </button>
                  )
                )}

                <button
                  onClick={() => onPageChange(pagination.page + 1)}
                  disabled={
                    pagination.page === pagination.totalPages || loading
                  }
                  className="bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-medium py-2 px-3 rounded-lg transition-colors flex items-center text-sm"
                >
                  Вперед
                  <svg
                    className="w-4 h-4 ml-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
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
          </div>
        )}
      </div>
    </div>
  );
}
