// Pharmacist authentication service
import { api } from '../../api/client';

export const authService = {
  /**
   * Set access token directly (for URL-based authentication)
   * @param {string} accessToken - JWT access token
   */
  setAccessToken(accessToken) {
    localStorage.setItem('pharmacist_access_token', accessToken);
    api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  },

  /**
   * Login pharmacist
   * @param {Object} credentials - Login credentials
   * @param {number} credentials.telegram_id - Telegram ID
   * @returns {Promise<{access_token: string, refresh_token: string}>}
   */
  async login(credentials) {
    const response = await api.post('/api/pharmacist/login/', credentials);
    
    if (response.data.access_token) {
      this.setAccessToken(response.data.access_token);
      localStorage.setItem('pharmacist_refresh_token', response.data.refresh_token);
    }
    
    return response.data;
  },

  /**
   * Refresh access token
   * @param {string} refreshToken - Current refresh token
   * @returns {Promise<{access_token: string}>}
   */
  async refresh(refreshToken) {
    try {
      const response = await api.post('/api/pharmacist/refresh/', {
        refresh_token: refreshToken,
      });
      
      if (response.data.access_token) {
        this.setAccessToken(response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      // If refresh fails, clear tokens and redirect to login
      this.logout();
      throw error;
    }
  },

  /**
   * Logout pharmacist
   * @param {string} refreshToken - Refresh token to revoke
   * @returns {Promise<void>}
   */
  async logout(refreshToken) {
    try {
      if (refreshToken) {
        await api.post('/api/pharmacist/logout/', {
          refresh_token: refreshToken,
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API call success
      localStorage.removeItem('pharmacist_access_token');
      localStorage.removeItem('pharmacist_refresh_token');
      delete api.defaults.headers.common['Authorization'];
    }
  },

  /**
   * Get current pharmacist profile
   * @returns {Promise<Object>}
   */
  async getProfile() {
    const response = await api.get('/api/pharmacist/profile');
    return response.data;
  },

  /**
   * Update pharmacist online status
   * @param {boolean} isOnline - Online status
   * @returns {Promise<Object>}
   */
  async setOnlineStatus(isOnline) {
    const endpoint = isOnline ? '/api/pharmacist/online' : '/api/pharmacist/offline';
    const response = await api.put(endpoint);
    return response.data;
  },

  /**
   * Get pharmacist status
   * @returns {Promise<{is_online: boolean, last_seen: string, is_active: boolean}>}
   */
  async getStatus() {
    const response = await api.get('/api/pharmacist/status');
    return response.data;
  },

  /**
   * Check if user is authenticated
   * @returns {boolean}
   */
  isAuthenticated() {
    return !!localStorage.getItem('pharmacist_access_token');
  },

  /**
   * Get current access token
   * @returns {string|null}
   */
  getAccessToken() {
    return localStorage.getItem('pharmacist_access_token');
  },

  /**
   * Get current refresh token
   * @returns {string|null}
   */
  getRefreshToken() {
    return localStorage.getItem('pharmacist_refresh_token');
  },
};
