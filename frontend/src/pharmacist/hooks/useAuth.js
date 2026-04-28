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
        // Try to get profile to verify token is valid
        const profile = await authService.getProfile();
        setPharmacist(profile);
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } catch (err) {
      logger.error('Auth check failed:', err);
      // Token might be expired, try to refresh
      const refreshToken = authService.getRefreshToken();
      if (refreshToken) {
        try {
          await authService.refresh(refreshToken);
          const profile = await authService.getProfile();
          setPharmacist(profile);
          setIsAuthenticated(true);
        } catch (refreshErr) {
          logger.error('Token refresh failed:', refreshErr);
          setIsAuthenticated(false);
          setPharmacist(null);
        }
      } else {
        setIsAuthenticated(false);
        setPharmacist(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

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
      
      logger.info(`Online status updated: ${isOnline}`);
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
    error,
    login,
    logout,
    setOnlineStatus,
    refreshProfile,
    checkAuth,
  };
}
