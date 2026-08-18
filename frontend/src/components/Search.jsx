import { useEffect } from 'react';
import {
  useNavigate,
  useSearchParams,
} from 'react-router-dom';
import { useTelegramWebApp } from '../telegram/TelegramContext';

/**
 * Legacy Search component - redirects to new URL-based search routes
 * This component is kept for backward compatibility and will redirect
 * users to the new search structure with proper URLs
 */
export default function Search() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isTelegram } = useTelegramWebApp();

  useEffect(() => {
    // Get any existing search parameters from URL
    const q = searchParams.get('q') || '';
    const city = searchParams.get('city') || '';

    // Redirect to new search route with parameters preserved
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (city) params.set('city', city);

    const queryString = params.toString();
    const targetUrl = queryString
      ? `/search?${queryString}`
      : '/search';

    navigate(targetUrl, { replace: true });
  }, [navigate, searchParams]);

  // Show loading state while redirecting
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
        <p className="text-gray-500 text-sm">
          {isTelegram
            ? 'Загрузка поиска...'
            : 'Перенаправление...'}
        </p>
      </div>
    </div>
  );
}
