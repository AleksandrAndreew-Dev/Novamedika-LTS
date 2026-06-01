// Telegram WebApp authentication for users
// Auto-login via initData when in Telegram environment
import userAuthService from "./userAuthService";
import { logger } from "../utils/logger";

class TelegramAuthService {
  constructor() {
    this.isInTelegram = this._detectTelegram();
    this.initData = this._getInitData();
    this.loginPromise = null;
  }

  /**
   * Check if we're inside Telegram WebApp
   */
  _detectTelegram() {
    return !!(
      window.Telegram?.WebApp?.initData &&
      window.Telegram.WebApp.initData.length > 0
    );
  }

  /**
   * Get initData from Telegram WebApp
   */
  _getInitData() {
    if (this.isInTelegram) {
      return window.Telegram.WebApp.initData;
    }
    return null;
  }

  /**
   * Check if user is already authenticated (via JWT token)
   */
  isAuthenticated() {
    return userAuthService.isAuthenticated();
  }

  /**
   * Check if we can do Telegram WebApp auth
   */
  canAuthViaWebApp() {
    return this.isInTelegram && this.initData && !this.isAuthenticated();
  }

  /**
   * Auto-login user via Telegram WebApp initData
   * Returns true if login was successful, false otherwise
   */
  async autoLogin() {
    // Prevent concurrent login attempts
    if (this.loginPromise) {
      console.log(
        "[TelegramAuthService] Login already in progress, returning existing promise",
      );
      return this.loginPromise;
    }

    // Check if already authenticated
    if (this.isAuthenticated()) {
      console.log("[TelegramAuthService] User already authenticated");
      return true;
    }

    // Check if we can do Telegram auth
    if (!this.canAuthViaWebApp()) {
      console.log("[TelegramAuthService] Cannot authenticate via Telegram", {
        isInTelegram: this.isInTelegram,
        hasInitData: !!this.initData,
        isAuthenticated: this.isAuthenticated(),
      });
      return false;
    }

    // Create login promise
    this.loginPromise = this._performTelegramLogin();

    try {
      const result = await this.loginPromise;
      return result;
    } finally {
      this.loginPromise = null;
    }
  }

  /**
   * Perform actual Telegram login
   */
  async _performTelegramLogin() {
    try {
      console.log("[TelegramAuthService] Starting Telegram WebApp login");

      const response = await fetch("/api/auth/login/telegram/", {
        method: "POST",
        headers: {
          Authorization: `tma ${this.initData}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        logger.error("[TelegramAuthService] Login failed", {
          status: response.status,
          error: errorData.detail || "Unknown error",
        });
        return false;
      }

      const data = await response.json();
      console.log("[TelegramAuthService] Login successful, storing tokens");

      // Store tokens using userAuthService
      if (data.access_token && data.refresh_token) {
        localStorage.setItem("user_access_token", data.access_token);
        localStorage.setItem("user_refresh_token", data.refresh_token);
        userAuthService.setAccessToken(data.access_token);

        console.log(
          "[TelegramAuthService] ✅ User authenticated via Telegram WebApp",
        );
        return true;
      } else {
        logger.error("[TelegramAuthService] No tokens in response", data);
        return false;
      }
    } catch (error) {
      logger.error("[TelegramAuthService] Login error:", error);
      return false;
    }
  }

  /**
   * Get user info from initDataUnsafe (does not require validation)
   */
  getUserInfo() {
    if (this.isInTelegram) {
      return window.Telegram.WebApp.initDataUnsafe?.user || null;
    }
    return null;
  }
}

export const telegramAuthService = new TelegramAuthService();
export default telegramAuthService;
