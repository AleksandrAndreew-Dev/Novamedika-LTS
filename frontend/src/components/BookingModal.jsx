import React from "react";

const BookingModal = React.memo(function BookingModal({
  bookingState,
  onFormChange,
  onQuantityChange,
  onClose,
  onSubmit,
}) {
  if (!bookingState.modal.isOpen || !bookingState.modal.product) return null;

  const product = bookingState.modal.product;

  const mapQuery = encodeURIComponent(
    `${product.pharmacy_name} №${product.pharmacy_number}, ${product.pharmacy_city || ""}${product.pharmacy_district ? `, ${product.pharmacy_district}` : ""}, ${product.pharmacy_address}`,
  );
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return "0";
    if (num % 1 === 0) return num.toString();
    return num.toFixed(3).replace(/\.?0+$/, "");
  };

  const calculateTotalPrice = () => {
    const total = product.price * bookingState.modal.quantity;
    return total.toFixed(2);
  };

  return (
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
                onClick={onClose}
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
                  onClick={onClose}
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

              <div className="mb-6 p-4 bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-gray-200">
                <h3 className="font-bold text-gray-900 text-lg mb-2">
                  {product.name}
                </h3>
                <p className="text-sm text-gray-600 mb-1">{product.form}</p>

                <div className="mt-4 pt-3 border-t border-gray-200">
                  <h4 className="font-semibold text-gray-900 mb-2">Аптека:</h4>
                  <p className="text-sm text-gray-600 mb-1">
                    {product.pharmacy_name} №{product.pharmacy_number}
                  </p>
                  <p className="text-sm text-gray-600 mb-1">
                    {product.pharmacy_city}
                    {product.pharmacy_district && (
                      <span className="text-gray-500">
                        , {product.pharmacy_district}
                      </span>
                    )}
                    , {product.pharmacy_address}
                  </p>
                  <a
                    href={mapUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium inline-flex items-center mb-1"
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
                        d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                    Посмотреть на карте
                  </a>
                  <p className="text-sm text-gray-600 mb-1">
                    Телефон: {product.pharmacy_phone}
                  </p>
                  <p className="text-sm text-gray-600">
                    Время работы:{" "}
                    {product.working_hours || "Уточняйте в аптеке"}
                  </p>
                </div>

                <div className="flex justify-between items-center mt-3">
                  <p className="text-sm font-semibold text-gray-700">
                    Доступно: {formatQuantity(product.quantity)} уп.
                  </p>
                  <p className="text-lg font-bold text-blue-600">
                    {product.price} Br
                  </p>
                </div>
              </div>

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

              <form onSubmit={onSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Ваше имя *
                  </label>
                  <input
                    type="text"
                    value={bookingState.form.customer_name}
                    onChange={(e) =>
                      onFormChange("customer_name", e.target.value)
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
                      onFormChange("customer_phone", e.target.value)
                    }
                    required
                    disabled={bookingState.loading}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200"
                    placeholder="+375 XX XXX-XX-XX"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Количество упаковок *
                  </label>
                  <div className="flex items-center gap-2 sm:gap-3">
                    {/* Кнопка уменьшения */}
                    <button
                      type="button"
                      onClick={() => {
                        const newQty = Math.max(1, bookingState.modal.quantity - 1);
                        onQuantityChange(newQty.toString());
                      }}
                      disabled={bookingState.loading || bookingState.modal.quantity <= 1}
                      className="min-w-[48px] min-h-[48px] sm:w-12 sm:h-12 flex-shrink-0 flex items-center justify-center bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all duration-200 border border-gray-300 touch-manipulation"
                      aria-label="Уменьшить количество"
                    >
                      <svg className="w-6 h-6 sm:w-5 sm:h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M20 12H4" />
                      </svg>
                    </button>
                    
                    {/* Поле ввода количества - стандартное поведение без автовыделения */}
                    <input
                      type="number"
                      min="1"
                      value={bookingState.modal.quantity}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value === '') {
                          onQuantityChange('1');
                        } else {
                          const num = parseInt(value);
                          if (!isNaN(num) && num >= 1) {
                            onQuantityChange(value);
                          }
                        }
                      }}
                      onBlur={(e) => {
                        if (e.target.value === '' || parseInt(e.target.value) < 1) {
                          onQuantityChange('1');
                        }
                      }}
                      disabled={bookingState.loading}
                      className="flex-1 min-w-[60px] px-3 py-3 sm:px-4 sm:py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200 text-center font-semibold text-lg touch-manipulation"
                      placeholder="1"
                      inputMode="numeric"
                      pattern="[0-9]*"
                    />
                    
                    {/* Кнопка увеличения */}
                    <button
                      type="button"
                      onClick={() => {
                        const newQty = bookingState.modal.quantity + 1;
                        onQuantityChange(newQty.toString());
                      }}
                      disabled={bookingState.loading}
                      className="min-w-[48px] min-h-[48px] sm:w-12 sm:h-12 flex-shrink-0 flex items-center justify-center bg-blue-500 hover:bg-blue-600 active:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all duration-200 shadow-md touch-manipulation"
                      aria-label="Увеличить количество"
                    >
                      <svg className="w-6 h-6 sm:w-5 sm:h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                      </svg>
                    </button>
                  </div>
                  
                  <div className="flex items-center justify-between mt-2">
                    <p className="text-xs text-gray-500">
                      Используйте +/- или введите число
                    </p>
                    <p className="text-sm font-semibold text-blue-600">
                      Итого: {calculateTotalPrice()} Br
                    </p>
                  </div>
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
                    onClick={onClose}
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
  );
});

export default BookingModal;
