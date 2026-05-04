# Исправление модального окна согласия для Production

**Дата:** 4 мая 2026 г.  
**Проблема:** После CI/CD на `https://spravka.novamedika.com/` модальное окно не появляется  
**Статус:** ✅ Исправлено

---

## 🔧 Что было исправлено

### Проблема:
В коде была проверка `window.location.protocol === "https:"`, которая могла вызывать проблемы в некоторых браузерах или при определенных конфигурациях.

### Решение:
1. **Удалена проверка HTTPS протокола** - теперь модальное окно показывается независимо от протокола
2. **Добавлено детальное логирование** - для диагностики проблем в production
3. **Добавлена зависимость от [isPharmacistMode](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\frontend\src\App.jsx#L38-L38)** - чтобы правильно реагировать на изменения режима

### Измененный код (`frontend/src/App.jsx`):

```javascript
useEffect(() => {
  const isInTelegram = window.Telegram?.WebApp;
  const cookiesAccepted = localStorage.getItem("cookiesAccepted");
  
  // Debug logging для production диагностики
  console.log('[Consent Modal Check]', {
    isInTelegram,
    cookiesAccepted,
    protocol: window.location.protocol,
    hostname: window.location.hostname,
    pathname: window.location.pathname,
    isPharmacistMode
  });
  
  // Показываем модальное окно если:
  // 1. Не в Telegram WebApp
  // 2. Нет записи о согласии в localStorage
  // 3. Не в режиме фармацевта (там своя аутентификация)
  if (!isInTelegram && !cookiesAccepted && !isPharmacistMode) {
    console.log('[Consent Modal] ✅ Showing modal');
    setShowCookieBanner(true);
  } else {
    console.log('[Consent Modal] ❌ NOT showing', {
      reason: isInTelegram ? 'in Telegram' : 
              cookiesAccepted ? 'already accepted' : 
              'pharmacist mode'
    });
  }
}, [isPharmacistMode]);
```

---

## 🚀 Инструкция по деплою

### Шаг 1: Закоммитить изменения
```bash
git add frontend/src/App.jsx
git commit -m "fix: remove HTTPS check from consent modal and add debug logging"
git push origin main
```

### Шаг 2: CI/CD автоматически задеплоит
После пуша в `main`, GitHub Actions автоматически:
1. Сбилдит фронтенд
2. Задеплоит на сервер
3. Перезапустит контейнеры

### Шаг 3: Очистить кэш браузера (для тестирования)

**Вариант A: Hard Refresh**
- Windows/Linux: `Ctrl + Shift + R` или `Ctrl + F5`
- Mac: `Cmd + Shift + R`

**Вариант B: Очистка через DevTools**
1. Открыть DevTools (`F12`)
2. Правый клик на кнопке Reload → "Empty Cache and Hard Reload"

**Вариант C: Ручная очистка**
1. Открыть настройки браузера
2. Найти "Очистить данные браузера"
3. Выбрать "Файлы cookie и другие данные сайтов"
4. Удалить данные для `spravka.novamedika.com`

---

## 🧪 Тестирование в Production

### Проверка 1: Модальное окно появляется
1. Откройте `https://spravka.novamedika.com/` в режиме инкогнито
2. Должно появиться модальное окно с 3 чекбоксами
3. Откройте Console (`F12` → Console tab)
4. Должны быть логи:
   ```
   [Consent Modal Check] {isInTelegram: undefined, cookiesAccepted: null, ...}
   [Consent Modal] ✅ Showing modal
   ```

### Проверка 2: Чекбоксы работают
1. Попробуйте нажать кнопку "Принять и продолжить" без отметки чекбоксов
2. Кнопка должна быть **disabled** (серая, не кликабельная)
3. Отметьте все 3 чекбокса
4. Кнопка должна стать **enabled** (синяя, кликабельная)

### Проверка 3: Согласие сохраняется
1. Отметьте все чекбоксы
2. Нажмите "Принять и продолжить"
3. Модальное окно должно закрыться
4. В Console должен быть лог:
   ```
   [Consent Modal] User accepted all consents
   [Consent Modal] Consents saved: {...}
   ```
5. Обновите страницу (`F5`)
6. Модальное окно НЕ должно появиться снова

### Проверка 4: Повторное появление после очистки
1. Откройте DevTools → Application → Local Storage
2. Найдите ключ `cookiesAccepted`
3. Удалите его (правый клик → Delete)
4. Обновите страницу
5. Модальное окно должно появиться снова

---

## 🐛 Диагностика проблем

Если модальное окно все еще не появляется:

### Шаг 1: Проверить Console логи
Откройте `https://spravka.novamedika.com/` и посмотрите в Console:

**Если видите:**
```
[Consent Modal Check] {isInTelegram: undefined, cookiesAccepted: "true", ...}
[Consent Modal] ❌ NOT showing {reason: "already accepted"}
```
→ **Проблема:** В localStorage осталась запись `cookiesAccepted=true`  
→ **Решение:** Очистите localStorage (см. выше)

**Если видите:**
```
[Consent Modal Check] {isInTelegram: {...}, cookiesAccepted: null, ...}
[Consent Modal] ❌ NOT showing {reason: "in Telegram"}
```
→ **Проблема:** Браузер определяет сайт как Telegram WebApp  
→ **Решение:** Откройте сайт в обычном браузере, не через Telegram

**Если видите:**
```
[Consent Modal Check] {..., isPharmacistMode: true, ...}
[Consent Modal] ❌ NOT showing {reason: "pharmacist mode"}
```
→ **Проблема:** Сайт определяется как pharmacist поддомен  
→ **Решение:** Используйте основной домен `spravka.novamedika.com`, а не `pharmacist.spravka.novamedika.com`

**Если НЕ видите никаких логов:**
→ **Проблема:** Новый код не задеплоился  
→ **Решение:** 
1. Проверьте статус CI/CD pipeline в GitHub Actions
2. Убедитесь, что деплой завершился успешно
3. Очистите кэш CDN (если используется)
4. Подождите 5-10 минут для распространения изменений

### Шаг 2: Проверить версию файла
Откройте в браузере: `view-source:https://spravka.novamedika.com/assets/index-*.js`  
Найдите текст `[Consent Modal Check]`  
Если не нашли → старый код еще на сервере

### Шаг 3: Проверить Network tab
1. Откройте DevTools → Network
2. Обновите страницу
3. Найдите запросы к `.js` файлам
4. Проверьте, что загружается новая версия (смотрите размер файла или время модификации)

---

## 📊 Ожидаемое поведение

| Сценарий | Ожидается |
|----------|-----------|
| Первый визит (новый браузер) | ✅ Модальное окно появляется |
| После принятия согласия | ❌ Модальное окно НЕ появляется |
| После очистки localStorage | ✅ Модальное окно появляется снова |
| В Telegram WebApp | ❌ Модальное окно НЕ появляется (используется бот) |
| На поддомене pharmacist | ❌ Модальное окно НЕ появляется (своя аутентификация) |
| Через 5 минут после деплоя | ✅ Новая версия должна работать |

---

## ⚠️ Важные замечания

1. **Кэширование браузера**: Даже после деплоя, браузер может использовать старую версию из кэша. Всегда тестируйте в режиме инкогнито или после полной очистки кэша.

2. **CDN кэш**: Если используется Cloudflare или другой CDN, может потребоваться ручная очистка кэша через панель управления.

3. **Service Workers**: Если в проекте есть service workers, они могут кэшировать старую версию. Проверьте наличие `service-worker.js` и при необходимости зарегистрируйте новую версию.

4. **Логи в production**: Console логи видны всем пользователям в DevTools. После подтверждения работы, рекомендуется убрать или уменьшить уровень логирования.

---

## 🎯 Следующие шаги после подтверждения работы

1. **Убрать debug логи** (опционально):
   ```javascript
   // Заменить console.log на условные логи
   if (import.meta.env.DEV) {
     console.log('[Consent Modal Check]', {...});
   }
   ```

2. **Добавить backend API** для сохранения согласий в БД (сейчас только localStorage)

3. **Создать таблицу логирования** всех согласий для аудита ОАЦ

4. **Реализовать отзыв согласия** (`/revoke_consent`)

---

**Статус:** ✅ Готово к деплою  
**Тестирование:** Требуется проверка в production после деплоя  
**Автор:** AI Assistant
