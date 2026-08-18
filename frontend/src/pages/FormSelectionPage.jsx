import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import FormSelection from '../components/FormSelection';
import Footer from '../components/Footer';
import { api } from '../api/client';
import { logger } from '../utils/logger';
import { useTelegramWebApp } from '../telegram/TelegramContext';

export default function FormSelectionPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const navigate = useNavigate();
  const location = useLocation();
  const abortRef = useRef(null);
  const { tg, isTelegram } = useTelegramWebApp();

  // Get search data from location state
  const searchData = location.state?.searchData || { name: '', city: '' };
  const searchContext = location.state?.searchContext || { availableCombinations: [], totalFound: 0 };

  // Handle Telegram back button
  const onTgBack = useCallback(() => {
    navigate('/search');
  }, [navigate]);

  useEffect(() => {
    if (!isTelegram || !tg) return;
    tg.BackButton.show();
    tg.BackButton.onClick(onTgBack);

    return () => {
      tg.BackButton.offClick(onTgBack);
    };
  }, [isTelegram, tg, onTgBack]);

  const handleFormSelect = async (name, form, manufacturer, country) => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setLoading(true);
    setError(null);
    try {
      const params = {
        q: name,
        page: 1,
        size: 50,
      };

      if (form) params.form = form;
      if (manufacturer) params.manufacturer = manufacturer;
      if (country) params.country = country;
      if (searchData.city) params.city = searchData.city;

      const response = await api.get('/search-fts/', {
        params,
        signal,
      });

      const updatedSearchData = {
        ...searchData,
        name: name,
        form,
        manufacturer,
        country,
      };

      // Navigate to results page with search data and results
      navigate('/search/results', {
        state: {
          searchData: updatedSearchData,
          results: response.data.items || [],
          pagination: {
            page: response.data.page || 1,
            size: 50,
            total: response.data.total || 0,
            totalPages: response.data.total_pages || 1,
          },
        },
      });
    } catch (error) {
      const isCanceled =
        error?.name === 'CanceledError' ||
        error?.name === 'AbortError' ||
        error?.code === 'ERR_CANCELED';

      if (isCanceled) return;

      logger.error('Form selection error:', error);
      setError('Ошибка при загрузке результатов.');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/search');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
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
            Назад к поиску
          </button>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Выбор формы препарата
          </h1>
          <p className="text-gray-600">
            {searchData.name && `Результаты для: ${searchData.name}`}
            {searchData.city && ` в ${searchData.city}`}
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
          <FormSelection
            availableCombinations={searchContext.availableCombinations}
            totalFound={searchContext.totalFound}
            onFormSelect={handleFormSelect}
            loading={loading}
          />
        )}
      </div>
      
      <Footer />
    </div>
  );
}