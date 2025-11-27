

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
    <div className="fixed inset-0 bg-gradient-to-br from-gray-900/80 via-blue-900/40 to-purple-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto animate-scaleIn">
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
    <div className="text-center py-4">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">
        Бронирование успешно!
      </h3>
      <p className="text-gray-600 mb-2">
        Номер заказа: <strong className="text-gray-900">{orderInfo?.uuid?.substring(0, 8)}...</strong>
      </p>
      <p className="text-gray-500 text-sm mb-6">
        Ожидайте звонка из аптеки для подтверждения.
      </p>
      <button
        onClick={onClose}
        className="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold py-3 px-4 rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl"
      >
        Готово
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Бронирование
        </h2>
        <button
          onClick={onClose}
          disabled={loading}
          className="p-2 hover:bg-gray-100 rounded-xl transition-colors duration-200 disabled:opacity-50"
        >
          <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {product && (
        <ProductInfo product={product} formatQuantity={formatQuantity} />
      )}

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
    <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
      <h3 className="font-bold text-gray-900 text-lg mb-1">{product.name}</h3>
      <p className="text-sm text-gray-600 mb-2">{product.form}</p>
      <div className="space-y-1 text-sm">
        <p className="text-gray-700">
          <span className="font-semibold">Аптека:</span> {product.pharmacy_name} №{product.pharmacy_number}
        </p>
        <p className="text-gray-700">
          <span className="font-semibold">Адрес:</span> {product.pharmacy_address}
        </p>
        <div className="flex justify-between items-center pt-2">
          <span className="text-sm font-semibold text-gray-900">
            Доступно: {formatQuantity(product.quantity)} уп.
          </span>
          <span className="text-lg font-bold text-blue-600">
            {product.price} Br
          </span>
        </div>
      </div>
    </div>
  );
}

function ErrorDisplay({ error }) {
  return (
    <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl">
      <div className="flex items-center">
        <svg className="w-5 h-5 text-red-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
        <span className="text-red-800 font-medium">{error}</span>
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
    <form onSubmit={onBooking} className="space-y-5">
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

function FormField({
  label,
  type,
  value,
  onChange,
  disabled,
  placeholder,
  hint,
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-2">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        disabled={disabled}
        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200 bg-white"
        placeholder={placeholder}
      />
      {hint && <p className="text-xs text-gray-500 mt-2">{hint}</p>}
    </div>
  );
}

function QuantitySelector({
  product,
  quantity,
  loading,
  onQuantityUpdate,
  getPackagingText,
}) {
  const totalPrice = product ? product.price * quantity : 0;

  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-2">
        Количество упаковок *
      </label>
      <select
        value={quantity}
        onChange={(e) => onQuantityUpdate(parseInt(e.target.value))}
        disabled={loading}
        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200 bg-white appearance-none"
      >
        {[...Array(Math.min(10, product?.quantity || 1)).keys()].map((i) => (
          <option key={i + 1} value={i + 1}>
            {i + 1} {getPackagingText(i + 1)}
          </option>
        ))}
      </select>
      <div className="flex justify-between items-center mt-3 p-3 bg-gray-50 rounded-lg">
        <span className="text-sm font-medium text-gray-600">Итоговая сумма:</span>
        <span className="text-lg font-bold text-blue-600">{totalPrice} Br</span>
      </div>
    </div>
  );
}

function FormActions({ product, quantity, loading, onClose }) {
  const totalPrice = product ? product.price * quantity : 0;

  return (
    <div className="flex gap-3 pt-4">
      <button
        type="submit"
        disabled={loading}
        className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold py-4 px-6 rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-h-[52px]"
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Бронируем...
          </>
        ) : (
          `Забронировать · ${totalPrice} Br`
        )}
      </button>
      <button
        type="button"
        onClick={onClose}
        disabled={loading}
        className="flex-1 bg-white text-gray-700 font-semibold py-4 px-6 rounded-xl border border-gray-200 hover:bg-gray-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed min-h-[52px]"
      >
        Отмена
      </button>
    </div>
  );
}
