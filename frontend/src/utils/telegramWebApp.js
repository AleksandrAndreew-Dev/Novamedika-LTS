/**
 * Telegram WebApp Initialization Utility
 * 
 * This utility initializes the Telegram WebApp SDK and provides
 * helper functions to interact with Telegram's WebApp API.
 * 
 * Documentation: https://core.telegram.org/bots/webapps
 */

class TelegramWebApp {
  constructor() {
    this.webApp = null;
    this.isInitialized = false;
    this.initData = null;
    this.user = null;
  }

  /**
   * Initialize Telegram WebApp
   * Should be called once when the app starts
   */
  initialize() {
    if (this.isInitialized) {
      console.log('[TelegramWebApp] Already initialized');
      return;
    }

    // Check if Telegram WebApp is available
    if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
      this.webApp = window.Telegram.WebApp;
      
      console.log('[TelegramWebApp] SDK detected');
      console.log('[TelegramWebApp] Platform:', this.webApp.platform);
      console.log('[TelegramWebApp] Version:', this.webApp.version);
      
      // Get initData (contains signed user data from Telegram)
      this.initData = this.webApp.initData;
      this.initDataUnsafe = this.webApp.initDataUnsafe;
      
      console.log('[TelegramWebApp] InitData available:', !!this.initData);
      console.log('[TelegramWebApp] User data:', this.initDataUnsafe?.user);
      
      // Extract user info if available
      if (this.initDataUnsafe?.user) {
        this.user = {
          id: this.initDataUnsafe.user.id,
          first_name: this.initDataUnsafe.user.first_name,
          last_name: this.initDataUnsafe.user.last_name,
          username: this.initDataUnsafe.user.username,
          language_code: this.initDataUnsafe.user.language_code,
          is_premium: this.initDataUnsafe.user.is_premium,
        };
      }
      
      // Mark as ready
      this.webApp.ready();
      
      // Expand to full height
      this.webApp.expand();
      
      // Set header color to match app theme
      this.webApp.setHeaderColor('secondary_bg_color');
      
      this.isInitialized = true;
      
      console.log('[TelegramWebApp] ✅ Initialized successfully');
    } else {
      console.warn('[TelegramWebApp] ⚠️ Telegram WebApp SDK not found - running outside Telegram?');
      console.warn('[TelegramWebApp] Some features may not work properly');
      
      // Still mark as initialized so app can continue
      this.isInitialized = true;
    }
  }

  /**
   * Close the WebApp
   */
  close() {
    if (this.webApp) {
      this.webApp.close();
    }
  }

  /**
   * Show alert dialog
   */
  showAlert(message) {
    if (this.webApp) {
      this.webApp.showAlert(message);
    } else {
      alert(message);
    }
  }

  /**
   * Show confirm dialog
   */
  showConfirm(message) {
    if (this.webApp) {
      return new Promise((resolve) => {
        this.webApp.showConfirm(message, resolve);
      });
    } else {
      return Promise.resolve(confirm(message));
    }
  }

  /**
   * Enable closing confirmation
   */
  enableClosingConfirmation() {
    if (this.webApp) {
      this.webApp.enableClosingConfirmation();
    }
  }

  /**
   * Disable closing confirmation
   */
  disableClosingConfirmation() {
    if (this.webApp) {
      this.webApp.disableClosingConfirmation();
    }
  }

  /**
   * Get theme params
   */
  getThemeParams() {
    if (this.webApp) {
      return this.webApp.themeParams;
    }
    return {};
  }

  /**
   * Check if running in Telegram
   */
  isInTelegram() {
    return !!(this.webApp && this.webApp.initData);
  }

  /**
   * Get color scheme (light/dark)
   */
  getColorScheme() {
    if (this.webApp) {
      return this.webApp.colorScheme;
    }
    return 'light';
  }

  /**
   * Set background color
   */
  setBackgroundColor(color) {
    if (this.webApp) {
      document.body.style.backgroundColor = color;
    }
  }

  /**
   * Apply theme colors from Telegram
   */
  applyTheme() {
    if (!this.webApp || !this.webApp.themeParams) {
      return;
    }

    const theme = this.webApp.themeParams;
    
    // Apply colors to CSS variables
    document.documentElement.style.setProperty('--tg-theme-bg-color', theme.bg_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-text-color', theme.text_color || '#000000');
    document.documentElement.style.setProperty('--tg-theme-hint-color', theme.hint_color || '#707579');
    document.documentElement.style.setProperty('--tg-theme-link-color', theme.link_color || '#3390ec');
    document.documentElement.style.setProperty('--tg-theme-button-color', theme.button_color || '#3390ec');
    document.documentElement.style.setProperty('--tg-theme-button-text-color', theme.button_text_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', theme.secondary_bg_color || '#f4f4f5');
    
    // Apply to body
    document.body.style.backgroundColor = theme.bg_color || '#ffffff';
    document.body.style.color = theme.text_color || '#000000';
  }
}

// Create singleton instance
export const telegramWebApp = new TelegramWebApp();

// Auto-initialize on module load
if (typeof window !== 'undefined') {
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      telegramWebApp.initialize();
    });
  } else {
    telegramWebApp.initialize();
  }
}

export default telegramWebApp;
