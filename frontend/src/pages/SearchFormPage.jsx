import { useState, useEffect, useRef } from 'react';
import {
  useNavigate,
  useSearchParams,
} from 'react-router-dom';
import SearchBar from '../components/SearchBar';
import Footer from '../components/Footer';
import { api } from '../api/client';
import { logger } from '../utils/logger';
import { useTelegramWebApp } from '../telegram/TelegramContext';

const DEFAULT_CITIES = [
  'Минск',
  'Гомель',
  'Брест',
  'Гродно',
  'Витебск',
  'Могилев',
];

export default function SearchFormPage() {
  const [cities, setCities] = useState(DEFAULT_CITIES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const abortRef = useRef(null);
  const { tg, isTelegram } = useTelegramWebApp();

  // Get initial values from URL params
  const initialName = searchParams.get('q') || '';
  const initialCity = searchParams.get('city') || '';

  // Load cities
  useEffect(() => {
    let cancelled = false;

    const fetchCities = async () => {
      try {
        const response = await api.get('/cities/');
        const data = response.data;

        const citiesList = Array.isArray(data)
          ? data
          : (data?.results ?? data?.items ?? []);

        if (!cancelled) {
          if (
            Array.isArray(citiesList) &&
            citiesList.length > 0
          ) {
            setCities(citiesList);
          } else {
            setCities(DEFAULT_CITIES);
          }
        }
      } catch (error) {
        logger.error('Error fetching cities:', error);
        if (!cancelled) {
          setCities(DEFAULT_CITIES);
        }
      }
    };

    const scheduleFetch = () => {
      if (
        typeof window !== 'undefined' &&
        'requestIdleCallback' in window
      ) {
        return window.requestIdleCallback(() => {
          void fetchCities();
        });
      }

      return window.setTimeout(() => {
        void fetchCities();
      }, 0);
    };

    const timerId = scheduleFetch();

    return () => {
      cancelled = true;
      if (typeof window !== 'undefined') {
        if (
          'cancelIdleCallback' in window &&
          typeof timerId === 'number'
        ) {
          window.cancelIdleCallback(timerId);
        } else {
          window.clearTimeout(timerId);
        }
      }
    };
  }, []);

  // Handle Telegram back button
  useEffect(() => {
    if (!isTelegram || !tg) return;
    tg.BackButton.hide();
  }, [isTelegram, tg]);

  const handleSearch = async (name, city) => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/search-fts/', {
        params: {
          q: name,
          city: city || '',
          page: 1,
          size: 20,
        },
        signal,
      });

      const responseData = response.data || {};

      // Navigate to form selection page with search context
      navigate('/search/form-selection', {
        state: {
          searchData: { name, city: city || '' },
          searchContext: {
            availableCombinations:
              responseData.available_combinations || [],
            totalFound: responseData.total_found || 0,
          },
        },
      });
    } catch (error) {
      const isCanceled =
        error?.name === 'CanceledError' ||
        error?.name === 'AbortError' ||
        error?.code === 'ERR_CANCELED';

      if (isCanceled) return;

      logger.error('Search error:', error);
      setError('Ошибка при поиске. Попробуйте еще раз.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Поиск лекарств
          </h1>
          <p className="text-gray-600">
            Найдите нужные препараты в аптеках вашего города
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
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
              <span className="text-red-800 text-sm">
                {error}
              </span>
            </div>
          </div>
        )}

        <SearchBar
          cities={cities}
          onSearch={handleSearch}
          loading={loading}
          currentCity={initialCity}
          isTelegram={isTelegram}
          initialName={initialName}
        />
      </div>

      <Footer />
    </div>
  );
}
