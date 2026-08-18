import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useReducer,
} from 'react';
import {
  useParams,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import Footer from '../components/Footer';
import { api } from '../api/client';
import { logger } from '../utils/logger';
import { useTelegramWebApp } from '../telegram/TelegramContext';
import BookingModal from '../components/BookingModal';
import {
  bookingReducer,
  initialState,
} from '../hooks/useBookingReducer';
import { useTelegramUser } from '../telegram/TelegramContext';
import { bookingApi } from '../api/client';

export default function ProductDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { tg, isTelegram } = useTelegramWebApp();
  const telegramUser = useTelegramUser();

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const [bookingState, dispatch] = useReducer(
    bookingReducer,
    initialState,
  );

  // Get product data from location state or fetch it
  const locationProduct = location.state?.product;

  useEffect(() => {
    const fetchProduct = async () => {
      if (locationProduct) {
        setProduct(locationProduct);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();
      const { signal } = abortRef.current;

      try {
        // Assuming there's an API endpoint to get product details by ID
        // If not, we'll use the data from location state only
        const response = await api.get(`/products/${id}`, {
          signal,
        });
        setProduct(response.data);
      } catch (error) {
        if (error.name !== 'CanceledError') {
          logger.error('Error fetching product:', error);
          setError(
            'Ошибка при загрузке информации о товаре',
          );
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [id, locationProduct]);

  // Handle Telegram back button — go back in history
  const onTgBack = useCallback(() => {
    navigate(-1);
  }, [navigate]);

  useEffect(() => {
    if (!isTelegram || !tg) return;
    tg.BackButton.show();
    tg.BackButton.onClick(onTgBack);

    return () => {
      tg.BackButton.offClick(onTgBack);
    };
  }, [isTelegram, tg, onTgBack]);

  const openBookingModal = useCallback(() => {
    if (!product) return;
    dispatch({
      type: 'OPEN_MODAL',
      product,
      phone: telegramUser?.phone_number || '',
    });
  }, [product, telegramUser]);

  const handleBooking = async (e) => {
    e.preventDefault();
    if (!bookingState.modal.product) return;

    dispatch({ type: 'SUBMIT_START' });

    try {
      const bookingData = {
        product_id: bookingState.modal.product.product_uuid,
        pharmacy_id: bookingState.modal.product.pharmacy_id,
        quantity: bookingState.modal.quantity,
        customer_name:
          bookingState.form.customer_name.trim(),
        customer_phone:
          bookingState.form.customer_phone.trim(),
        telegram_id: telegramUser?.id || null,
      };

      if (!bookingData.customer_name)
        throw new Error('Введите ваше имя');
      if (!bookingData.customer_phone)
        throw new Error('Введите номер телефона');

      const phoneRegex = /^[+]?[1-9][\d]{0,15}$/;
      const cleanPhone = bookingData.customer_phone.replace(
        /[^\d+]/g,
        '',
      );
      if (!phoneRegex.test(cleanPhone))
        throw new Error(
          'Введите корректный номер телефона',
        );

      const order =
        await bookingApi.createOrder(bookingData);

      dispatch({ type: 'SUBMIT_SUCCESS', order });
      setTimeout(
        () => dispatch({ type: 'CLOSE_MODAL' }),
        3000,
      );
    } catch (error) {
      let errorMessage = 'Ошибка при бронировании';
      if (error.response) {
        const serverError = error.response.data;
        errorMessage =
          serverError.detail ||
          (typeof serverError === 'string'
            ? serverError
            : serverError.message || errorMessage);
      } else if (error.request) {
        errorMessage =
          'Ошибка сети. Проверьте подключение к интернету.';
      } else {
        errorMessage = error.message;
      }
      dispatch({
        type: 'SUBMIT_ERROR',
        error: errorMessage,
      });
    }
  };

  const formatQuantity = (quantity) => {
    const num = parseFloat(quantity);
    if (isNaN(num)) return '0';
    if (num % 1 === 0) return num.toString();
    return num.toFixed(3).replace(/\.?0+$/, '');
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Недавно';
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

  const handleBack = () => {
    navigate(-1);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
          <p className="text-gray-500 text-sm">
            Загрузка...
          </p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">
            {error || 'Товар не найден'}
          </p>
          <button
            onClick={handleBack}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Вернуться к результатам
          </button>
        </div>
      </div>
    );
  }

  const mapQuery = encodeURIComponent(
    `${product.pharmacy_name} №${product.pharmacy_number}, ${product.pharmacy_city}${product.pharmacy_district ? `, ${product.pharmacy_district}` : ''}, ${product.pharmacy_address}`,
  );
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <BookingModal
          bookingState={bookingState}
          onFormChange={(field, value) =>
            dispatch({ type: 'UPDATE_FORM', field, value })
          }
          onQuantityChange={(value) =>
            dispatch({ type: 'UPDATE_QUANTITY', value })
          }
          onClose={() => dispatch({ type: 'CLOSE_MODAL' })}
          onSubmit={handleBooking}
        />

        <div className="mb-8">
          <button
            onClick={handleBack}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Вернуться к результатам
          </button>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {product.name}
          </h1>
          <p className="text-gray-600">
            {product.form} •{' '}
            {product.manufacturer ||
              'Производитель не указан'}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-6">
            <div className="flex-1">
              <div className="text-3xl font-bold text-telegram-primary mb-2">
                {product.price} Br
              </div>
              <div className="text-lg text-gray-800 font-medium">
                {formatQuantity(product.quantity)} уп. в
                наличии
              </div>
            </div>

            <button
              onClick={openBookingModal}
              disabled={product.quantity <= 0}
              className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-lg"
            >
              {product.quantity <= 0
                ? 'Нет в наличии'
                : 'Забронировать'}
            </button>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Информация об аптеке
            </h2>

            <div className="space-y-4">
              <div className="flex items-start">
                <svg
                  className="w-6 h-6 mr-3 flex-shrink-0 text-gray-600"
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
                  <div className="font-semibold text-gray-900">
                    {product.pharmacy_name} №
                    {product.pharmacy_number}
                  </div>
                  <div className="text-gray-800 mt-1">
                    {product.pharmacy_city}
                    {product.pharmacy_district && (
                      <span className="text-gray-600">
                        , {product.pharmacy_district}
                      </span>
                    )}
                    , {product.pharmacy_address}
                  </div>
                </div>
              </div>

              <div className="flex items-start">
                <svg
                  className="w-6 h-6 mr-3 flex-shrink-0 text-gray-600"
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
                <div>
                  <div className="font-semibold text-gray-900">
                    Телефон:
                  </div>
                  <div className="text-gray-800">
                    {product.pharmacy_phone}
                  </div>
                </div>
              </div>

              <div className="flex items-start">
                <svg
                  className="w-6 h-6 mr-3 flex-shrink-0 text-gray-600"
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
                  <div className="font-semibold text-gray-900">
                    Время работы:
                  </div>
                  <div className="text-gray-800">
                    {product.working_hours ||
                      'Уточняйте в аптеке'}
                  </div>
                </div>
              </div>

              <div className="flex items-start">
                <svg
                  className="w-6 h-6 mr-3 flex-shrink-0 text-gray-600"
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
                <div>
                  <div className="font-semibold text-gray-900">
                    На карте:
                  </div>
                  <a
                    href={mapUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Посмотреть на карте Google
                  </a>
                </div>
              </div>

              <div className="flex items-start">
                <svg
                  className="w-6 h-6 mr-3 flex-shrink-0 text-gray-600"
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
                  <div className="font-semibold text-gray-900">
                    Обновлено:
                  </div>
                  <div className="text-gray-800">
                    {formatDate(product.updated_at)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
