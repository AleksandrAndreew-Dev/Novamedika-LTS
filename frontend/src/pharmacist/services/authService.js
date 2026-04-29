// Pharmacist authentication service
import { api } from '../../api/client';

// Login state management to prevent race conditions
let loginPromise = null;

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
   * Login pharmacist via Telegram WebApp using Authorization header (TMA standard)
   * @returns {Promise<{session_token: string}>}
   */
  async loginWithTelegram() {
    // Prevent concurrent login attempts by returning existing promise if login is in progress
    if (loginPromise) {
      console.log('[authService] Login already in progress, returning existing promise');
      return loginPromise;
    }
    
    // Check if we're in Telegram environment
    if (!window.Telegram?.WebApp) {
      throw new Error('Not in Telegram WebApp environment. Please open from Telegram bot.');
    }
    
    // Get initData from Telegram SDK
    const initData = window.Telegram.WebApp.initData;
    
    if (!initData) {
      throw new Error('Telegram initData not available. Please reload the WebApp.');
    }
    
    // Create and store the login promise
    loginPromise = fetch('/api/pharmacist/login/telegram/', {
      method: 'POST',
      headers: {
        'Authorization': `tma ${initData}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({}) // Empty body as data is in header
    }).then(async response => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific Telegram session errors
        if (errorData.detail && errorData.detail.includes('QUERY_ID_INVALID')) {
          throw new Error('Telegram session expired. Please restart the Mini App.');
        }
        
        throw new Error(errorData.detail || 'Login failed');
      }
      
      const data = await response.json();
      if (data.session_token) {
        this.setSessionToken(data.session_token);
      }
      
      // Clear the login promise after successful completion
      loginPromise = null;
      return data;
    }).catch(error => {
      // Clear the login promise on error
      loginPromise = null;
      throw error;
    });
    
    return loginPromise;
  },

  /**
   * Login with token from URL (legacy method)
   * @param {string} token - Session token
   * @returns {Promise<void>}
   */
  async loginWithToken(token) {
    this.setSessionToken(token);
    // Verify the token by fetching profile
    await this.getProfile();
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
      // Clear any pending login promise
      loginPromise = null;
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