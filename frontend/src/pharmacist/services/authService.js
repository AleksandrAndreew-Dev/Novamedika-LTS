// Pharmacist authentication service
import { api } from '../../api/client';

export const authService = {
  /**
   * Set session token directly 
   * @param {string} sessionToken - Session token
   */
  setSessionToken(sessionToken) {
    localStorage.setItem('pharmacist_session_token', sessionToken);
    // NOTE: Don't set api.defaults.headers here - the interceptor in client.js
    // will automatically add the Authorization header from localStorage for each request.
    // This avoids conflicts and ensures consistency.
  },

  /**
   * Login pharmacist via Telegram WebApp
   * @returns {Promise<{session_token: string}>}
   */
  async loginWithTelegram() {
    // Check if we're in Telegram environment
    if (!window.Telegram?.WebApp) {
      throw new Error('Not in Telegram WebApp environment. Please open from Telegram bot.');
    }
    
    // Get initData from Telegram SDK
    const initData = window.Telegram.WebApp.initData;
    
    if (!initData) {
      throw new Error('Telegram initData not available. Please reload the WebApp.');
    }
    
    const response = await api.post('/api/pharmacist/login/telegram/', {
      initData: initData
    });
    
    if (response.data.session_token) {
      this.setSessionToken(response.data.session_token);
    }
    
    return response.data;
  },

  /**
   * Logout pharmacist
   * @returns {Promise<void>}
   */
  async logout() {
    try {
      // Call backend logout endpoint
      await api.post('/api/pharmacist/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API call success
      localStorage.removeItem('pharmacist_session_token');
    }
  },

  /**
   * Get current pharmacist profile
   * @returns {Promise<Object>}
   */
  async getProfile() {
    const response = await api.get('/api/pharmacist/me');
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
    return !!localStorage.getItem('pharmacist_session_token');
  },

  /**
   * Get current session token
   * @returns {string|null}
   */
  getSessionToken() {
    return localStorage.getItem('pharmacist_session_token');
  },
};
