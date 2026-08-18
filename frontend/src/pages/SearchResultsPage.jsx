import React, {
  useState,
  useCallback,
  useMemo,
  useRef,
  useEffect,
} from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import SearchResults from '../components/SearchResults';
import Footer from '../components/Footer';
import { api } from '../api/client';
import { logger } from '../utils/logger';
import { useTelegramWebApp } from '../telegram/TelegramContext';

export default function SearchResultsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    size: 50,
    total: 0,
    totalPages: 1,
  });

  const navigate = useNavigate();
  const location = useLocation();
  const abortRef = useRef(null);
  const { tg, isTelegram } = useTelegramWebApp();

  // Get search data from location state - wrapped in useMemo to avoid
  // creating new object on every render
  const searchData = useMemo(
    () =>
      location.state?.searchData || {
        name: '',
        city: '',
        form: '',
      },
    [location.state?.searchData],
  );
  const initialResults = useMemo(
    () => location.state?.results || [],
    [location.state?.results],
  );
  const initialPagination = useMemo(
    () => ({ page: 1, size: 50, total: 0, totalPages: 1 }),
    [],
  );

  // Initialize state from location state
  useEffect(() => {
    setResults(initialResults);
    setPagination(initialPagination);
  }, [initialResults, initialPagination]);

  // Handle Telegram back button
  const onTgBack = useCallback(() => {
    navigate('/search/form-selection', {
      state: {
        searchData,
        searchContext: location.state?.searchContext,
      },
    });
  }, [navigate, searchData, location.state]);

  useEffect(() => {
    if (!isTelegram || !tg) return;
    tg.BackButton.show();
    tg.BackButton.onClick(onTgBack);

    return () => {
      tg.BackButton.offClick(onTgBack);
    };
  }, [isTelegram, tg, onTgBack]);

  const handlePageChange = async (newPage) => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setLoading(true);
    try {
      const params = {
        q: searchData.name,
        page: newPage,
        size: pagination.size,
      };

      if (searchData.form) params.form = searchData.form;
      if (searchData.manufacturer)
        params.manufacturer = searchData.manufacturer;
      if (searchData.country)
        params.country = searchData.country;
      if (searchData.city) params.city = searchData.city;

      const response = await api.get('/search-fts/', {
        params,
        signal,
      });

      setResults(response.data.items);
      setPagination((prev) => ({
        ...prev,
        page: response.data.page,
        total: response.data.total,
        totalPages: response.data.total_pages,
      }));
    } catch (error) {
      const isCanceled =
        error?.name === 'CanceledError' ||
        error?.name === 'AbortError' ||
        error?.code === 'ERR_CANCELED';

      if (isCanceled) return;

      logger.error('Pagination error:', error);
      setError('Ошибка при загрузке результатов.');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/search/form-selection', {
      state: {
        searchData,
        searchContext: location.state?.searchContext,
      },
    });
  };

  const handleNewSearch = () => {
    navigate('/search');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={handleBack}
              className="flex items-center text-gray-600 hover:text-gray-900"
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
              Назад к выбору формы
            </button>

            <button
              onClick={handleNewSearch}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Новый поиск
            </button>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Результаты поиска
          </h1>
          <p className="text-gray-600">
            {searchData.name &&
              `Препарат: ${searchData.name}`}
            {searchData.form &&
              ` • Форма: ${searchData.form}`}
            {searchData.city &&
              ` • Город: ${searchData.city}`}
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

        {loading && (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          </div>
        )}

        {!loading && (
          <SearchResults
            results={results}
            pagination={pagination}
            onPageChange={handlePageChange}
            loading={loading}
            searchData={searchData}
          />
        )}
      </div>

      <Footer />
    </div>
  );
}
