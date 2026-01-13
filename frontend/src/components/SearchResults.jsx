import React, { useState } from "react";
import { bookingApi } from "../api/client";
import { useTelegramUser } from "../telegram/TelegramWebApp"; // Добавляем хук

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
  const [bookingState, setBookingState] = useState({
    modal: {
      isOpen: false,
      product: null,
      quantity: 1,
    },
    form: {
      customer_name: "",
      customer_phone: "",
    },
    loading: false,
    success: false,
    error: null,
    orderInfo: null,
  });

  // Получаем данные пользователя Telegram
  const telegramUser = useTelegramUser();

  const openBookingModal = (product) => {
    setBookingState((prev) => ({
      ...prev,
      modal: {
        isOpen: true,
        product: product,
        quantity: 1,
      },
      form: {
        // Если есть данные пользователя Telegram, подставляем их
        customer_name: "",
        customer_phone: telegramUser?.phone_number || "",
      },
      success: false,
      error: null,
      orderInfo: null,
    }));
  };

  // Функция обработки бронирования
  const handleBooking = async (e) => {
    e.preventDefault();
    if (!bookingState.modal.product) return;

    setBookingState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const bookingData = {
        product_id: bookingState.modal.product.product_uuid, // Изменено с uuid
        pharmacy_id: bookingState.modal.product.pharmacy_id,
        quantity: bookingState.modal.quantity,
        customer_name: bookingState.form.customer_name.trim(),
        customer_phone: bookingState.form.customer_phone.trim(),
        telegram_id: telegramUser?.id || null, // Добавляем Telegram ID
      };

      // Валидация данных
      if (!bookingData.customer_name) {
        throw new Error("Введите ваше имя");
      }

      if (!bookingData.customer_phone) {
        throw new Error("Введите номер телефона");
      }

      // Базовая валидация телефона
      const phoneRegex = /^[+]?[1-9][\d]{0,15}$/;
      const cleanPhone = bookingData.customer_phone.replace(/[^\d+]/g, "");
      if (!phoneRegex.test(cleanPhone)) {
        throw new Error("Введите корректный номер телефона");
      }

      // Используем API метод для создания заказа
      const order = await bookingApi.createOrder(bookingData);

      setBookingState((prev) => ({
        ...prev,
        loading: false,
        success: true,
        orderInfo: order,
      }));

      // Автоматическое закрытие через 3 секунды
      setTimeout(() => {
        closeBookingModal();
      }, 3000);
    } catch (error) {
      console.error("Booking error:", error);

      let errorMessage = "Ошибка при бронировании";

      if (error.response) {
        const serverError = error.response.data;
        if (serverError.detail) {
          errorMessage = serverError.detail;
        } else if (typeof serverError === "string") {
          errorMessage = serverError;
        } else if (serverError.message) {
          errorMessage = serverError.message;
        }
      } else if (error.request) {
        errorMessage = "Ошибка сети. Проверьте подключение к интернету.";
      } else {
        errorMessage = error.message;
      }

      setBookingState((prev) => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  };

  // Функция обновления формы
  const updateBookingForm = (field, value) => {
    setBookingState((prev) => ({
      ...prev,
      form: {
        ...prev.form,
        [field]: value,
      },
    }));
  };

  // Функция обновления количества
  const updateBookingQuantity = (quantity) => {
    // Преобразуем в число и убираем NaN значения
    const numQuantity = parseInt(quantity) || 1;
    setBookingState((prev) => ({
      ...prev,
      modal: {
        ...prev.modal,
        quantity: Math.max(1, numQuantity), // Минимальное значение 1
      },
    }));
  };

  // Функция закрытия модального окна
  const closeBookingModal = () => {
    setBookingState({
      modal: {
        isOpen: false,
        product: null,
        quantity: 1,
      },
      form: {
        customer_name: "",
        customer_phone: "",
      },
      loading: false,
      success: false,
      error: null,
      orderInfo: null,
    });
  };

  // Функция для расчета итоговой суммы с округлением
  const calculateTotalPrice = () => {
    if (!bookingState.modal.product) return "0.00";
    const total =
      bookingState.modal.product.price * bookingState.modal.quantity;
    return total.toFixed(2);
  };

  // УДАЛЕНО: функция getPackagingText больше не используется

  const getGroupedResults = () => {
    const grouped = {};

  results.filter(item => (parseFloat(item.quantity) || 0) > 0)
  .forEach((item) => {
    // Используем product_uuid для бронирования
    const productUuid = item.product_uuid || item.uuid || item.id;
    const pharmacyId = item.pharmacy_id || item.pharmacy_number;

    const key = `${pharmacyId}-${item.name}-${item.form}-${item.manufacturer}`;

    if (!grouped[key]) {
      grouped[key] = {
        ...item,
        // Сохраняем UUID продукта для бронирования
        product_uuid: productUuid,
        pharmacy_id: pharmacyId,
        quantities: [parseFloat(item.quantity) || 0],
        prices: [parseFloat(item.price) || 0],
        working_hours: item.working_hours || item.opening_hours || "9:00-21:00",
      };
    } else {
        // Добавляем новое количество (не суммируем!)
        grouped[key].quantities.push(parseFloat(item.quantity) || 0);
        // Добавляем новую цену
        if (!grouped[key].prices.includes(parseFloat(item.price) || 0)) {
          grouped[key].prices.push(parseFloat(item.price) || 0);
        }

        // Обновляем время, если запись новее
        const currentDate = new Date(grouped[key].updated_at);
        const newDate = new Date(item.updated_at);
        if (newDate > currentDate) {
          grouped[key].updated_at = item.updated_at;
          if (item.working_hours || item.opening_hours) {
            grouped[key].working_hours =
              item.working_hours || item.opening_hours;
          }
        }
      }
    });

    // Преобразуем обратно в массив с рассчитанными суммами
     return Object.values(grouped).map((item) => ({
    ...item,
    quantity: item.quantities.reduce((sum, q) => sum + q, 0),
    price: Math.min(...item.prices),
    hasMultiplePrices: item.prices.length > 1,
    originalPrices: item.prices,
  }));
};

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return "0";

    if (num % 1 === 0) {
      return num.toString();
    }

    // Для дробных значений показываем с точностью до 3 знаков
    return num.toFixed(3).replace(/\.?0+$/, "");
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
    }
  };

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      {/* Модальное окно бронирования */}
      {bookingState.modal.isOpen && (
        <div className="fixed inset-0 bg-gradient-to-br from-gray-900/80 via-blue-900/40 to-purple-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto animate-scaleIn">
            <div className="p-6">
              {bookingState.success ? (
                <div className="text-center">
                  <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
                    <svg
                      className="w-8 h-8 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    Бронирование успешно!
                  </h3>
                  <p className="text-gray-600 mb-2">
                    Номер заказа:{" "}
                    <strong className="text-gray-900">
                      {bookingState.orderInfo?.uuid?.substring(0, 8)}...
                    </strong>
                  </p>
                  <p className="text-gray-600 mb-6 text-sm">
                    Ожидайте звонка из аптеки для подтверждения.
                  </p>
                  <button
                    onClick={closeBookingModal}
                    className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-3 px-4 rounded-xl hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-lg"
                  >
                    Закрыть
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">
                      Бронирование
                    </h2>
                    <button
                      onClick={closeBookingModal}
                      disabled={bookingState.loading}
                      className="text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors p-1 rounded-lg hover:bg-gray-100"
                    >
                      <svg
                        className="w-6 h-6"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>

                  {bookingState.modal.product && (
                    <div className="mb-6 p-4 bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-gray-200">
                      <h3 className="font-bold text-gray-900 text-lg mb-2">
                        {bookingState.modal.product.name}
                      </h3>
                      <p className="text-sm text-gray-600 mb-1">
                        {bookingState.modal.product.form}
                      </p>

                      {/* Информация об аптеке */}
                      <div className="mt-4 pt-3 border-t border-gray-200">
                        <h4 className="font-semibold text-gray-900 mb-2">
                          Аптека:
                        </h4>
                        <p className="text-sm text-gray-600 mb-1">
                          {bookingState.modal.product.pharmacy_name} №
                          {bookingState.modal.product.pharmacy_number}
                        </p>
                        <p className="text-sm text-gray-600 mb-1">
                          Адрес: {bookingState.modal.product.pharmacy_address}
                        </p>
                        <p className="text-sm text-gray-600 mb-1">
                          Телефон: {bookingState.modal.product.pharmacy_phone}
                        </p>
                        <p className="text-sm text-gray-600">
                          Время работы:{" "}
                          {bookingState.modal.product.working_hours ||
                            "Уточняйте в аптеке"}
                        </p>
                      </div>

                      <div className="flex justify-between items-center mt-3">
                        <p className="text-sm font-semibold text-gray-700">
                          Доступно:{" "}
                          {formatQuantity(bookingState.modal.product.quantity)}{" "}
                          уп.
                        </p>
                        <p className="text-lg font-bold text-blue-600">
                          {bookingState.modal.product.price} Br
                        </p>
                      </div>
                    </div>
                  )}

                  {bookingState.error && (
                    <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl">
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-red-500 mr-2"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="text-red-800 text-sm font-medium">
                          {bookingState.error}
                        </span>
                      </div>
                    </div>
                  )}

                  <form onSubmit={handleBooking} className="space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Ваше имя *
                      </label>
                      <input
                        type="text"
                        value={bookingState.form.customer_name}
                        onChange={(e) =>
                          updateBookingForm("customer_name", e.target.value)
                        }
                        required
                        disabled={bookingState.loading}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200"
                        placeholder="Иван Иванов"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Телефон *
                      </label>
                      <input
                        type="tel"
                        value={bookingState.form.customer_phone}
                        onChange={(e) =>
                          updateBookingForm("customer_phone", e.target.value)
                        }
                        required
                        disabled={bookingState.loading}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200"
                        placeholder="+375 XX XXX-XX-XX"
                      />
                      {/* Убрана строка с форматом телефона */}
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Количество упаковок *
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={bookingState.modal.quantity}
                        onChange={(e) => updateBookingQuantity(e.target.value)}
                        disabled={bookingState.loading}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200"
                        placeholder="Введите количество"
                      />
                      <p className="text-xs text-gray-500 mt-2">
                        Итоговая сумма:{" "}
                        <strong className="text-blue-600">
                          {calculateTotalPrice()} Br
                        </strong>
                      </p>
                    </div>

                    <div className="flex gap-3 pt-4">
                      <button
                        type="submit"
                        disabled={bookingState.loading}
                        className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-4 px-6 rounded-xl hover:from-blue-600 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg"
                      >
                        {bookingState.loading ? (
                          <>
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                            Бронируем...
                          </>
                        ) : (
                          `Забронировать за ${calculateTotalPrice()} Br`
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={closeBookingModal}
                        disabled={bookingState.loading}
                        className="flex-1 bg-gray-100 text-gray-800 font-semibold py-4 px-6 rounded-xl hover:bg-gray-200 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Отмена
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Остальной код компонента остается без изменений */}
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header */}
        <div className="border-b border-telegram-border px-4 md:px-6 py-4">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900 tracking-wide leading-relaxed">
                Результаты поиска:
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
              Выберите удобную для Вас аптеку:
            </h3>
            {/* <p className="text-gray-800 text-sm">
              <span className="mr-1">{searchData.name}</span>
              {searchData.form}
              {searchData.manufacturer && ` - ${searchData.manufacturer}`}
              {searchData.country && ` (${searchData.country})`}
            </p> */}
          </div>

          {loading && (
            <div className="space-y-4 mb-6" aria-live="polite">
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
                        Время работы:{" "}
                        {item.working_hours || "Уточняйте в аптеке"}
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

                    {/* Кнопка бронирования для Telegram */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openBookingModal(item);
                      }}
                      disabled={item.quantity <= 0}
                      className="w-full bg-telegram-primary text-gray-900 font-medium py-3 px-4 rounded-lg mt-3 hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2"
                    >
                      {item.quantity <= 0 ? "Нет в наличии" : "Забронировать"}
                    </button>
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

                  {/* Кнопка бронирования для веб-версии */}
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={() => openBookingModal(item)}
                      disabled={item.quantity <= 0}
                      className="bg-telegram-primary text-gray-900 font-medium py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {item.quantity <= 0 ? "Нет в наличии" : "Забронировать"}
                    </button>
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
                В выбранной аптеке нет этого препарата
              </h3>
              <p className="text-gray-800 text-sm mb-6">
                Попробуйте выбрать другую форму или изменить параметры поиска
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={onBackToForms}
                  className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:ring-offset-2 min-h-[44px]"
                >
                  Выбрать другую форму
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
