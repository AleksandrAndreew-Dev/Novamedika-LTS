/**
 * Утилита для сохранения/загрузки контекста поиска в sessionStorage.
 * Решает проблему потери availableCombinations при навигации "назад"
 * и при перезагрузке страницы (актуально для Telegram WebApp).
 */

const STORAGE_KEY = 'novamedika_search_context';

/**
 * Сохранить контекст поиска (searchData + searchContext).
 * @param {{name: string, city: string}} searchData
 * @param {{availableCombinations: Array, totalFound: number}} searchContext
 */
export function saveSearchContext(
  searchData,
  searchContext,
) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        searchData,
        searchContext: {
          availableCombinations:
            searchContext?.availableCombinations || [],
          totalFound: searchContext?.totalFound || 0,
        },
        savedAt: Date.now(),
      }),
    );
  } catch {
    // sessionStorage может быть недоступен (private mode / WebApp) — молча игнорируем
  }
}

/**
 * Загрузить сохранённый контекст поиска.
 * @returns {{searchData: {name: string, city: string}, searchContext: {availableCombinations: Array, totalFound: number}} | null}
 */
export function loadSearchContext() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (!parsed?.searchData) return null;

    return {
      searchData: parsed.searchData,
      searchContext: parsed.searchContext || {
        availableCombinations: [],
        totalFound: 0,
      },
    };
  } catch {
    return null;
  }
}

/**
 * Очистить сохранённый контекст поиска.
 */
export function clearSearchContext() {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
