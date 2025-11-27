import React from "react";

export default function ProductCard({ item, isTelegram, onBook, formatQuantity, formatDate }) {
  return isTelegram ? (
    <TelegramProductCard
      item={item}
      onBook={onBook}
      formatQuantity={formatQuantity}
      formatDate={formatDate}
    />
  ) : (
    <WebProductCard
      item={item}
      onBook={onBook}
      formatQuantity={formatQuantity}
      formatDate={formatDate}
    />
  );
}

function TelegramProductCard({ item, onBook, formatQuantity, formatDate }) {
  const handleCardKeyPress = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
    }
  };

  return (
    <div
      className="border border-gray-300 rounded-lg p-4 hover:border-telegram-primary transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
      tabIndex={0}
      role="button"
      aria-label={`${item.name} в аптеке ${item.pharmacy_name}. Цена: ${item.price} рублей. Количество: ${formatQuantity(item.quantity)} упаковок. Адрес: ${item.pharmacy_address}. Телефон: ${item.pharmacy_phone}`}
      onKeyDown={handleCardKeyPress}
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

      <ProductDetails item={item} formatQuantity={formatQuantity} formatDate={formatDate} />

      <BookButton item={item} onBook={onBook} />
    </div>
  );
}

function WebProductCard({ item, onBook, formatQuantity, formatDate }) {
  const handleCardKeyPress = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
    }
  };

  return (
    <div
      className="bg-white border border-gray-300 rounded-xl p-4 md:p-6 hover:shadow-md transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
      tabIndex={0}
      role="article"
      aria-label={`${item.name}, ${item.form} от ${item.manufacturer || "неизвестного производителя"} в аптеке ${item.pharmacy_name}`}
      onKeyDown={handleCardKeyPress}
    >
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4 mb-4">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 text-lg md:text-xl">{item.name}</h3>
          <p className="text-gray-800 text-sm md:text-base mt-1">
            {item.form} • {item.manufacturer || "Производитель не указан"}
          </p>
        </div>
        <div className="text-left lg:text-right">
          <div className="text-xl md:text-2xl font-bold text-telegram-primary">{item.price} Br</div>
          <div className="text-sm md:text-base text-gray-800 mt-1 font-medium">
            {formatQuantity(item.quantity)} уп.
          </div>
        </div>
      </div>

      <ProductDetails item={item} formatQuantity={formatQuantity} formatDate={formatDate} isWeb />

      <div className="mt-4 flex justify-end">
        <BookButton item={item} onBook={onBook} />
      </div>
    </div>
  );
}

function ProductDetails({ item, formatQuantity, formatDate, isWeb = false }) {
  const Container = isWeb ? "div" : "div";
  const textClass = isWeb ? "text-sm md:text-base" : "text-sm";

  return (
    <Container className={`${isWeb ? 'grid grid-cols-1 md:grid-cols-2 gap-4' : 'space-y-2'} ${textClass} text-gray-800`}>
      <div>
        <div className="flex items-start mb-2">
          <LocationIcon />
          <span>
            {item.pharmacy_name} №{item.pharmacy_number}, {item.pharmacy_address}
          </span>
        </div>
        {isWeb && (
          <div className="text-gray-800 ml-7">
            {item.pharmacy_address}, {item.pharmacy_city}
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center mb-2">
          <PhoneIcon />
          <span className={isWeb ? "text-gray-900 font-medium" : ""}>
            {isWeb ? "Телефон:" : ""} {item.pharmacy_phone}
          </span>
        </div>

        <div className="flex items-center">
          <TimeIcon />
          <div>
            {isWeb && <span className="text-gray-900 font-medium">Время работы:</span>}{" "}
            {item.working_hours || "Уточняйте в аптеке"}
          </div>
        </div>

        {isWeb ? (
          <div className="text-gray-700 text-xs md:text-sm ml-7 bg-gray-100 inline-block py-1 px-2 rounded">
            Обновлено: {formatDate(item.updated_at)}
          </div>
        ) : (
          <div className="flex justify-between items-center">
            <span className="font-medium">Количество: {formatQuantity(item.quantity)} уп.</span>
            <span className="text-xs text-gray-700 bg-gray-100 py-1 px-2 rounded">
              {formatDate(item.updated_at)}
            </span>
          </div>
        )}
      </div>
    </Container>
  );
}

function BookButton({ item, onBook }) {
  return (
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
  );
}

// Иконки как отдельные компоненты для переиспользования
function LocationIcon() {
  return <Icon path="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z" />;
}

function PhoneIcon() {
  return <Icon path="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />;
}

function TimeIcon() {
  return <Icon path="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />;
}

function Icon({ path }) {
  return (
    <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
    </svg>
  );
}
