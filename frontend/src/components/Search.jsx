import React, { useState, useEffect } from "react";
import SearchBar from "./SearchBar";
import FormSelection from "./FormSelection";
import SearchResults from "./SearchResults";
import { useTelegramWebApp } from "../telegram/TelegramWebApp";
import { api } from "../api/client";

export default function Search() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [cities, setCities] = useState([]);
  const [searchData, setSearchData] = useState({
    name: "",
    city: "",
    form: "",
  });
  const [searchContext, setSearchContext] = useState(null);
  const [results, setResults] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    size: 50, // Увеличил количество результатов на странице
    total: 0,
    totalPages: 1,
  });
  const [error, setError] = useState(null);

  const { tg, isTelegram } = useTelegramWebApp();

  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await api.get("/cities/");
        const data = response.data;

        // безопасность: привести результат к массиву
        const cities = Array.isArray(data)
          ? data
          : data?.results ?? data?.items ?? [];
        if (!Array.isArray(cities)) {
          // если всё ещё не массив — fallback
          setCities([
            "Минск",
            "Гомель",
            "Брест",
            "Гродно",
            "Витебск",
            "Могилев",
          ]);
        } else {
          setCities(cities);
        }
      } catch (error) {
        console.error("Error fetching cities:", error);
        setCities(["Минск", "Гомель", "Брест", "Гродно", "Витебск", "Могилев"]);
      }
    };
    fetchCities();
  }, []);

  useEffect(() => {
    if (!isTelegram || !tg) return;

    if (step === 1) {
      tg.BackButton.hide();
    } else {
      tg.BackButton.show();
      tg.BackButton.onClick(() => {
        if (step === 2) {
          setStep(1);
        } else if (step === 3) {
          setStep(2);
        }
      });
    }

    return () => {
      tg.BackButton.offClick();
    };
  }, [step, isTelegram, tg]);
  // Search.jsx - исправить обработку ответа API
  const handleInitialSearch = async (name, city) => {
  setLoading(true);
  setError(null);
  try {
    const response = await api.get("/search-advanced/", {
      params: {
        name,
        city: city || "",
        use_fuzzy: true,
        page: 1,
        size: 20,
      },
    });

    const responseData = response.data || {};

    setSearchData({ name, city: city || "" });
    setSearchContext({
      availableCombinations: responseData.available_combinations || [],
      totalFound: responseData.total_found || 0,
    });
    setStep(2);
  } catch (error) {
    console.error("Search error:", error);
    setError("Ошибка при поиске. Попробуйте еще раз.");
    // ... остальная обработка ошибок
  } finally {
    setLoading(false);
  }
};

  // Обновим функцию handleFormSelect
  // Search.jsx - исправленный handleFormSelect
  // Search.jsx - исправленная функция handleFormSelect
// В функции handleFormSelect обновляем передачу параметров:
const handleFormSelect = async (name, form, manufacturer, country) => {
  setLoading(true);
  setError(null);
  try {
    const params = {
      name: name, // Используем реальное название из выбранной комбинации
      form: form,
      manufacturer: manufacturer,
      country: country,
      page: 1,
      size: pagination.size,
      use_fuzzy: true,
    };

    if (searchData.city) {
      params.city = searchData.city;
    }

    const response = await api.get("/search-advanced/", { params });

    setSearchData((prev) => ({
      ...prev,
      name: name, // Сохраняем реальное название
      form,
      manufacturer,
      country,
    }));

    setResults(response.data.items || []);
    setPagination((prev) => ({
      ...prev,
      page: response.data.page || 1,
      total: response.data.total || 0,
      totalPages: response.data.total_pages || 1,
    }));
    setStep(3);
  } catch (error) {
    console.error("Form selection error:", error);
    setError("Ошибка при загрузке результатов.");
    // ... обработка ошибок
  } finally {
    setLoading(false);
  }
};

  const handlePageChange = async (newPage) => {
    setLoading(true);
    try {
      const params = {
        page: newPage,
        size: pagination.size,
        use_fuzzy: true, // Добавьте этот параметр
      };

      // Приоритет: searchId > прямой поиск
      if (searchContext?.searchId) {
        params.search_id = searchContext.searchId;
        params.form = searchData.form;
      } else {
        params.name = searchData.name;
        params.city = searchData.city;
        params.form = searchData.form;
      }

      const response = await api.get("/search-advanced/", {
        // Измените эндпоинт
        params,
      });

      setResults(response.data.items);
      setPagination((prev) => ({
        ...prev,
        page: response.data.page,
        total: response.data.total,
        totalPages: response.data.total_pages,
      }));
    } catch (error) {
      console.error("Pagination error:", error);
      setError("Ошибка при загрузке страницы.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`min-h-screen ${
        isTelegram ? "bg-transparent" : "bg-telegram-bg"
      }`}
    >
      {/* Показываем кастомный header только вне Telegram */}
      {!isTelegram && (
        <div className="bg-white shadow-sm border-b border-telegram-border">
          <div className="text-center py-4 px-4 relative">
            {/* Кнопка назад для десктопа */}
            {step > 1 && (
              <button
                onClick={() => {
                  if (step === 2) {
                    setStep(1);
                  } else if (step === 3) {
                    setStep(2);
                  }
                }}
                disabled={loading}
                className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center text-sm"
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Назад
              </button>
            )}
            <div className="text-gray-600 text-sm mb-1">Сеть Аптек</div>
            <h1 className="text-2xl font-bold text-telegram-primary m-0">
              <span className="text-orange-500">Н</span>ова
              <span className="text-orange-500">М</span>едика
            </h1>
            <div className="text-gray-600 text-sm mt-1">
              Справочная служба CI CD
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className={isTelegram ? "p-2" : "p-4"}>
        <div className={isTelegram ? "max-w-full" : "max-w-4xl mx-auto"}>
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
                <span className="text-red-800 text-sm">{error}</span>
              </div>
            </div>
          )}
          {step === 1 && (
            <SearchBar
              cities={cities}
              onSearch={handleInitialSearch}
              loading={loading}
              currentCity={searchData.city}
              isTelegram={isTelegram}
            />
          )}
          {loading && (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-telegram-primary"></div>
            </div>
          )}

          {step === 2 && searchContext && (
  <FormSelection
    availableCombinations={searchContext.availableCombinations || []}
    searchData={searchData}
    onFormSelect={handleFormSelect}
    onBack={() => setStep(1)}
    loading={loading}
    isTelegram={isTelegram}
  />
)}
          {step === 3 && (
            <SearchResults
              results={results}
              searchData={searchData}
              pagination={pagination}
              onPageChange={handlePageChange}
              onNewSearch={() => {
                // Полный сброс к начальному состоянию
                setStep(1);
                setSearchData({ name: "", city: "", form: "" });
                setResults([]);
                setSearchContext(null);
              }}
              onBackToForms={() => setStep(2)} // Добавьте эту строку
              loading={loading}
              isTelegram={isTelegram}
            />
          )}
        </div>
      </div>

      {/* Footer */}
      {!isTelegram && (
        <div className="bg-white border-t border-telegram-border mt-8">
          <div className="max-w-4xl mx-auto py-6 px-4">
            <div className="space-y-4">
              <div className="flex flex-wrap justify-center gap-4 text-sm">
                <a
                  href="/"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Поиск
                </a>
                <a
                  href="/terms"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Условия использования
                </a>
                <a
                  href="/cookie-policy"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Cookie
                </a>
                <a
                  href="/pharmacies-nearby"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Аптеки рядом
                </a>
                <a
                  href="/contacts"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Контакты
                </a>
                <a
                  href="/help"
                  className="text-telegram-primary hover:text-blue-600 transition-colors"
                >
                  Помощь
                </a>
              </div>
              <div className="text-center text-gray-600 text-sm">
                &#169;2025 Novamedika.com
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
