import { useState, useCallback } from 'react';

/**
 * Hook для управления Toast уведомлениями
 * 
 * Использование:
 * const { showToast, hideToast } = useToast();
 * showToast('Успешно!', 'success');
 */
export default function useToast() {
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = 'info', duration = 3000) => {
    setToast({ message, type, duration });
  }, []);

  const hideToast = useCallback(() => {
    setToast(null);
  }, []);

  return { toast, showToast, hideToast };
}
