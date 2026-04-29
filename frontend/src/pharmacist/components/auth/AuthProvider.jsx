import { useState, useEffect, createContext, useRef, useCallback } from 'react';
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

  // Single unified auto-login function as recommended in faq3.md
  const performAutoLogin = useCallback(async () => {
    // Prevent concurrent login attempts
    if (loginInProgressRef.current) {
      console.log('[AuthProvider] Login already in progress, skipping');
      return;
    }

    loginInProgressRef.current = true;
    console.log('[AuthProvider] Starting auto-login check...');

    try {
      setIsLoading(true);
      setError(null);

      // Check if we're in Telegram environment
      if (!window.Telegram?.WebApp) {
        console.log('[AuthProvider] Not in Telegram environment. Skipping pharmacist auth.');
        setIsAuthenticated(false);
        setPharmacist(null);
        return;
      }

      // Step 1: Try existing token if available
      const token = localStorage.getItem('pharmacist_session_token');
      if (token) {
        try {
          const profile = await authService.getProfile();
          
          if (profile && profile.is_active) {
            // ✅ Valid active session
            setPharmacist(profile);
            setIsAuthenticated(true);
            console.log('[AuthProvider] Session is valid, active pharmacist:', profile.user?.first_name);
            return;
          } else {
            // ❌ Pharmacist exists but is not active - NO RETRY
            console.warn('[AuthProvider] Pharmacist is not active');
            setError('Доступ запрещен. Ваш аккаунт фармацевта ещё не активирован администратором.');
            localStorage.removeItem('pharmacist_session_token');
            setIsAuthenticated(false);
            setPharmacist(null);
            return;
          }
        } catch (err) {
          // Handle specific error types
          if (err.message === 'Session expired') {
            // Token expired - remove it and continue to initData login
            console.log('[AuthProvider] Token expired, trying auto-login with initData');
            localStorage.removeItem('pharmacist_session_token');
          } else if (err.message?.includes('not an active registered pharmacist')) {
            // 403 - Access denied, NO RETRY
            console.warn('[AuthProvider] Access denied: not an active registered pharmacist');
            setError('Доступ запрещен. Вы не зарегистрированы как активный фармацевт.');
            localStorage.removeItem('pharmacist_session_token');
            setIsAuthenticated(false);
            setPharmacist(null);
            return;
          } else {
            // Other errors - throw to outer catch
            throw err;
          }
        }
      }

      // Step 2: No token or token expired - try auto-login via initData
      const initData = window.Telegram.WebApp.initData;
      if (!initData) {
        console.log('[AuthProvider] No initData, not in Telegram Mini App');
        setIsAuthenticated(false);
        setPharmacist(null);
        return;
      }

      console.log('[AuthProvider] 🔄 Attempting auto-login with initData...');
      
      // Initialize Telegram WebApp
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();

      try {
        // Login via backend
        await authService.loginWithTelegram();
        
        console.log('[AuthProvider] ✅ Backend validated initData and returned session token');
        
        // Immediately fetch profile to verify
        const profile = await authService.getProfile();
        
        if (profile && profile.is_active) {
          setPharmacist(profile);
          setIsAuthenticated(true);
          console.log('[AuthProvider] ✅ Auto-login successful:', profile.user?.first_name);
        } else {
          // Pharmacist not active after login
          console.warn('[AuthProvider] Pharmacist exists but is not active after login');
          setError('Доступ запрещен. Ваш аккаунт фармацевта ещё не активирован администратором.');
          localStorage.removeItem('pharmacist_session_token');
          setIsAuthenticated(false);
          setPharmacist(null);
        }
      } catch (loginErr) {
        console.error('[AuthProvider] ❌ Auto-login failed:', loginErr.message);
        
        // Clear any partial data
        localStorage.removeItem('pharmacist_session_token');
        
        // Set appropriate error message
        let errorMessage = 'Ошибка авторизации. ';
        
        if (loginErr.message.includes('Not in Telegram')) {
          errorMessage = 'Эта страница должна быть открыта из Telegram бота. Пожалуйста, нажмите кнопку "Панель фармацевта" в боте.';
        } else if (loginErr.message.includes('initData not available')) {
          errorMessage = 'Данные Telegram не загружены. Попробуйте закрыть и открыть WebApp снова.';
        } else if (loginErr.message.includes('Telegram session expired') || loginErr.message.includes('QUERY_ID_INVALID')) {
          errorMessage = 'Сессия Telegram истекла. Пожалуйста, перезапустите Мини-Приложение.';
        } else if (loginErr.message.includes('not an active registered pharmacist') || loginErr.message.includes('Access denied')) {
          errorMessage = 'Доступ запрещен. Вы не зарегистрированы как активный фармацевт.';
        } else {
          errorMessage += loginErr.message || 'Попробуйте позже.';
        }
        
        setError(errorMessage);
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } catch (unexpectedError) {
      console.error('[AuthProvider] Unexpected error:', unexpectedError);
      setError('Произошла непредвиденная ошибка. Пожалуйста, перезапустите Mini App.');
      setIsAuthenticated(false);
      setPharmacist(null);
    } finally {
      // ALWAYS reset the flag
      loginInProgressRef.current = false;
      setIsLoading(false);
    }
  }, []);

  // Run auto-login on mount
  useEffect(() => {
    performAutoLogin();
  }, [performAutoLogin]);

  // Legacy loginWithTelegram method for manual triggers (if needed)
  const loginWithTelegram = async () => {
    // Delegate to performAutoLogin
    return performAutoLogin();
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
    loginWithTelegram, // Delegates to performAutoLogin
    loginWithToken, // Legacy: Login with token from URL
    logout,
    setOnlineStatus,
    refreshProfile,
    checkAuth: performAutoLogin, // Alias for backward compatibility
  };

  // Return the provider component
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext, AuthProvider };