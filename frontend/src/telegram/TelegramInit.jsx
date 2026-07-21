import { useEffect } from 'react';

const TelegramInit = () => {
  useEffect(() => {
    if (
      document.querySelector(
        'script[src*="telegram-web-app"]',
      )
    ) {
      return;
    }

    const script = document.createElement('script');
    script.src =
      'https://telegram.org/js/telegram-web-app.js';
    script.async = true;
    script.defer = true;
    script.setAttribute('data-initialized', 'true');
    document.head.appendChild(script);

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, []);

  return null;
};

export default TelegramInit;
