import React from "react";

const ResultItemWeb = React.memo(function ResultItemWeb({
  item,
  formatQuantity,
  formatDate,
  onBook,
}) {
  return (
    <div
      className="bg-white border border-gray-300 rounded-xl p-4 md:p-6 hover:shadow-md transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
      tabIndex={0}
      role="article"
      aria-label={`${item.name}, ${item.form} от ${item.manufacturer || "неизвестного производителя"} в аптеке ${item.pharmacy_name}`}
    >
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4 mb-4">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 text-lg md:text-xl">
            {item.name}
          </h3>
          <p className="text-gray-800 text-sm md:text-base mt-1">
            {item.form} • {item.manufacturer || "Производитель не указан"}
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
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
            <div>
              <strong className="text-gray-900">{item.pharmacy_name}</strong> №
              {item.pharmacy_number}
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
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
              />
            </svg>
            <span className="text-gray-900 font-medium">Телефон:</span>{" "}
            {item.pharmacy_phone}
          </div>

          <div className="flex items-center text-gray-800">
            <svg
              className="w-5 h-5 mr-2 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <span className="text-gray-900 font-medium">Время работы:</span>{" "}
              {item.working_hours || "Уточняйте в аптеке"}
            </div>
          </div>
          <div className="text-gray-700 text-xs md:text-sm ml-7 bg-gray-100 inline-block py-1 px-2 rounded">
            Обновлено: {formatDate(item.updated_at)}
          </div>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={() => onBook(item)}
          disabled={item.quantity <= 0}
          className="bg-telegram-primary text-gray-900 font-medium py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {item.quantity <= 0 ? "Нет в наличии" : "Забронировать"}
        </button>
      </div>
    </div>
  );
});

export default ResultItemWeb;
