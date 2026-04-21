import React, { useReducer, useMemo } from "react";
import { bookingApi } from "../api/client";
import { useTelegramUser } from "../telegram/TelegramContext";
import { bookingReducer, initialState } from "../hooks/useBookingReducer";
import BookingModal from "./BookingModal";
import ResultItemTelegram from "./ResultItemTelegram";
import ResultItemWeb from "./ResultItemWeb";
import SearchResultsPagination from "./SearchResultsPagination";
import SkeletonList from "./SkeletonList";

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
  const [bookingState, dispatch] = useReducer(bookingReducer, initialState);

  const telegramUser = useTelegramUser();

  const openBookingModal = (product) => {
    dispatch({
      type: "OPEN_MODAL",
      product,
      phone: telegramUser?.phone_number || "",
    });
  };

  const handleBooking = async (e) => {
    e.preventDefault();
    if (!bookingState.modal.product) return;

    dispatch({ type: "SUBMIT_START" });

    try {
      const bookingData = {
        product_id: bookingState.modal.product.product_uuid,
        pharmacy_id: bookingState.modal.product.pharmacy_id,
        quantity: bookingState.modal.quantity,
        customer_name: bookingState.form.customer_name.trim(),
        customer_phone: bookingState.form.customer_phone.trim(),
        telegram_id: telegramUser?.id || null,
      };

      if (!bookingData.customer_name) throw new Error("Введите ваше имя");
      if (!bookingData.customer_phone)
        throw new Error("Введите номер телефона");

      const phoneRegex = /^[+]?[1-9][\d]{0,15}$/;
      const cleanPhone = bookingData.customer_phone.replace(/[^\d+]/g, "");
      if (!phoneRegex.test(cleanPhone))
        throw new Error("Введите корректный номер телефона");

      const order = await bookingApi.createOrder(bookingData);

      dispatch({ type: "SUBMIT_SUCCESS", order });
      setTimeout(() => dispatch({ type: "CLOSE_MODAL" }), 3000);
    } catch (error) {
      let errorMessage = "Ошибка при бронировании";
      if (error.response) {
        const serverError = error.response.data;
        errorMessage =
          serverError.detail ||
          (typeof serverError === "string"
            ? serverError
            : serverError.message || errorMessage);
      } else if (error.request) {
        errorMessage = "Ошибка сети. Проверьте подключение к интернету.";
      } else {
        errorMessage = error.message;
      }
      dispatch({ type: "SUBMIT_ERROR", error: errorMessage });
    }
  };

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return "0";
    if (num % 1 === 0) return num.toString();
    return num.toFixed(3).replace(/\.?0+$/, "");
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Недавно";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 60) return `${diffMins} мин назад`;
    if (diffHours < 24) return `${diffHours} ч назад`;
    return `${diffDays} дн назад`;
  };

  const groupedResults = useMemo(() => {
    const grouped = {};
    results
      .filter((item) => (parseFloat(item.quantity) || 0) > 0)
      .forEach((item) => {
        const productUuid = item.product_uuid || item.uuid || item.id;
        const pharmacyId = item.pharmacy_id || item.pharmacy_number;
        const key = `${pharmacyId}-${item.name}-${item.form}-${item.manufacturer}`;

        if (!grouped[key]) {
          grouped[key] = {
            ...item,
            product_uuid: productUuid,
            pharmacy_id: pharmacyId,
            quantities: [parseFloat(item.quantity) || 0],
            prices: [parseFloat(item.price) || 0],
            working_hours:
              item.working_hours || item.opening_hours || "9:00-21:00",
          };
        } else {
          grouped[key].quantities.push(parseFloat(item.quantity) || 0);
          if (!grouped[key].prices.includes(parseFloat(item.price) || 0)) {
            grouped[key].prices.push(parseFloat(item.price) || 0);
          }
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

    return Object.values(grouped).map((item) => ({
      ...item,
      quantity: item.quantities.reduce((sum, q) => sum + q, 0),
      price: Math.min(...item.prices),
      hasMultiplePrices: item.prices.length > 1,
      originalPrices: item.prices,
    }));
  }, [results]);

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      <BookingModal
        bookingState={bookingState}
        onFormChange={(field, value) =>
          dispatch({ type: "UPDATE_FORM", field, value })
        }
        onQuantityChange={(value) =>
          dispatch({ type: "UPDATE_QUANTITY", value })
        }
        onClose={() => dispatch({ type: "CLOSE_MODAL" })}
        onSubmit={handleBooking}
      />

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
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
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
              >
                <svg
                  className="w-5 h-5 mr-2"
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
          </div>

          {loading ? (
            <SkeletonList count={5} />
          ) : groupedResults.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-500 text-lg">Ничего не найдено</p>
              <p className="text-gray-400 text-sm mt-2">Попробуйте изменить параметры поиска</p>
            </div>
          ) : (
            <>
              {isTelegram ? (
                <div
                  className="space-y-3"
                  role="list"
                  aria-label="Результаты поиска лекарств"
                >
                  {groupedResults.map((item, index) => (
                    <ResultItemTelegram
                      key={index}
                      item={item}
                      formatQuantity={formatQuantity}
                      formatDate={formatDate}
                      onBook={openBookingModal}
                    />
                  ))}
                </div>
              ) : (
                <div
                  className="space-y-4"
                  role="list"
                  aria-label="Результаты поиска лекарств"
                >
                  {groupedResults.map((item, index) => (
                    <ResultItemWeb
                      key={index}
                      item={item}
                      formatQuantity={formatQuantity}
                      formatDate={formatDate}
                      onBook={openBookingModal}
                    />
                  ))}
                </div>
              )}

              <SearchResultsPagination
                pagination={pagination}
                onPageChange={onPageChange}
                loading={loading}
              />
            </>
          )}
        </div>
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && !loading && (
        <SearchResultsPagination
          pagination={pagination}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}
