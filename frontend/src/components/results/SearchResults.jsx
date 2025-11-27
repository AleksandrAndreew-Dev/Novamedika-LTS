import React, { useState } from "react";
import { bookingApi } from "../api/client";
import SearchResultsHeader from "./SearchResultsHeader";
import BookingModal from "./BookingModal";
import ProductCard from "./ProductCard";
import Pagination from "./Pagination";
import EmptyResults from "./EmptyResults";
import LoadingSkeleton from "./LoadingSkeleton";

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
    modal: { isOpen: false, product: null, quantity: 1 },
    form: { customer_name: "", customer_phone: "" },
    loading: false,
    success: false,
    error: null,
    orderInfo: null,
  });

  // Функции для работы с бронированием
  const openBookingModal = (product) => {
    setBookingState({
      modal: { isOpen: true, product, quantity: 1 },
      form: { customer_name: "", customer_phone: "" },
      loading: false,
      success: false,
      error: null,
      orderInfo: null,
    });
  };

  const handleBooking = async (e) => {
    e.preventDefault();
    if (!bookingState.modal.product) return;

    setBookingState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const bookingData = {
        product_id: bookingState.modal.product.uuid,
        pharmacy_id: bookingState.modal.product.pharmacy_id,
        quantity: bookingState.modal.quantity,
        customer_name: bookingState.form.customer_name.trim(),
        customer_phone: bookingState.form.customer_phone.trim(),
      };

      // Валидация (остается без изменений)
      if (!bookingData.customer_name) throw new Error("Введите ваше имя");
      if (!bookingData.customer_phone) throw new Error("Введите номер телефона");

      const phoneRegex = /^[+]?[1-9][\d]{0,15}$/;
      const cleanPhone = bookingData.customer_phone.replace(/[^\d+]/g, "");
      if (!phoneRegex.test(cleanPhone)) throw new Error("Введите корректный номер телефона");

      if (bookingState.modal.quantity > bookingState.modal.product.quantity) {
        throw new Error(`Недостаточно товара. Доступно: ${formatQuantity(bookingState.modal.product.quantity)} уп.`);
      }

      const order = await bookingApi.createOrder(bookingData);

      setBookingState(prev => ({
        ...prev,
        loading: false,
        success: true,
        orderInfo: order,
      }));

      setTimeout(closeBookingModal, 3000);
    } catch (error) {
      // Обработка ошибок (остается без изменений)
      console.error("Booking error:", error);
      let errorMessage = "Ошибка при бронировании";

      if (error.response) {
        const serverError = error.response.data;
        if (serverError.detail) errorMessage = serverError.detail;
        else if (typeof serverError === "string") errorMessage = serverError;
        else if (serverError.message) errorMessage = serverError.message;
      } else if (error.request) {
        errorMessage = "Ошибка сети. Проверьте подключение к интернету.";
      } else {
        errorMessage = error.message;
      }

      setBookingState(prev => ({ ...prev, loading: false, error: errorMessage }));
    }
  };

  const updateBookingForm = (field, value) => {
    setBookingState(prev => ({
      ...prev,
      form: { ...prev.form, [field]: value },
    }));
  };

  const updateBookingQuantity = (quantity) => {
    setBookingState(prev => ({
      ...prev,
      modal: { ...prev.modal, quantity },
    }));
  };

  const closeBookingModal = () => {
    setBookingState({
      modal: { isOpen: false, product: null, quantity: 1 },
      form: { customer_name: "", customer_phone: "" },
      loading: false,
      success: false,
      error: null,
      orderInfo: null,
    });
  };

  // Вспомогательные функции
  const getGroupedResults = () => {
    const grouped = {};
    results.forEach((item) => {
      const key = `${item.pharmacy_number}-${item.name}-${item.form}-${item.manufacturer}`;
      if (!grouped[key]) {
        grouped[key] = {
          ...item,
          quantity: parseFloat(item.quantity) || 0,
          working_hours: item.working_hours || item.opening_hours || "9:00-21:00",
          pharmacy_id: item.pharmacy_id,
        };
      } else {
        grouped[key].quantity += parseFloat(item.quantity) || 0;
        const currentDate = new Date(grouped[key].updated_at);
        const newDate = new Date(item.updated_at);
        if (newDate > currentDate) {
          grouped[key].updated_at = item.updated_at;
          if (item.working_hours || item.opening_hours) {
            grouped[key].working_hours = item.working_hours || item.opening_hours;
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

  const formatDate = (dateString) => {
    if (!dateString) return "Недавно";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} мин назад`;
    else if (diffHours < 24) return `${diffHours} ч назад`;
    else return `${diffDays} дн назад`;
  };

  const groupedResults = getGroupedResults();

  return (
    <div className={`${isTelegram ? "p-2" : "p-4"} max-w-6xl mx-auto`}>
      {/* Модальное окно бронирования */}
      <BookingModal
        isOpen={bookingState.modal.isOpen}
        product={bookingState.modal.product}
        quantity={bookingState.modal.quantity}
        formData={bookingState.form}
        loading={bookingState.loading}
        success={bookingState.success}
        error={bookingState.error}
        orderInfo={bookingState.orderInfo}
        onClose={closeBookingModal}
        onBooking={handleBooking}
        onFormUpdate={updateBookingForm}
        onQuantityUpdate={updateBookingQuantity}
      />

      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        <SearchResultsHeader
          searchData={searchData}
          loading={loading}
          onBackToForms={onBackToForms}
          onNewSearch={onNewSearch}
        />

        <div className="p-4 md:p-6">
          <SearchSummary searchData={searchData} pagination={pagination} />

          {loading && <LoadingSkeleton />}

          <ProductList
            results={groupedResults}
            isTelegram={isTelegram}
            loading={loading}
            onBook={openBookingModal}
            formatQuantity={formatQuantity}
            formatDate={formatDate}
          />

          {groupedResults.length === 0 && !loading && (
            <EmptyResults onBackToForms={onBackToForms} onNewSearch={onNewSearch} />
          )}

          <Pagination
            pagination={pagination}
            loading={loading}
            onPageChange={onPageChange}
          />
        </div>
      </div>
    </div>
  );
}

function SearchSummary({ searchData, pagination }) {
  return (
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
  );
}

function ProductList({ results, isTelegram, loading, onBook, formatQuantity, formatDate }) {
  if (loading || results.length === 0) return null;

  return (
    <div className={isTelegram ? "space-y-3" : "space-y-4"} role="list" aria-label="Результаты поиска лекарств">
      {results.map((item, index) => (
        <ProductCard
          key={index}
          item={item}
          isTelegram={isTelegram}
          onBook={onBook}
          formatQuantity={formatQuantity}
          formatDate={formatDate}
        />
      ))}
    </div>
  );
}
