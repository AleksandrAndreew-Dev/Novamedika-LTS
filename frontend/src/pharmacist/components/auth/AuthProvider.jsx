import { useState, useEffect, createContext, useRef } from 'react';
import { authService } from '../../services/authService';
import { logger } from '../../../utils/logger';

// Create Auth Context
const AuthContext = createContext(null);

// Auth Provider Component
function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [pharmacist, setPharmacist] = useState(null);
  const [error, setError] = useState(null);
  const loginInProgressRef = useRef(false); // Prevent concurrent login attempts

  // Check authentication status on mount
  useEffect(() => {
    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAuth = async () => {
    // Prevent concurrent auth checks
    if (loginInProgressRef.current) return;

    try {
      loginInProgressRef.current = true;
      setIsLoading(true);
      setError(null);

      if (authService.isAuthenticated()) {
        console.log('[AuthProvider] Found session token in localStorage, verifying...');
        // Try to get profile to verify session is valid
        const profile = await authService.getProfile();
        setPharmacist(profile);
        setIsAuthenticated(true);
        console.log('[AuthProvider] Session is valid, user authenticated:', profile.user?.first_name);
      } else {
        console.log('[AuthProvider] No session token found in localStorage');
        // If no token but we are in Telegram, try to login immediately
        const initData = window.Telegram?.WebApp?.initData;
        if (initData) {
          console.log('[AuthProvider] 🔄 No token but initData found. Attempting auto-login...');
          try {
            await loginWithTelegram();
            return; // Exit early as loginWithTelegram handles state updates
          } catch (loginErr) {
            console.error('[AuthProvider] ❌ Initial auto-login failed:', loginErr);
          }
        }
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } catch (err) {
      console.error('[AuthProvider] Auth check failed:', err);
      console.error('[AuthProvider] Error details:', err.response?.data || err.message);
      
      // Clear invalid token
      localStorage.removeItem('pharmacist_session_token');
      
      // Auto-login via Telegram WebApp if available
      const initData = window.Telegram?.WebApp?.initData;
      if (initData && err.response?.status === 401) {
        console.log('[AuthProvider] ⚠️ Session expired. Attempting auto-login via Telegram WebApp...');
        try {
          await loginWithTelegram();
          return; // Exit early as loginWithTelegram handles state updates
        } catch (loginErr) {
          console.error('[AuthProvider] ❌ Auto-login failed:', loginErr);
        }
      }
      
      console.log('[AuthProvider] Session invalid or expired, user not authenticated');
      setIsAuthenticated(false);
      setPharmacist(null);
      
      // Set specific error message for user
      if (err.response?.status === 401) {
        setError('Сессия истекла. Пожалуйста, войдите снова через Telegram.');
      } else {
        setError(err.userMessage || 'Ошибка сессии. Попробуйте войти снова.');
      }
    } finally {
      loginInProgressRef.current = false;
      setIsLoading(false);
    }
  };

  // Login with Telegram WebApp initData (NEW - simplified method)
  const loginWithTelegram = async () => {
    // Prevent concurrent login attempts
    if (loginInProgressRef.current) {
      console.log('[AuthProvider] ⚠️ Login already in progress, skipping...');
      return pharmacist;
    }

    try {
      loginInProgressRef.current = true;
      setIsLoading(true);
      setError(null);
      
      console.log('[AuthProvider] 🔄 Starting Telegram WebApp login...');
      
      // Initialize Telegram WebApp if available
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
      }
      
      // Use the new loginWithTelegram method from authService
      await authService.loginWithTelegram();
      
      console.log('[AuthProvider] ✅ Backend validated initData and returned session token');
      
      console.log('[AuthProvider] Fetching pharmacist profile...');
      const profile = await authService.getProfile();
      
      console.log('[AuthProvider] ✅ Profile fetched successfully:', profile.user?.first_name, profile.user?.telegram_id);
      setPharmacist(profile);
      setIsAuthenticated(true);
      
      console.log('[AuthProvider] ✅ Telegram login successful');
      return profile;
      
    } catch (err) {
      console.error('[AuthProvider] ❌ Telegram login failed:', err);
      
      // Clear any partial data
      localStorage.removeItem('pharmacist_session_token');
      
      let errorMessage = 'Ошибка входа через Telegram. ';
      
      if (err.message.includes('Not in Telegram')) {
        errorMessage = 'Эта страница должна быть открыта из Telegram бота. Пожалуйста, нажмите кнопку "Панель фармацевта" в боте.';
      } else if (err.message.includes('initData not available')) {
        errorMessage = 'Данные Telegram не загружены. Попробуйте закрыть и открыть WebApp снова.';
      } else {
        errorMessage += err.message || 'Попробуйте позже.';
      }
      
      setError(errorMessage);
      throw err;
    } finally {
      loginInProgressRef.current = false;
      setIsLoading(false);
    }
  };

  // Login with token from URL (legacy method - if needed)
  const loginWithToken = async (token) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('[AuthProvider] 🔄 Starting login with token...');
      
      // Store the token
      authService.setSessionToken(token);
      
      console.log('[AuthProvider] Fetching pharmacist profile...');
      const profile = await authService.getProfile();
      
      console.log('[AuthProvider] ✅ Profile fetched successfully:', profile.user?.first_name);
      setPharmacist(profile);
      setIsAuthenticated(true);
      
      console.log('[AuthProvider] ✅ Token login successful');
      return profile;
      
    } catch (err) {
      console.error('[AuthProvider] ❌ Token login failed:', err);
      
      // Clear any partial data
      localStorage.removeItem('pharmacist_session_token');
      
      let errorMessage = 'Ошибка входа. ';
      
      if (err.response?.status === 401) {
        errorMessage += 'Неверный или истекший токен.';
      } else {
        errorMessage += err.message || 'Попробуйте позже.';
      }
      
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      await authService.logout();
      
      setPharmacist(null);
      setIsAuthenticated(false);
      setError(null);
      
      logger.info('Logout successful');
      
      // Redirect to login page using window.location
      window.location.href = '/pharmacist/login';
    } catch (err) {
      logger.error('Logout error:', err);
    }
  };

  // Update online status
  const setOnlineStatus = async (isOnline) => {
    try {
      await authService.setOnlineStatus(isOnline);
      
      // Update local state
      setPharmacist((prev) => ({
        ...prev,
        is_online: isOnline,
      }));
    } catch (err) {
      logger.error('Failed to update online status:', err);
      throw err;
    }
  };

  // Refresh profile data
  const refreshProfile = async () => {
    try {
      const profile = await authService.getProfile();
      setPharmacist(profile);
      return profile;
    } catch (err) {
      logger.error('Failed to refresh profile:', err);
      throw err;
    }
  };

  const value = {
    isAuthenticated,
    isLoading,
    pharmacist,
    user: pharmacist, // Alias for compatibility
    error,
    loginWithTelegram, // NEW: Telegram WebApp login using session tokens
    loginWithToken, // Legacy: Login with token from URL
    logout,
    setOnlineStatus,
    refreshProfile,
    checkAuth,
  };

  // Return the provider component
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext, AuthProvider };