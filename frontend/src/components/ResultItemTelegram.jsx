import React from "react";

const ResultItemTelegram = React.memo(function ResultItemTelegram({
  item,
  formatQuantity,
  formatDate,
  onBook,
}) {
  const mapQuery = encodeURIComponent(
    `${item.pharmacy_name} №${item.pharmacy_number}, ${item.pharmacy_city}, ${item.pharmacy_address}`,
  );
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;

  return (
    <div
      className="border border-gray-300 rounded-lg p-4 hover:border-telegram-primary transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
      tabIndex={0}
      role="button"
      aria-label={`${item.name} в аптеке ${item.pharmacy_name}. Цена: ${item.price} рублей. Количество: ${formatQuantity(item.quantity)} упаковок. Адрес: ${item.pharmacy_address}. Телефон: ${item.pharmacy_phone}`}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">{item.name}</h3>
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
            {item.pharmacy_name} №{item.pharmacy_number}, {item.pharmacy_city},{" "}
            {item.pharmacy_address}
          </span>
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center ml-2 text-sm text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-2 py-0.5 rounded transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <svg
              className="w-3.5 h-3.5 mr-1 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
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
            На карте
          </a>
        </div>
        <div className="flex items-center">
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
          <span>{item.pharmacy_phone}</span>
        </div>

        <div className="flex items-center text-sm text-gray-800">
          <svg
            className="w-4 h-4 mr-2 flex-shrink-0"
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

        <button
          onClick={(e) => {
            e.stopPropagation();
            onBook(item);
          }}
          disabled={item.quantity <= 0}
          className="w-full bg-telegram-primary text-gray-900 font-medium py-3 px-4 rounded-lg mt-3 hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
        >
          {item.quantity <= 0 ? "Нет в наличии" : "Забронировать"}
        </button>
      </div>
    </div>
  );
});

export default ResultItemTelegram;
