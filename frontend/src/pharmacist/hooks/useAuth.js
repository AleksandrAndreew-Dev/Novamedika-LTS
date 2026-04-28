// Authentication hook for pharmacist dashboard
import { useState, useEffect, useCallback } from 'react';
import { authService } from '../services/authService';
import { logger } from '../../utils/logger';

export function useAuth() {
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
        console.log('[useAuth] Found token in localStorage, verifying...');
        // Try to get profile to verify token is valid
        const profile = await authService.getProfile();
        setPharmacist(profile);
        setIsAuthenticated(true);
        console.log('[useAuth] Token is valid, user authenticated:', profile.user?.first_name);
      } else {
        console.log('[useAuth] No token found in localStorage');
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } catch (err) {
      console.error('[useAuth] Auth check failed:', err);
      console.error('[useAuth] Error details:', err.response?.data || err.message);
      
      // Token might be expired, try to refresh
      const refreshToken = authService.getRefreshToken();
      if (refreshToken) {
        console.log('[useAuth] Attempting to refresh token...');
        try {
          await authService.refresh(refreshToken);
          const profile = await authService.getProfile();
          setPharmacist(profile);
          setIsAuthenticated(true);
          console.log('[useAuth] Token refresh successful');
        } catch (refreshErr) {
          console.error('[useAuth] Token refresh failed:', refreshErr);
          console.error('[useAuth] Refresh error details:', refreshErr.response?.data || refreshErr.message);
          setIsAuthenticated(false);
          setPharmacist(null);
        }
      } else {
        console.log('[useAuth] No refresh token available, user not authenticated');
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Login with JWT token directly (from URL or other source)
  const loginWithToken = useCallback(async (token) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('[useAuth] Setting access token...');
      // Save the token
      authService.setAccessToken(token);
      
      console.log('[useAuth] Fetching pharmacist profile...');
      // Get profile after setting token
      const profile = await authService.getProfile();
      setPharmacist(profile);
      setIsAuthenticated(true);
      
      console.log('[useAuth] Login with token successful:', profile.user?.first_name);
      return profile;
    } catch (err) {
      console.error('[useAuth] Login with token failed:', err);
      console.error('[useAuth] Error details:', err.response?.data || err.message);
      setError(err.response?.data?.detail || 'Ошибка аутентификации.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Login function
  const login = useCallback(async (credentials) => {
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
  }, []);

  // Logout function
  const logout = useCallback(async () => {
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
  }, []);

  // Update online status
  const setOnlineStatus = useCallback(async (isOnline) => {
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
  }, []);

  // Refresh profile data
  const refreshProfile = useCallback(async () => {
    try {
      const profile = await authService.getProfile();
      setPharmacist(profile);
      return profile;
    } catch (err) {
      logger.error('Failed to refresh profile:', err);
      throw err;
    }
  }, []);

  return {
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
}
