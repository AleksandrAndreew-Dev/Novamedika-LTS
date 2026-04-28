import { useState, useEffect, createContext } from 'react';
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

  // Check authentication status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      if (authService.isAuthenticated()) {
        console.log('[AuthProvider] Found token in localStorage, verifying...');
        // Try to get profile to verify token is valid
        const profile = await authService.getProfile();
        setPharmacist(profile);
        setIsAuthenticated(true);
        console.log('[AuthProvider] Token is valid, user authenticated:', profile.user?.first_name);
      } else {
        console.log('[AuthProvider] No token found in localStorage');
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } catch (err) {
      console.error('[AuthProvider] Auth check failed:', err);
      console.error('[AuthProvider] Error details:', err.response?.data || err.message);
      
      // Token might be expired, try to refresh
      const refreshToken = authService.getRefreshToken();
      if (refreshToken) {
        console.log('[AuthProvider] Attempting to refresh token...');
        try {
          await authService.refresh(refreshToken);
          const profile = await authService.getProfile();
          setPharmacist(profile);
          setIsAuthenticated(true);
          console.log('[AuthProvider] Token refresh successful');
        } catch (refreshErr) {
          console.error('[AuthProvider] Token refresh failed:', refreshErr);
          console.error('[AuthProvider] Refresh error details:', refreshErr.response?.data || refreshErr.message);
          setIsAuthenticated(false);
          setPharmacist(null);
          
          // Set specific error message for user
          if (refreshErr.response?.status === 401) {
            setError('Сессия истекла. Пожалуйста, войдите снова через Telegram.');
          }
        }
      } else {
        console.log('[AuthProvider] No refresh token available, user not authenticated');
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Login with JWT token directly (from URL or other source)
  const loginWithToken = async (token) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('[AuthProvider] 🔄 Starting login with token...');
      console.log('[AuthProvider] Token length:', token?.length);
      
      // Validate token structure before proceeding
      if (!token || typeof token !== 'string') {
        throw new Error('Invalid token format');
      }
      
      // Save the token to localStorage - interceptor will pick it up
      console.log('[AuthProvider] Setting access token in localStorage...');
      authService.setAccessToken(token);
      
      // Verify token was saved
      const savedToken = localStorage.getItem('pharmacist_access_token');
      console.log('[AuthProvider] Token saved to localStorage:', !!savedToken);
      
      if (!savedToken) {
        throw new Error('Failed to save token to localStorage');
      }
      
      console.log('[AuthProvider] Fetching pharmacist profile from /api/pharmacist/me...');
      // Get profile after setting token - interceptor will add Authorization header
      const profile = await authService.getProfile();
      
      console.log('[AuthProvider] ✅ Profile fetched successfully:', profile.user?.first_name, profile.user?.telegram_id);
      setPharmacist(profile);
      setIsAuthenticated(true);
      
      console.log('[AuthProvider] ✅ Login with token successful');
      return profile;
    } catch (err) {
      console.error('[AuthProvider] ❌ Login with token failed:', err);
      console.error('[AuthProvider] Error status:', err.response?.status);
      console.error('[AuthProvider] Error data:', err.response?.data);
      console.error('[AuthProvider] Error message:', err.message);
      
      // Clear invalid token from localStorage
      localStorage.removeItem('pharmacist_access_token');
      localStorage.removeItem('pharmacist_refresh_token');
      
      // Check if it's an authentication error
      if (err.response?.status === 401) {
        console.error('[AuthProvider] ⚠️ Token is invalid, expired, or pharmacist not found');
        // Decode token to get more info (for debugging)
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          console.log('[AuthProvider] Token payload:', payload);
          if (payload.sub) {
            console.log(`[AuthProvider] Looking for pharmacist with UUID: ${payload.sub}`);
          }
        } catch (decodeErr) {
          console.error('[AuthProvider] Failed to decode token:', decodeErr);
        }
        setError('Токен недействителен или фармацевт не найден. Пожалуйста, войдите снова через Telegram.');
      } else if (err.response?.status === 403) {
        console.error('[AuthProvider] ⚠️ Access forbidden - no token sent');
        setError('Ошибка доступа. Токен не был отправлен.');
      } else if (err.response?.status === 0) {
        console.error('[AuthProvider] ⚠️ Network error - check API connectivity');
        setError('Ошибка сети. Проверьте подключение к интернету.');
      } else {
        setError(err.response?.data?.detail || 'Ошибка аутентификации. Попробуйте позже.');
      }
      
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Login function
  const login = async (credentials) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = await authService.login(credentials);
      
      // Get profile after successful login
      const profile = await authService.getProfile();
      setPharmacist(profile);
      setIsAuthenticated(true);
      
      logger.info('Login successful');
      return data;
    } catch (err) {
      logger.error('Login failed:', err);
      setError(err.response?.data?.detail || 'Ошибка входа. Проверьте данные.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      const refreshToken = authService.getRefreshToken();
      await authService.logout(refreshToken);
      
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
    login,
    loginWithToken, // New function for token-based login
    logout,
    setOnlineStatus,
    refreshProfile,
    checkAuth,
  };

  // Return the provider component
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext, AuthProvider };