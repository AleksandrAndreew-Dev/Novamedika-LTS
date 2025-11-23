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
    size: 50,
    total: 0,
    totalPages: 1,
  });
  const [error, setError] = useState(null);

  const { tg, isTelegram } = useTelegramWebApp();

  // Добавляем функцию навигации по шагам
  const handleStepNavigation = (targetStep) => {
    if (targetStep < step) {
      setStep(targetStep);
    }
  };

  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await api.get("/cities/");
        const data = response.data;

        const cities = Array.isArray(data)
          ? data
          : data?.results ?? data?.items ?? [];
        if (!Array.isArray(cities)) {
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

  const handleInitialSearch = async (name, city) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get("/search-fts/", {
        params: {
          q: name,
          city: city || "",
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
    } finally {
      setLoading(false);
    }
  };

  const handleFormSelect = async (name, form, manufacturer, country) => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        q: name,
        page: 1,
        size: pagination.size,
      };

      if (form) params.form = form;
      if (manufacturer) params.manufacturer = manufacturer;
      if (country) params.country = country;
      if (searchData.city) params.city = searchData.city;

      const response = await api.get("/search-fts/", { params });

      setSearchData((prev) => ({
        ...prev,
        name: name,
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
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = async (newPage) => {
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
      if (searchData.country) params.country = searchData.country;
      if (searchData.city) params.city = searchData.city;

      const response = await api.get("/search-fts/", { params });

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
            <div className="text-gray-700 text-sm mb-1">Сеть Аптек</div>
            <h1 className="text-2xl font-bold text-telegram-primary m-0">
              <span className="text-orange-500">Н</span>ова
              <span className="text-orange-500">М</span>едика
            </h1>
            <div className="text-gray-700 text-sm mt-1">Справочная служба</div>
          </div>
        </div>
      )}

      <div className={isTelegram ? "p-2" : "p-4"}>
        <div className={isTelegram ? "max-w-full" : "max-w-4xl mx-auto"}>
          <div className="mb-6 bg-white rounded-xl p-4 border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {[1, 2, 3].map((stepNum) => (
                  <React.Fragment key={stepNum}>
                    <button
                      onClick={() =>
                        stepNum < step && handleStepNavigation(stepNum)
                      }
                      disabled={stepNum > step}
                      className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all ${
                        stepNum === step
                          ? "bg-telegram-primary text-white shadow-md"
                          : stepNum < step
                          ? "bg-telegram-primary/20 text-telegram-primary cursor-pointer hover:bg-telegram-primary/30"
                          : "bg-gray-100 text-gray-400"
                      }`}
                      aria-label={`Перейти к шагу ${stepNum}: ${
                        stepNum === 1
                          ? "Поиск"
                          : stepNum === 2
                          ? "Выбор формы"
                          : "Результаты"
                      }`}
                    >
                      {stepNum}
                    </button>
                    {stepNum < 3 && (
                      <div
                        className={`w-8 h-0.5 ${
                          stepNum < step ? "bg-telegram-primary" : "bg-gray-200"
                        }`}
                      />
                    )}
                  </React.Fragment>
                ))}
              </div>

              <div className="text-sm text-gray-600 font-medium">
                Шаг {step} из 3
              </div>
            </div>

            <div className="flex justify-between text-sm">
              <button
                onClick={() => step > 1 && handleStepNavigation(1)}
                className={`flex flex-col items-center ${
                  step >= 1
                    ? "text-telegram-primary cursor-pointer hover:text-blue-700"
                    : "text-gray-400"
                }`}
              >
                <span className="font-medium">Поиск</span>
                <span className="text-xs mt-1">Название и город</span>
              </button>

              <button
                onClick={() => step > 2 && handleStepNavigation(2)}
                className={`flex flex-col items-center ${
                  step >= 2
                    ? "text-telegram-primary cursor-pointer hover:text-blue-700"
                    : "text-gray-400"
                }`}
              >
                <span className="font-medium">Форма</span>
                <span className="text-xs mt-1">Выбор препарата</span>
              </button>

              <div
                className={`flex flex-col items-center ${
                  step === 3 ? "text-telegram-primary" : "text-gray-400"
                }`}
              >
                <span className="font-medium">Результаты</span>
                <span className="text-xs mt-1">Наличие в аптеках</span>
              </div>
            </div>
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
              <div className="space-y-4 w-full max-w-2xl">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                  <div className="animate-pulse space-y-4">
                    <div className="flex space-x-4">
                      <div className="rounded-full bg-gray-200 h-4 w-4"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="h-4 bg-gray-200 rounded"></div>
                      <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                    </div>
                  </div>
                </div>
              </div>
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
                setStep(1);
                setSearchData({ name: "", city: "", form: "" });
                setResults([]);
                setSearchContext(null);
              }}
              onBackToForms={() => setStep(2)}
              loading={loading}
              isTelegram={isTelegram}
            />
          )}
        </div>
      </div>

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
              <div className="text-center text-gray-700 text-sm">
                &#169;2025 Novamedika.com
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
