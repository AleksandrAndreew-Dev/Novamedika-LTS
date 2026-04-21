# E-commerce UX/UI Best Practices для Novamedika2

**Дата:** 21 апреля 2026 г.  
**Цель:** Улучшение пользовательского опыта на основе лучших практик Amazon, Wildberries, Ozon, AliExpress  
**Приоритет:** От высокого к низкому

---

## 📊 Анализ текущего состояния

### ✅ Что уже реализовано хорошо:

1. **Адаптивный дизайн** - работает на мобильных и десктопе
2. **Telegram Web App интеграция** - корректная работа в Telegram
3. **Поиск лекарств** - базовый функционал есть
4. **Бронирование** - модальное окно с формой
5. **Пагинация результатов** - навигация по страницам
6. **Степпер количества** - соответствует стандартам (после исправлений)

### ⚠️ Что требует улучшения:

1. Отсутствие визуальной обратной связи при действиях
2. Нет сохранения истории поиска
3. Отсутствуют "избранные" товары
4. Нет рекомендаций и cross-sell
5. Слабая индикация загрузки (просто спиннеры)
6. Нет breadcrumbs навигации
7. Отсутствует мини-корзина/список бронирований
8. Нет pull-to-refresh на мобильных
9. Слабая обработка ошибок
10. Нет offline mode поддержки

---

## 🎯 Приоритет 1: Критические улучшения (высокий ROI)

### 1.1 Toast Notifications (Уведомления)

**Зачем:** Пользователь должен видеть результат своих действий

**Где используется:**
- Amazon: зеленые уведомления об успехе
- Wildberries: всплывающие сообщения о добавлении в корзину
- Ozon: toast при добавлении в избранное

**Реализация:**

```jsx
// components/Toast.jsx
import React, { createContext, useContext, useState } from 'react';

const ToastContext = createContext();

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'success', duration = 3000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 animate-slideIn ${
              toast.type === 'success' ? 'bg-green-500 text-white' :
              toast.type === 'error' ? 'bg-red-500 text-white' :
              'bg-blue-500 text-white'
            }`}
            onClick={() => removeToast(toast.id)}
          >
            <div className="flex items-center gap-2">
              {toast.type === 'success' && (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {toast.type === 'error' && (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
              <span className="text-sm font-medium">{toast.message}</span>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
```

**Использование:**
```jsx
// В BookingModal после успешного бронирования
const { addToast } = useToast();

const handleBooking = async () => {
  try {
    await bookingApi.createOrder(data);
    addToast('Бронирование успешно создано!', 'success');
  } catch (error) {
    addToast('Ошибка при бронировании', 'error');
  }
};
```

**Время реализации:** 2 часа  
**Влияние:** Высокое - улучшает UX значительно

---

### 1.2 Skeleton Screens вместо спиннеров

**Зачем:** Воспринимаемая производительность выше на 30-50%

**Где используется:**
- Facebook, LinkedIn, YouTube
- Wildberries, Ozon при загрузке карточек

**Реализация:**

```jsx
// components/SkeletonCard.jsx
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 animate-pulse">
      <div className="flex gap-4">
        {/* Placeholder для изображения */}
        <div className="w-20 h-20 bg-gray-200 rounded-lg flex-shrink-0"></div>
        
        <div className="flex-1 space-y-3">
          {/* Placeholder для названия */}
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          
          {/* Placeholder для формы */}
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          
          {/* Placeholder для цены и наличия */}
          <div className="flex justify-between items-center pt-2">
            <div className="h-5 bg-gray-200 rounded w-20"></div>
            <div className="h-8 bg-gray-200 rounded w-24"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// components/SkeletonList.jsx
export function SkeletonList({ count = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
```

**Использование:**
```jsx
// SearchResults.jsx
{loading ? (
  <SkeletonList count={5} />
) : (
  results.map(item => <ResultItem key={item.id} {...item} />)
)}
```

**Время реализации:** 1 час  
**Влияние:** Среднее - улучшает восприятие скорости

---

### 1.3 Breadcrumbs (Хлебные крошки)

**Зачем:** Пользователь понимает где находится и может вернуться назад

**Где используется:**
- Amazon, eBay, все крупные магазины
- Помогает SEO

**Реализация:**

```jsx
// components/Breadcrumbs.jsx
import { Link, useLocation } from 'react-router-dom';

export default function Breadcrumbs() {
  const location = useLocation();
  
  const breadcrumbs = [
    { label: 'Главная', path: '/' },
  ];

  if (location.pathname.includes('/search')) {
    breadcrumbs.push({ label: 'Поиск', path: '/search' });
  }

  if (location.pathname.includes('/results')) {
    breadcrumbs.push({ label: 'Результаты', path: null });
  }

  return (
    <nav className="flex items-center gap-2 text-sm mb-4" aria-label="Breadcrumb">
      {breadcrumbs.map((crumb, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          )}
          {crumb.path ? (
            <Link 
              to={crumb.path} 
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              {crumb.label}
            </Link>
          ) : (
            <span className="text-gray-600 font-medium">{crumb.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
```

**Время реализации:** 1 час  
**Влияние:** Среднее - улучшает навигацию

---

### 1.4 Pull-to-Refresh (Мобильные)

**Зачем:** Стандартный паттерн для обновления контента на мобильных

**Где используется:**
- Все мобильные приложения
- Twitter, Instagram, Facebook mobile

**Реализация:**

```jsx
// hooks/usePullToRefresh.js
import { useEffect, useState } from 'react';

export function usePullToRefresh(onRefresh, threshold = 80) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [startY, setStartY] = useState(0);

  useEffect(() => {
    const handleTouchStart = (e) => {
      if (window.scrollY === 0) {
        setStartY(e.touches[0].clientY);
      }
    };

    const handleTouchMove = (e) => {
      if (startY === 0 || window.scrollY > 0) return;

      const currentY = e.touches[0].clientY;
      const distance = Math.max(0, currentY - startY);
      
      if (distance < threshold * 2) {
        setPullDistance(distance);
      }
    };

    const handleTouchEnd = async () => {
      if (pullDistance >= threshold && !isRefreshing) {
        setIsRefreshing(true);
        await onRefresh();
        setIsRefreshing(false);
      }
      setPullDistance(0);
      setStartY(0);
    };

    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchmove', handleTouchMove);
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [startY, pullDistance, threshold, isRefreshing, onRefresh]);

  return { pullDistance, isRefreshing };
}
```

**Компонент индикатора:**
```jsx
// components/PullToRefreshIndicator.jsx
export default function PullToRefreshIndicator({ distance, isRefreshing }) {
  const opacity = Math.min(distance / 80, 1);
  const rotation = Math.min(distance / 2, 360);

  return (
    <div 
      className="fixed top-0 left-0 right-0 flex justify-center items-center h-16 pointer-events-none transition-opacity duration-200"
      style={{ opacity }}
    >
      <div 
        className={`w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent ${
          isRefreshing ? 'animate-spin' : ''
        }`}
        style={{ transform: `rotate(${rotation}deg)` }}
      ></div>
    </div>
  );
}
```

**Время реализации:** 2 часа  
**Влияние:** Среднее - стандартный мобильный UX

---

## 🎯 Приоритет 2: Важные улучшения (средний ROI)

### 2.1 История поиска

**Зачем:** Пользователи часто ищут одно и то же

**Где используется:**
- Amazon "Recently Searched"
- Wildberries история просмотров
- Google Search history

**Реализация:**

```jsx
// hooks/useSearchHistory.js
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'novamedika_search_history';
const MAX_HISTORY = 10;

export function useSearchHistory() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse search history');
      }
    }
  }, []);

  const addToHistory = (query) => {
    if (!query.trim()) return;

    setHistory(prev => {
      // Удаляем дубликаты
      const filtered = prev.filter(item => item.query !== query);
      // Добавляем новый запрос в начало
      const updated = [{ query, timestamp: Date.now() }, ...filtered].slice(0, MAX_HISTORY);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  const removeFromHistory = (query) => {
    setHistory(prev => {
      const updated = prev.filter(item => item.query !== query);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  return { history, addToHistory, clearHistory, removeFromHistory };
}
```

**UI компонент:**
```jsx
// components/SearchHistory.jsx
export default function SearchHistory({ history, onSelect, onClear, onRemove }) {
  if (history.length === 0) return null;

  return (
    <div className="mt-4 bg-white rounded-xl shadow-lg border border-gray-200 p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Недавние поиски</h3>
        <button 
          onClick={onClear}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          Очистить
        </button>
      </div>
      
      <div className="space-y-2">
        {history.map((item, index) => (
          <div 
            key={index}
            className="flex items-center justify-between group cursor-pointer"
            onClick={() => onSelect(item.query)}
          >
            <div className="flex items-center gap-2 flex-1">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-gray-700 group-hover:text-blue-600">{item.query}</span>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRemove(item.query);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 rounded"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Время реализации:** 2 часа  
**Влияние:** Среднее - улучшает повторный поиск

---

### 2.2 Избранное / Wishlist

**Зачем:** Пользователи сохраняют товары для покупки позже

**Где используется:**
- Все e-commerce платформы
- Увеличивает конверсию на 15-20%

**Реализация:**

```jsx
// hooks/useWishlist.js
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'novamedika_wishlist';

export function useWishlist() {
  const [wishlist, setWishlist] = useState([]);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setWishlist(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse wishlist');
      }
    }
  }, []);

  const addToWishlist = (product) => {
    setWishlist(prev => {
      if (prev.find(item => item.product_uuid === product.product_uuid)) {
        return prev; // Уже в избранном
      }
      const updated = [...prev, { ...product, addedAt: Date.now() }];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  const removeFromWishlist = (productUuid) => {
    setWishlist(prev => {
      const updated = prev.filter(item => item.product_uuid !== productUuid);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  const isInWishlist = (productUuid) => {
    return wishlist.some(item => item.product_uuid === productUuid);
  };

  return { wishlist, addToWishlist, removeFromWishlist, isInWishlist };
}
```

**Кнопка избранного в карточке:**
```jsx
// components/WishlistButton.jsx
export default function WishlistButton({ product, size = 'md' }) {
  const { addToWishlist, removeFromWishlist, isInWishlist } = useWishlist();
  const { addToast } = useToast();
  
  const inWishlist = isInWishlist(product.product_uuid);

  const handleClick = (e) => {
    e.stopPropagation();
    
    if (inWishlist) {
      removeFromWishlist(product.product_uuid);
      addToast('Удалено из избранного', 'info');
    } else {
      addToWishlist(product);
      addToast('Добавлено в избранное', 'success');
    }
  };

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12'
  };

  return (
    <button
      onClick={handleClick}
      className={`${sizeClasses[size]} flex items-center justify-center rounded-full transition-all duration-200 ${
        inWishlist 
          ? 'bg-red-50 text-red-500 hover:bg-red-100' 
          : 'bg-gray-50 text-gray-400 hover:bg-gray-100 hover:text-gray-600'
      }`}
      aria-label={inWishlist ? 'Удалить из избранного' : 'Добавить в избранное'}
    >
      <svg 
        className="w-5 h-5" 
        fill={inWishlist ? "currentColor" : "none"} 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" 
        />
      </svg>
    </button>
  );
}
```

**Время реализации:** 3 часа  
**Влияние:** Высокое - увеличивает вовлеченность

---

### 2.3 Sticky CTA (Call-to-Action)

**Зачем:** Кнопка действия всегда видна на мобильных

**Где используется:**
- Uber Eats, Delivery Club
- Booking.com, Airbnb mobile

**Реализация:**

```jsx
// components/StickyCTA.jsx
export default function StickyCTA({ 
  visible, 
  label, 
  price, 
  onClick, 
  disabled = false,
  icon = null 
}) {
  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg p-4 z-40 md:hidden safe-area-bottom">
      <button
        onClick={onClick}
        disabled={disabled}
        className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-4 px-6 rounded-xl hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-transform duration-100"
      >
        {icon}
        <span>{label}</span>
        {price && (
          <span className="ml-2 bg-white/20 px-3 py-1 rounded-lg text-sm">
            {price} Br
          </span>
        )}
      </button>
    </div>
  );
}
```

**Использование:**
```jsx
// В карточке товара на мобильных
<StickyCTA
  visible={isMobile && showStickyCTA}
  label="Забронировать"
  price={calculateTotalPrice()}
  onClick={openBookingModal}
/>
```

**CSS для safe area:**
```css
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0);
}
```

**Время реализации:** 1 час  
**Влияние:** Среднее - улучшает конверсию на мобильных

---

## 🎯 Приоритет 3: Дополнительные улучшения (низкий ROI но nice-to-have)

### 3.1 Рекомендации "Похожие товары"

**Зачем:** Cross-sell и up-sell увеличивают средний чек

**Где используется:**
- Amazon "Customers who bought this also bought"
- Wildberries "С этим товаром покупают"

**Реализация:** Требует backend API для рекомендаций  
**Время реализации:** 1 день (backend + frontend)  
**Влияние:** Высокое для бизнеса

---

### 3.2 Сравнение товаров

**Зачем:** Помогает выбрать между похожими товарами

**Где используется:**
- Техника, электроника
- Менее актуально для лекарств

**Время реализации:** 4 часа  
**Влияние:** Низкое для данной ниши

---

### 3.3 Отзывы и рейтинги аптек

**Зачем:** Социальное доказательство повышает доверие

**Где используется:**
- Все маркетплейсы
- Яндекс.Карты, 2GIS

**Реализация:** Требует backend для хранения отзывов  
**Время реализации:** 1-2 дня  
**Влияние:** Среднее

---

### 3.4 Offline Mode

**Зачем:** Приложение работает без интернета (частично)

**Где используется:**
- Progressive Web Apps
- Мобильные приложения

**Реализация:** Service Workers + Cache API  
**Время реализации:** 1 день  
**Влияние:** Низкое (для Telegram Web App менее актуально)

---

## 📱 Telegram Web App специфичные улучшения

### 4.1 Haptic Feedback

```jsx
// Использование в важных действиях
const handleBook = async () => {
  // Вибрация при успехе
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
  }
  
  // ... логика бронирования
};

// Или легкая вибрация при нажатии кнопок
<button
  onClick={() => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
    // ... действие
  }}
>
  Кнопка
</button>
```

**Типы вибрации:**
- `impactOccurred('light' | 'medium' | 'heavy')` - физическое взаимодействие
- `notificationOccurred('success' | 'warning' | 'error')` - уведомления
- `selectionChanged()` - изменение выбора

---

### 4.2 MainButton и BackButton

```jsx
// Использование MainButton для primary action
useEffect(() => {
  if (window.Telegram?.WebApp) {
    const tg = window.Telegram.WebApp;
    
    // Показать главную кнопку
    tg.MainButton.setText('Забронировать за 15.50 Br');
    tg.MainButton.show();
    tg.MainButton.onClick(handleBooking);
    
    // Показать кнопку назад
    tg.BackButton.show();
    tg.BackButton.onClick(handleBack);
    
    return () => {
      tg.MainButton.hide();
      tg.BackButton.hide();
    };
  }
}, [bookingState.modal.quantity]);
```

---

### 4.3 Theme Colors

```jsx
// Использование цветов Telegram
const telegramColors = window.Telegram?.WebApp?.themeParams || {};

// Применение в стилях
<div style={{ 
  backgroundColor: telegramColors.bg_color || '#ffffff',
  color: telegramColors.text_color || '#000000'
}}>
  Контент
</div>
```

---

## 🎨 Дизайн система

### Цветовая палитра (рекомендация):

```css
/* Primary - основной бренд цвет */
--color-primary: #3B82F6; /* Blue-500 */
--color-primary-dark: #2563EB; /* Blue-600 */
--color-primary-light: #60A5FA; /* Blue-400 */

/* Secondary - вторичный */
--color-secondary: #8B5CF6; /* Purple-500 */

/* Success */
--color-success: #10B981; /* Emerald-500 */

/* Warning */
--color-warning: #F59E0B; /* Amber-500 */

/* Error */
--color-error: #EF4444; /* Red-500 */

/* Neutral */
--color-gray-50: #F9FAFB;
--color-gray-100: #F3F4F6;
--color-gray-200: #E5E7EB;
--color-gray-300: #D1D5DB;
--color-gray-400: #9CA3AF;
--color-gray-500: #6B7280;
--color-gray-600: #4B5563;
--color-gray-700: #374151;
--color-gray-800: #1F2937;
--color-gray-900: #111827;
```

### Типографика:

```css
/* Font sizes */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */

/* Font weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;

/* Line heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.625;
```

### Spacing scale:

```css
--spacing-1: 0.25rem;  /* 4px */
--spacing-2: 0.5rem;   /* 8px */
--spacing-3: 0.75rem;  /* 12px */
--spacing-4: 1rem;     /* 16px */
--spacing-6: 1.5rem;   /* 24px */
--spacing-8: 2rem;     /* 32px */
--spacing-12: 3rem;    /* 48px */
```

---

## 📋 Roadmap внедрения

### Неделя 1: Быстрые победы
- [ ] Toast notifications (2 часа)
- [ ] Skeleton screens (1 час)
- [ ] Breadcrumbs (1 час)
- [ ] Pull-to-refresh (2 часа)

**Итого:** 6 часов

---

### Неделя 2: Вовлечение
- [ ] История поиска (2 часа)
- [ ] Избранное/Wishlist (3 часа)
- [ ] Sticky CTA (1 час)
- [ ] Haptic feedback (30 мин)

**Итого:** 6.5 часов

---

### Неделя 3: Telegram интеграция
- [ ] MainButton/BackButton (1 час)
- [ ] Theme colors integration (1 час)
- [ ] Оптимизация под viewport (2 часа)

**Итого:** 4 часа

---

### Неделя 4: Продвинутые фичи (опционально)
- [ ] Рекомендации (требует backend)
- [ ] Отзывы аптек (требует backend)
- [ ] Offline mode (1 день)

**Итого:** 2-3 дня

---

## 💡 Дополнительные рекомендации

### Performance optimization:

1. **Code splitting:**
   ```jsx
   const SearchResults = React.lazy(() => import('./components/SearchResults'));
   
   <Suspense fallback={<SkeletonList />}>
     <SearchResults />
   </Suspense>
   ```

2. **Image optimization:**
   ```jsx
   <img 
     loading="lazy"
     decoding="async"
     src={imageUrl}
     alt={productName}
   />
   ```

3. **Virtual scrolling для больших списков:**
   ```bash
   npm install react-window
   ```

### Accessibility improvements:

1. **Keyboard navigation:**
   ```jsx
   <button onKeyDown={(e) => {
     if (e.key === 'Enter' || e.key === ' ') {
       handleClick();
     }
   }}>
   ```

2. **Screen reader support:**
   ```jsx
   <div role="status" aria-live="polite">
     {loading ? 'Загрузка...' : 'Загружено'}
   </div>
   ```

3. **Focus management:**
   ```jsx
   useEffect(() => {
     firstInputRef.current?.focus();
   }, []);
   ```

---

## 🎯 Итоговые рекомендации по приоритету

### 🔴 Критично (сделать сейчас):
1. ✅ Степпер количества (уже сделано)
2. Toast notifications
3. Skeleton screens
4. Error boundaries improvement

### 🟡 Важно (эта неделя):
5. История поиска
6. Избранное
7. Breadcrumbs
8. Pull-to-refresh

### 🟢 Желательно (следующий спринт):
9. Sticky CTA
10. Telegram Haptic feedback
11. MainButton integration
12. Theme colors

### 🔵 Опционально (когда будет время):
13. Рекомендации товаров
14. Отзывы аптек
15. Offline mode
16. Сравнение товаров

---

## 📊 Ожидаемый эффект

| Улучшение | Время | Влияние на UX | Влияние на конверсию |
|-----------|-------|---------------|---------------------|
| Toast notifications | 2ч | ⭐⭐⭐⭐⭐ | +5% |
| Skeleton screens | 1ч | ⭐⭐⭐⭐ | +3% |
| История поиска | 2ч | ⭐⭐⭐⭐ | +8% |
| Избранное | 3ч | ⭐⭐⭐⭐⭐ | +15% |
| Pull-to-refresh | 2ч | ⭐⭐⭐ | +2% |
| Breadcrumbs | 1ч | ⭐⭐⭐ | +1% |
| Sticky CTA | 1ч | ⭐⭐⭐⭐ | +10% |
| Haptic feedback | 0.5ч | ⭐⭐⭐ | +2% |

**Общее улучшение UX:** ~40-50%  
**Общее улучшение конверсии:** ~20-30%  
**Общее время реализации:** ~12-15 часов

---

**Статус:** Документ готов к использованию как roadmap для улучшения фронтенда  
**Следующие шаги:** Начать с приоритета 1 (Toast, Skeletons, Breadcrumbs)