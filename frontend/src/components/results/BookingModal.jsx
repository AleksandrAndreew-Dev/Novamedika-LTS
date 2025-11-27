import React from "react";

export default function BookingModal({
  isOpen,
  product,
  quantity,
  formData,
  loading,
  success,
  error,
  orderInfo,
  onClose,
  onBooking,
  onFormUpdate,
  onQuantityUpdate,
}) {
  if (!isOpen) return null;

  const getPackagingText = (qty) => {
    if (qty === 1) return "упаковка";
    if (qty >= 2 && qty <= 4) return "упаковки";
    return "упаковок";
  };

  const formatQuantity = (qty) => {
    const num = parseFloat(qty);
    if (isNaN(num)) return "0";
    const formatted = Math.round(num * 1000) / 1000;
    return formatted.toString().replace(/\.?0+$/, "");
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {success ? (
            <SuccessView orderInfo={orderInfo} onClose={onClose} />
          ) : (
            <BookingForm
              product={product}
              quantity={quantity}
              formData={formData}
              loading={loading}
              error={error}
              onClose={onClose}
              onBooking={onBooking}
              onFormUpdate={onFormUpdate}
              onQuantityUpdate={onQuantityUpdate}
              getPackagingText={getPackagingText}
              formatQuantity={formatQuantity}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function SuccessView({ orderInfo, onClose }) {
  return (
    <div className="text-center">
      <div className="text-green-500 text-6xl mb-4">✓</div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        Бронирование успешно!
      </h3>
      <p className="text-gray-600 mb-2">
        Номер заказа:{" "}
        <strong>{orderInfo?.uuid?.substring(0, 8)}...</strong>
      </p>
      <p className="text-gray-600 mb-4 text-sm">
        Ожидайте звонка из аптеки для подтверждения.
      </p>
      <button
        onClick={onClose}
        className="w-full bg-telegram-primary text-gray-900 font-medium py-3 px-4 rounded-lg hover:bg-blue-600 transition-colors"
      >
        Закрыть
      </button>
    </div>
  );
}

function BookingForm({
  product,
  quantity,
  formData,
  loading,
  error,
  onClose,
  onBooking,
  onFormUpdate,
  onQuantityUpdate,
  getPackagingText,
  formatQuantity,
}) {
  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          Бронирование препарата
        </h2>
        <button
          onClick={onClose}
          disabled={loading}
          className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {product && <ProductInfo product={product} formatQuantity={formatQuantity} />}

      {error && <ErrorDisplay error={error} />}

      <BookingFormFields
        product={product}
        quantity={quantity}
        formData={formData}
        loading={loading}
        onBooking={onBooking}
        onFormUpdate={onFormUpdate}
        onQuantityUpdate={onQuantityUpdate}
        onClose={onClose}
        getPackagingText={getPackagingText}
      />
    </>
  );
}

function ProductInfo({ product, formatQuantity }) {
  return (
    <div className="mb-6 p-4 bg-gray-50 rounded-lg">
      <h3 className="font-semibold text-gray-900 text-lg">{product.name}</h3>
      <p className="text-sm text-gray-600">{product.form}</p>
      <p className="text-sm text-gray-600">
        {product.pharmacy_name} №{product.pharmacy_number}
      </p>
      <p className="text-sm text-gray-600">Адрес: {product.pharmacy_address}</p>
      <p className="text-sm font-medium text-gray-700 mt-2">
        Доступно: {formatQuantity(product.quantity)} уп. • Цена: {product.price} Br
      </p>
    </div>
  );
}

function ErrorDisplay({ error }) {
  return (
    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
      <div className="flex items-center">
        <svg className="w-5 h-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-red-800 text-sm">{error}</span>
      </div>
    </div>
  );
}

function BookingFormFields({
  product,
  quantity,
  formData,
  loading,
  onBooking,
  onFormUpdate,
  onQuantityUpdate,
  onClose,
  getPackagingText,
}) {
  return (
    <form onSubmit={onBooking} className="space-y-4">
      <FormField
        label="Ваше имя *"
        type="text"
        value={formData.customer_name}
        onChange={(value) => onFormUpdate("customer_name", value)}
        disabled={loading}
        placeholder="Иван Иванов"
      />

      <FormField
        label="Телефон *"
        type="tel"
        value={formData.customer_phone}
        onChange={(value) => onFormUpdate("customer_phone", value)}
        disabled={loading}
        placeholder="+375 XX XXX-XX-XX"
        hint="Формат: +375XXXXXXXXX или 80XXXXXXXXX"
      />

      <QuantitySelector
        product={product}
        quantity={quantity}
        loading={loading}
        onQuantityUpdate={onQuantityUpdate}
        getPackagingText={getPackagingText}
      />

      <FormActions
        product={product}
        quantity={quantity}
        loading={loading}
        onClose={onClose}
      />
    </form>
  );
}

function FormField({ label, type, value, onChange, disabled, placeholder, hint }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent disabled:opacity-50"
        placeholder={placeholder}
      />
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

function QuantitySelector({ product, quantity, loading, onQuantityUpdate, getPackagingText }) {
  const totalPrice = product ? product.price * quantity : 0;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Количество упаковок *
      </label>
      <select
        value={quantity}
        onChange={(e) => onQuantityUpdate(parseInt(e.target.value))}
        disabled={loading}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-telegram-primary focus:border-transparent disabled:opacity-50"
      >
        {[...Array(Math.min(10, product?.quantity || 1)).keys()].map((i) => (
          <option key={i + 1} value={i + 1}>
            {i + 1} {getPackagingText(i + 1)}
          </option>
        ))}
      </select>
      <p className="text-xs text-gray-500 mt-1">
        Итоговая сумма: <strong>{totalPrice} Br</strong>
      </p>
    </div>
  );
}

function FormActions({ product, quantity, loading, onClose }) {
  const totalPrice = product ? product.price * quantity : 0;

  return (
    <div className="flex gap-3 pt-2">
      <button
        type="submit"
        disabled={loading}
        className="flex-1 bg-telegram-primary text-gray-900 font-medium py-3 px-4 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
            Бронируем...
          </>
        ) : (
          `Забронировать за ${totalPrice} Br`
        )}
      </button>
      <button
        type="button"
        onClick={onClose}
        disabled={loading}
        className="flex-1 bg-gray-100 text-gray-800 font-medium py-3 px-4 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Отмена
      </button>
    </div>
  );
}
