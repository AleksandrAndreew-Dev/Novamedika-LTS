/**
 * SearchBar — Google-style unified search input.
 *
 * UX:
 *  - Single rounded pill: [📍 city icon] [ text input ] [ ➤ submit ]
 *  - Click city icon → dropdown panel with city list
 *  - Below the pill — active filter chips (city / form / manufacturer / country)
 *  - Fully Telegram-WebApp aware: uses TG theme vars when available
 *
 * IMPORTANT: This component ONLY changes presentation.
 * All callback signatures (onSearch, cities, loading, currentCity,
 * initialName, isTelegram) are preserved exactly as before, so
 * SearchFormPage.jsx and downstream logic remain untouched.
 */
import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
} from 'react';

const SearchBar = React.memo(function SearchBar({
  cities,
  onSearch,
  loading,
  currentCity,
  isTelegram,
  initialName,
}) {
  const [name, setName] = useState(initialName || '');
  const [city, setCity] = useState(currentCity || '');
  const [nameError, setNameError] = useState('');
  const [cityPanelOpen, setCityPanelOpen] = useState(false);
  const [cityFilter, setCityFilter] = useState('');

  const inputRef = useRef(null);
  const cityPanelRef = useRef(null);
  const containerRef = useRef(null);

  // Sync external initialName (URL params)
  useEffect(() => {
    if (initialName) setName(initialName);
  }, [initialName]);

  // Sync external currentCity
  useEffect(() => {
    setCity(currentCity || '');
  }, [currentCity]);

  // Close city panel on outside click / Escape
  useEffect(() => {
    if (!cityPanelOpen) return;

    const handleClickOutside = (e) => {
      if (
        cityPanelRef.current &&
        !cityPanelRef.current.contains(e.target) &&
        !containerRef.current?.querySelector('[data-city-trigger]')?.contains(e.target)
      ) {
        setCityPanelOpen(false);
      }
    };
    const handleEscape = (e) => {
      if (e.key === 'Escape') setCityPanelOpen(false);
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [cityPanelOpen]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!name.trim()) {
      setNameError('Введите название препарата');
      inputRef.current?.focus();
      return;
    }
    setNameError('');
    setCityPanelOpen(false);
    onSearch(name, city);
  };

  const handleNameChange = (e) => {
    setName(e.target.value);
    if (nameError) setNameError('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handlePickCity = (pickedCity) => {
    setCity(pickedCity);
    setCityPanelOpen(false);
    setCityFilter('');
    // Return focus to the input so user can continue typing
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const filteredCities = useMemo(() => {
    const q = cityFilter.trim().toLowerCase();
    if (!q) return cities;
    return cities.filter((c) => c.toLowerCase().includes(q));
  }, [cities, cityFilter]);

  const activeChips = useMemo(() => {
    const chips = [];
    if (city) {
      chips.push({
        key: 'city',
        label: city,
        icon: '📍',
        onClear: () => setCity(''),
      });
    }
    return chips;
  }, [city]);

  // ─────────────────────────────────────────────────────────
  //  RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <div
      ref={containerRef}
      className={`searchbar-root ${isTelegram ? 'searchbar-root--tg' : ''}`}
    >
      {/* ===== Main pill ===== */}
      <form
        onSubmit={handleSubmit}
        className="searchbar-pill"
        role="search"
        aria-label="Поиск лекарств"
      >
        {/* City trigger */}
        <button
          type="button"
          data-city-trigger
          onClick={() => setCityPanelOpen((v) => !v)}
          className={`searchbar-city-btn ${city ? 'searchbar-city-btn--active' : ''}`}
          aria-haspopup="dialog"
          aria-expanded={cityPanelOpen}
          aria-label={city ? `Город: ${city}` : 'Выбрать город'}
          title={city || 'Выбрать город'}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          {city && (
            <span className="searchbar-city-label" aria-hidden="true">
              {city.length > 12 ? city.slice(0, 12) + '…' : city}
            </span>
          )}
        </button>

        {/* Divider */}
        <span className="searchbar-divider" aria-hidden="true" />

        {/* Text input */}
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={handleNameChange}
          onKeyDown={handleKeyDown}
          placeholder="Найдите лекарство…"
          className="searchbar-input"
          aria-label="Название препарата"
          aria-invalid={!!nameError}
          aria-describedby={nameError ? 'searchbar-error' : undefined}
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
          enterKeyHint="search"
        />

        {/* Clear (only when text present) */}
        {name && (
          <button
            type="button"
            onClick={() => {
              setName('');
              inputRef.current?.focus();
            }}
            className="searchbar-clear-btn"
            aria-label="Очистить"
            tabIndex={-1}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="searchbar-submit-btn"
          aria-label={loading ? 'Выполняется поиск…' : 'Найти'}
        >
          {loading ? (
            <span className="searchbar-spinner" aria-hidden="true" />
          ) : (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          )}
        </button>
      </form>

      {/* ===== Error ===== */}
      {nameError && (
        <p
          id="searchbar-error"
          className="searchbar-error"
          role="alert"
        >
          {nameError}
        </p>
      )}

      {/* ===== Active filter chips ===== */}
      {activeChips.length > 0 && (
        <div className="searchbar-chips" aria-label="Активные фильтры">
          {activeChips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={chip.onClear}
              className="searchbar-chip"
              aria-label={`Убрать фильтр ${chip.label}`}
            >
              <span aria-hidden="true">{chip.icon}</span>
              <span>{chip.label}</span>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          ))}
        </div>
      )}

      {/* ===== City dropdown panel ===== */}
      {cityPanelOpen && (
        <div
          ref={cityPanelRef}
          className="searchbar-city-panel"
          role="dialog"
          aria-label="Выбор города"
        >
          <div className="searchbar-city-panel__head">
            <span>Выберите город</span>
            <button
              type="button"
              className="searchbar-city-panel__close"
              onClick={() => setCityPanelOpen(false)}
              aria-label="Закрыть"
            >
              ✕
            </button>
          </div>

          {cities.length > 6 && (
            <input
              type="text"
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              placeholder="Поиск города…"
              className="searchbar-city-panel__search"
              autoFocus
            />
          )}

          <ul className="searchbar-city-panel__list" role="listbox">
            <li>
              <button
                type="button"
                role="option"
                aria-selected={city === ''}
                onClick={() => handlePickCity('')}
                className={`searchbar-city-panel__item ${city === '' ? 'is-selected' : ''}`}
              >
                <span>🌍</span>
                <span>Все города</span>
              </button>
            </li>
            {filteredCities.map((c) => (
              <li key={c}>
                <button
                  type="button"
                  role="option"
                  aria-selected={city === c}
                  onClick={() => handlePickCity(c)}
                  className={`searchbar-city-panel__item ${city === c ? 'is-selected' : ''}`}
                >
                  <span>📍</span>
                  <span>{c}</span>
                </button>
              </li>
            ))}
            {filteredCities.length === 0 && (
              <li className="searchbar-city-panel__empty">
                Ничего не найдено
              </li>
            )}
          </ul>
        </div>
      )}

      {/* ===== Scoped styles ===== */}
      <style>{`
        .searchbar-root {
          position: relative;
          width: 100%;
          max-width: 720px;
          margin: 0 auto;
        }

        /* ---------- PILL ---------- */
        .searchbar-pill {
          display: flex;
          align-items: center;
          gap: 4px;
          background: var(--tg-bg, #ffffff);
          border: 1px solid var(--tg-border, #e5e7eb);
          border-radius: 999px;
          padding: 6px 6px 6px 8px;
          box-shadow:
            0 1px 2px rgba(0, 0, 0, 0.04),
            0 4px 14px rgba(0, 0, 0, 0.04);
          transition:
            border-color 0.15s ease,
            box-shadow 0.15s ease;
        }

        .searchbar-pill:focus-within {
          border-color: var(--tg-link, #2b6cb0);
          box-shadow:
            0 1px 2px rgba(0, 0, 0, 0.05),
            0 6px 20px rgba(43, 108, 176, 0.12);
        }

        /* ---------- CITY TRIGGER ---------- */
        .searchbar-city-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 10px;
          border-radius: 999px;
          background: transparent;
          border: none;
          color: var(--tg-hint, #6b7280);
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
          flex-shrink: 0;
          max-width: 140px;
        }

        .searchbar-city-btn:hover {
          background: var(--tg-secondary-bg, #f3f4f6);
          color: var(--tg-text, #111827);
        }

        .searchbar-city-btn--active {
          color: var(--tg-link, #2b6cb0);
        }

        .searchbar-city-btn--active:hover {
          background: rgba(43, 108, 176, 0.08);
        }

        .searchbar-city-label {
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* ---------- DIVIDER ---------- */
        .searchbar-divider {
          width: 1px;
          height: 22px;
          background: var(--tg-border, #e5e7eb);
          flex-shrink: 0;
          margin: 0 2px;
        }

        /* ---------- INPUT ---------- */
        .searchbar-input {
          flex: 1;
          min-width: 0;
          border: none;
          outline: none;
          background: transparent;
          font-size: 16px; /* >=16px prevents iOS zoom */
          line-height: 1.4;
          padding: 10px 4px;
          color: var(--tg-text, #111827);
          font-family: inherit;
          -webkit-appearance: none;
          appearance: none;
        }

        .searchbar-input::placeholder {
          color: var(--tg-hint, #9ca3af);
        }

        /* ---------- CLEAR ---------- */
        .searchbar-clear-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 999px;
          background: transparent;
          border: none;
          color: var(--tg-hint, #9ca3af);
          cursor: pointer;
          flex-shrink: 0;
          transition: background 0.15s, color 0.15s;
        }

        .searchbar-clear-btn:hover {
          background: var(--tg-secondary-bg, #f3f4f6);
          color: var(--tg-text, #111827);
        }

        /* ---------- SUBMIT ---------- */
        .searchbar-submit-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 999px;
          background: var(--tg-link, #2b6cb0);
          color: #ffffff;
          border: none;
          cursor: pointer;
          flex-shrink: 0;
          transition: background 0.15s, transform 0.1s;
        }

        .searchbar-submit-btn:hover:not(:disabled) {
          filter: brightness(1.08);
        }

        .searchbar-submit-btn:active:not(:disabled) {
          transform: scale(0.94);
        }

        .searchbar-submit-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .searchbar-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.35);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: searchbar-spin 0.6s linear infinite;
        }

        @keyframes searchbar-spin {
          to { transform: rotate(360deg); }
        }

        /* ---------- ERROR ---------- */
        .searchbar-error {
          margin: 8px 16px 0;
          font-size: 13px;
          color: #ef4444;
        }

        /* ---------- CHIPS ---------- */
        .searchbar-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin: 10px 12px 0;
        }

        .searchbar-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(43, 108, 176, 0.1);
          color: var(--tg-link, #2b6cb0);
          border: none;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s;
        }

        .searchbar-chip:hover {
          background: rgba(43, 108, 176, 0.18);
        }

        /* ---------- CITY PANEL ---------- */
        .searchbar-city-panel {
          position: absolute;
          top: calc(100% + 8px);
          left: 0;
          width: 280px;
          max-width: calc(100vw - 32px);
          max-height: 380px;
          background: var(--tg-bg, #ffffff);
          border: 1px solid var(--tg-border, #e5e7eb);
          border-radius: 16px;
          box-shadow:
            0 8px 24px rgba(0, 0, 0, 0.10),
            0 2px 6px rgba(0, 0, 0, 0.04);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          z-index: 40;
          animation: searchbar-panel-in 0.14s ease-out;
        }

        @keyframes searchbar-panel-in {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .searchbar-city-panel__head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 14px;
          font-size: 13px;
          font-weight: 600;
          color: var(--tg-text, #111827);
          border-bottom: 1px solid var(--tg-border, #e5e7eb);
        }

        .searchbar-city-panel__close {
          background: transparent;
          border: none;
          color: var(--tg-hint, #9ca3af);
          font-size: 16px;
          cursor: pointer;
          padding: 2px 6px;
          border-radius: 6px;
          transition: background 0.15s;
        }

        .searchbar-city-panel__close:hover {
          background: var(--tg-secondary-bg, #f3f4f6);
          color: var(--tg-text, #111827);
        }

        .searchbar-city-panel__search {
          margin: 10px 12px;
          padding: 8px 12px;
          border-radius: 10px;
          border: 1px solid var(--tg-border, #e5e7eb);
          background: var(--tg-secondary-bg, #f9fafb);
          font-size: 14px;
          color: var(--tg-text, #111827);
          outline: none;
          font-family: inherit;
        }

        .searchbar-city-panel__search:focus {
          border-color: var(--tg-link, #2b6cb0);
        }

        .searchbar-city-panel__list {
          list-style: none;
          margin: 0;
          padding: 4px 6px 8px;
          overflow-y: auto;
          flex: 1;
        }

        .searchbar-city-panel__item {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 10px 12px;
          border-radius: 10px;
          background: transparent;
          border: none;
          cursor: pointer;
          font-size: 14px;
          color: var(--tg-text, #111827);
          text-align: left;
          transition: background 0.12s;
          font-family: inherit;
        }

        .searchbar-city-panel__item:hover {
          background: var(--tg-secondary-bg, #f3f4f6);
        }

        .searchbar-city-panel__item.is-selected {
          background: rgba(43, 108, 176, 0.08);
          color: var(--tg-link, #2b6cb0);
          font-weight: 500;
        }

        .searchbar-city-panel__empty {
          padding: 16px 12px;
          text-align: center;
          color: var(--tg-hint, #9ca3af);
          font-size: 13px;
        }

        /* ---------- TELEGRAM MODE ---------- */
        .searchbar-root--tg .searchbar-input {
          font-size: 16px; /* no iOS zoom in WebApp */
        }

        /* ---------- MOBILE ---------- */
        @media (max-width: 480px) {
          .searchbar-pill {
            padding: 5px 5px 5px 6px;
          }
          .searchbar-city-btn {
            padding: 8px;
          }
          .searchbar-city-label {
            display: none;
          }
          .searchbar-city-btn--active .searchbar-city-label {
            display: inline;
            max-width: 80px;
          }
          .searchbar-submit-btn {
            width: 38px;
            height: 38px;
          }
          .searchbar-chips {
            margin: 8px 4px 0;
          }
        }
      `}</style>
    </div>
  );
});

export default SearchBar;
