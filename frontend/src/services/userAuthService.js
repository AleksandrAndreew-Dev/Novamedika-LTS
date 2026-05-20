// User authentication service for web app users (not pharmacists)
import api from '../api/client';
import { logger } from '../utils/logger';

class UserAuthService {
  /**
   * Register a new user
   * @param {Object} userData - User registration data
   * @param {string} userData.email - Email address (optional if phone provided)
   * @param {string} userData.phone - Phone number (optional if email provided)
   * @param {string} userData.password - Password
   * @param {string} userData.first_name - First name (optional)
   * @param {string} userData.last_name - Last name (optional)
   * @param {boolean} userData.consent_privacy_policy - Privacy policy consent
   * @returns {Promise<Object>} Registered user data
   */
  async register(userData) {
    try {
      const response = await api.post('/api/auth/register/', userData);
      return response.data;
    } catch (error) {
      logger.error('User registration failed:', error);
      throw error;
    }
  }

  /**
   * Login user with email/phone and password
   * @param {Object} loginData - Login credentials
   * @param {string} loginData.email - Email (optional if phone provided)
   * @param {string} loginData.phone - Phone (optional if email provided)
   * @param {string} loginData.password - Password
   * @returns {Promise<{access_token: string, refresh_token: string, token_type: string, expires_in: number}>}
   */
  async login(loginData) {
    try {
      const response = await api.post('/api/auth/login/', loginData);
      
      // Store tokens
      if (response.data.access_token) {
        localStorage.setItem('user_access_token', response.data.access_token);
        localStorage.setItem('user_refresh_token', response.data.refresh_token);
        
        // Set authorization header for future requests
        this.setAccessToken(response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      logger.error('User login failed:', error);
      throw error;
    }
  }

  /**
   * Logout user
   * @returns {Promise<void>}
   */
  async logout() {
    try {
      const refreshToken = localStorage.getItem('user_refresh_token');
      
      if (refreshToken) {
        // Notify backend to invalidate refresh token
        await api.post('/api/auth/logout/', null, {
          params: { refresh_token: refreshToken }
        });
      }
    } catch (error) {
      logger.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API call success
      localStorage.removeItem('user_access_token');
      localStorage.removeItem('user_refresh_token');
      
      // Clear authorization header
      delete api.defaults.headers.common['Authorization'];
    }
  }

  /**
   * Get current user profile
   * @returns {Promise<Object>} User profile data
   */
  async getProfile() {
    const token = localStorage.getItem('user_access_token');
    if (!token) {
      throw new Error('No access token');
    }

    try {
      const response = await api.get('/api/auth/me/');
      return response.data;
    } catch (error) {
      if (error.response?.status === 401) {
        // Token expired - try to refresh
        try {
          await this.refreshAccessToken();
          // Retry getting profile with new token
          const response = await api.get('/api/auth/me/');
          return response.data;
        } catch (_refreshError) {
          // Refresh failed - clear tokens
          localStorage.removeItem('user_access_token');
          localStorage.removeItem('user_refresh_token');
          throw new Error('Session expired');
        }
      }
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   * @returns {Promise<{access_token: string, refresh_token: string}>}
   */
  async refreshAccessToken() {
    const refreshToken = localStorage.getItem('user_refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token');
    }

    try {
      const response = await api.post('/api/auth/refresh/', null, {
        params: { refresh_token: refreshToken }
      });
      
      // Store new tokens
      if (response.data.access_token) {
        localStorage.setItem('user_access_token', response.data.access_token);
        localStorage.setItem('user_refresh_token', response.data.refresh_token);
        
        // Update authorization header
        this.setAccessToken(response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      logger.error('Token refresh failed:', error);
      // Clear invalid tokens
      localStorage.removeItem('user_access_token');
      localStorage.removeItem('user_refresh_token');
      throw error;
    }
  }

  /**
   * Set access token in API client headers
   * @param {string} token - JWT access token
   */
  setAccessToken(token) {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  }

  /**
   * Check if user is authenticated
   * @returns {boolean}
   */
  isAuthenticated() {
    return !!localStorage.getItem('user_access_token');
  }

  /**
   * Get current access token
   * @returns {string|null}
   */
  getAccessToken() {
    return localStorage.getItem('user_access_token');
  }

  /**
   * Initialize auth state on app load
   * Sets up token in headers if exists
   */
  initializeAuth() {
    const token = localStorage.getItem('user_access_token');
    if (token) {
      this.setAccessToken(token);
    }
  }
}

export const userAuthService = new UserAuthService();
export default userAuthService;
