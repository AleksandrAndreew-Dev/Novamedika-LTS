// components/Search.jsx
import React, { useState, useEffect } from "react";
import axios from "axios";
import SearchBar from "./SearchBar";
import FormSelection from "./FormSelection";
import SearchResults from "./SearchResults";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Search() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [cities, setCities] = useState([]);
  const [searchData, setSearchData] = useState({
    name: "",
    city: "",
    form: ""
  });
  const [searchContext, setSearchContext] = useState(null);
  const [results, setResults] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    size: 50,
    total: 0,
    totalPages: 1
  });

  // Загружаем список городов при монтировании
  useEffect(() => {
    const fetchCities = async () => {
      try {
        console.log("Fetching cities from:", `${API_BASE_URL}/api/search/cities/`);
        const response = await axios.get(`${API_BASE_URL}/api/search/cities/`);
        console.log("Cities response:", response.data);
        setCities(response.data);
      } catch (error) {
        console.error("Error fetching cities:", error);
        setCities(["Минск", "Гомель", "Брест", "Гродно", "Витебск", "Могилев"]);
      }
    };
    fetchCities();
  }, []);

  // Первый этап поиска
  const handleInitialSearch = async (name, city) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/search/search-two-step/`, {
        params: { name, city }
      });

      setSearchData(prev => ({ ...prev, name, city }));
      setSearchContext({
        availableForms: response.data.available_forms,
        previewProducts: response.data.preview_products,
        totalFound: response.data.total_found,
        searchId: response.data.search_id
      });
      setStep(2);
    } catch (error) {
      console.error("Search error:", error);
      alert("Ошибка при поиске. Попробуйте еще раз.");
    } finally {
      setLoading(false);
    }
  };

  // Второй этап - выбор формы
  const handleFormSelect = async (form) => {
    setLoading(true);
    try {
      const params = {
        form,
        page: 1,
        size: pagination.size
      };

      // Если есть search_id из контекста, используем его
      if (searchContext?.searchId) {
        params.search_id = searchContext.searchId;
      } else {
        // Иначе используем обычные параметры
        params.name = searchData.name;
        params.city = searchData.city;
      }

      const response = await axios.get(`${API_BASE_URL}/api/search/search/`, { params });

      setSearchData(prev => ({ ...prev, form }));
      setResults(response.data.items);
      setPagination(prev => ({
        ...prev,
        page: response.data.page,
        total: response.data.total,
        totalPages: response.data.total_pages
      }));
      setStep(3);
    } catch (error) {
      console.error("Form selection error:", error);
      alert("Ошибка при загрузке результатов.");
    } finally {
      setLoading(false);
    }
  };

  // Пагинация
  const handlePageChange = async (newPage) => {
    setLoading(true);
    try {
      const params = {
        name: searchData.name,
        city: searchData.city,
        form: searchData.form,
        page: newPage,
        size: pagination.size
      };

      const response = await axios.get(`${API_BASE_URL}/api/search/search/`, { params });

      setResults(response.data.items);
      setPagination(prev => ({
        ...prev,
        page: response.data.page,
        total: response.data.total,
        totalPages: response.data.total_pages
      }));
    } catch (error) {
      console.error("Pagination error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Сброс поиска
  const handleReset = () => {
    setStep(1);
    setSearchData({ name: "", city: "", form: "" });
    setSearchContext(null);
    setResults([]);
  };

  return (
    <div className="search-container">
      <nav className="nav">
        <ul className="list-inline">
          <li className="list-inline-item">
            <a href="/psi">Центр психологической силы Инсайтинк</a>
          </li>
          <li className="list-inline-item">
            <a href="/novamedika">Сайт Новамедика</a>
          </li>
        </ul>
      </nav>

      <main className="container-lg">
        <section className="row flex-wrapper container-fluid">
          <header className="header container">
            <span className="logo-text1">Сеть Аптек</span>
            <h1 className="logo-text">
              <span className="fletter">Н</span>ова<span className="fletter">М</span>едика
            </h1>
            <span className="logo-text2">Справочная служба</span>
          </header>

          <div id="two" className="container">
            <div className="row">
              <SearchBar
                cities={cities}
                onSearch={handleInitialSearch}
                loading={loading}
                currentCity={searchData.city}
              />
            </div>
          </div>
        </section>

        {/* Результаты поиска */}
        {step === 2 && searchContext && (
          <FormSelection
            availableForms={searchContext.availableForms}
            previewProducts={searchContext.previewProducts}
            totalFound={searchContext.totalFound}
            searchData={searchData}
            onFormSelect={handleFormSelect}
            onBack={handleReset}
            loading={loading}
          />
        )}

        {step === 3 && (
          <SearchResults
            results={results}
            searchData={searchData}
            pagination={pagination}
            onPageChange={handlePageChange}
            onNewSearch={handleReset}
            loading={loading}
          />
        )}
      </main>

      {/* Футер */}
      <div className="footer container-fluid text-center">
        <ul className="list-inline">
          <li className="list-inline-item"><a href="/">Поиск</a></li>
          <li className="list-inline-item"><a href="/terms">Условия использования сервиса</a></li>
          <li className="list-inline-item"><a href="/cookie-policy">Политика использования файлов cookie</a></li>
          <li className="list-inline-item"><a href="/pharmacies-nearby">Аптеки рядом</a></li>
          <li className="list-inline-item"><a href="/advertising">Реклама</a></li>
          <li className="list-inline-item"><a href="/contacts">Контакты</a></li>
          <li className="list-inline-item"><a href="/help">Помощь</a></li>
        </ul>
      </div>

      <footer className="footer container-fluid text-center">
        &#169;2025 Novamedika.com
      </footer>
    </div>
  );
}
