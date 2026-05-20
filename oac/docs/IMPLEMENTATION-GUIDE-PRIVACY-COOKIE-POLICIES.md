# ИНСТРУКЦИЯ ПО ВНЕДРЕНИЮ COOKIE POLICY И ОБНОВЛЕННОЙ PRIVACY POLICY

**Дата:** 20 мая 2026 г.  
**Приоритет:** 🔴 ВЫСОКИЙ (требуется до следующей проверки ОАЦ)

---

## 📋 ЧТО СДЕЛАНО

### ✅ Созданные документы:
1. **[oac/docs/05-cookie-policy.md](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\05-cookie-policy.md)** - Новая Cookie Policy
2. **[oac/docs/PRIVACY-POLICY-UPDATE-SUMMARY-2026-05-20.md](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\PRIVACY-POLICY-UPDATE-SUMMARY-2026-05-20.md)** - Сводка изменений

### ✅ Обновленные документы:
1. **[oac/docs/04-privacy-policy.md](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\04-privacy-policy.md)** - Privacy Policy с учетом Telegram и cookie

---

## 🎯 КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ

### 1. Cookie Policy (НОВЫЙ ДОКУМЕНТ)

**Что регулирует:**
- Использование cookie-файлов на web-сайте spravka.novamedika.com
- LocalStorage, SessionStorage, Service Workers
- НЕ применяется к Telegram-боту (Telegram не использует cookie)

**Основные моменты:**
- Строго необходимые cookie (без согласия): session_id, auth_token, csrf_token
- Функциональные cookie (с согласием): language, theme, consent_preferences
- Аналитические и маркетинговые cookie: ❌ НЕ используются
- Срок хранения: 1 год для постоянных cookie
- Управление: через браузер, интерфейс сайта, email

---

### 2. Privacy Policy (ОБНОВЛЕН)

**Новые разделы:**

#### Раздел 1.7 - Ссылки на связанные документы:
- Cookie Policy (05-cookie-policy.md)
- Standard Bot Privacy Policy Telegram
- Privacy Policy Telegram

#### Раздел 4 - Трансграничная передача (ПОЛНОСТЬЮ ПЕРЕПИСАН):
- 4.1: Параметры трансграничной передачи через Telegram
- 4.2: Особенности обработки через мессенджеры
- 4.3: Альтернативные каналы связи (web, email, телефон)
- 4.4: Порядок получения согласия
- 4.5: Порядок отзыва согласия
- 4.6: Локальная обработка без трансграничной передачи

#### Раздел 5 - Cookie-файлы (НОВЫЙ):
- Общие положения
- Ссылка на отдельную Cookie Policy
- Основные положения об используемых cookie

---

## 📝 ШАГИ ПО ВНЕДРЕНИЮ

### Этап 1: Заполнение placeholder'ов (1 день)

#### 1.1. Открыть файлы для редактирования

```bash
cd oac/docs
code 04-privacy-policy.md
code 05-cookie-policy.md
```

#### 1.2. Найти и заменить все placeholder'ы

**В 04-privacy-policy.md:**
- `[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ / ИП]` → Реальное название
- `[АДРЕС]` → Юридический адрес
- `[НОМЕР]` → Регистрационный номер в ЕГР
- `[ТЕЛЕФОН]` → Контактный телефон
- `[EMAIL]` → Email для связи
- `[ФИО]` → ФИО генерального директора
- `+375 (XX) XXX-XX-XX` → Реальный номер телефона

**В 05-cookie-policy.md:**
- Те же placeholder'ы + 
- `[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]` в заголовке
- `[ФИО ОТВЕТСТВЕННОГО]` → ФИО ответственного за защиту ПД

#### 1.3. Сохранить изменения

```bash
git add oac/docs/04-privacy-policy.md
git add oac/docs/05-cookie-policy.md
git commit -m "docs: Fill placeholders in privacy and cookie policies

- Replace [НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ] with actual company name
- Replace [АДРЕС], [ТЕЛЕФОН], [EMAIL] with real contact info
- Replace [ФИО] with director's full name
- Update phone numbers to real values"
git push
```

---

### Этап 2: Утверждение документов (1-2 дня)

#### 2.1. Подготовить приказ об утверждении

Создать файл `oac/docs/orders/order-approve-policies-2026.md`:

```markdown
# ПРИКАЗ № ___

от "___" ____________ 2026 г.

Об утверждении Политики обработки персональных данных 
и Политики использования cookie-файлов

В целях обеспечения compliance с требованиями Закона Республики Беларусь 
№99-З «О защите персональных данных» и Приказа ОАЦ №66

ПРИКАЗЫВАЮ:

1. Утвердить следующие документы:
   1.1. Политика обработки персональных данных информационной системы 
        NovaMedika2 (версия 1.2 от 20.05.2026)
   1.2. Политика использования cookie-файлов и аналогичных технологий 
        (версия 1.0 от 20.05.2026)

2. Ответственному за защиту персональных данных [ФИО]:
   2.1. Опубликовать утвержденные документы на сайте spravka.novamedika.com
   2.2. Обеспечить доступность документов с любой страницы сайта (footer)
   2.3. Организовать обучение сотрудников работе с новыми политиками

3. IT-отделу ([ФИО]):
   3.1. Добавить ссылки на политики в footer сайта
   3.2. Обновить модальное окно согласия на cookie
   3.3. Реализовать механизм управления cookie-настройками

4. Контроль за исполнением настоящего приказа оставляю за собой.

Генеральный директор
[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]        _______________ / [ФИО]
```

#### 2.2. Подписать приказ

- Распечатать приказ
- Подписать у генерального директора
- Отсканировать и сохранить в `oac/docs/orders/`

---

### Этап 3: Публикация на сайте (1-2 дня)

#### 3.1. Добавить файлы в public директорию frontend

```bash
# Скопировать markdown файлы в public
cp oac/docs/04-privacy-policy.md frontend/public/privacy-policy.md
cp oac/docs/05-cookie-policy.md frontend/public/cookie-policy.md

# Или конвертировать в HTML (рекомендуется)
# Использовать markdown-to-html converter
```

#### 3.2. Добавить ссылки в footer сайта

Открыть `frontend/src/components/Footer.jsx` (или аналогичный компонент):

```jsx
<footer className="bg-gray-800 text-white py-8">
  <div className="container mx-auto px-4">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* ... existing code ... */}
      
      <div>
        <h3 className="text-lg font-semibold mb-4">Правовая информация</h3>
        <ul className="space-y-2">
          <li>
            <a href="/privacy-policy" className="hover:text-blue-400">
              Политика конфиденциальности
            </a>
          </li>
          <li>
            <a href="/cookie-policy" className="hover:text-blue-400">
              Политика использования cookie
            </a>
          </li>
          <li>
            <button onClick={openCookieSettings} className="hover:text-blue-400">
              Настройки cookie
            </button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</footer>
```

#### 3.3. Создать страницы для политик

Создать `frontend/src/pages/PrivacyPolicy.jsx`:

```jsx
import React from 'react';
import { useMarkdown } from '../hooks/useMarkdown';

const PrivacyPolicy = () => {
  const { content, loading } = useMarkdown('/privacy-policy.md');

  if (loading) return <div>Загрузка...</div>;

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Политика конфиденциальности</h1>
      <div 
        className="prose prose-lg"
        dangerouslySetInnerHTML={{ __html: content }}
      />
    </div>
  );
};

export default PrivacyPolicy;
```

Аналогично создать `frontend/src/pages/CookiePolicy.jsx`.

#### 3.4. Добавить роуты

В `frontend/src/App.jsx`:

```jsx
import PrivacyPolicy from './pages/PrivacyPolicy';
import CookiePolicy from './pages/CookiePolicy';

// ... existing routes ...

<Route path="/privacy-policy" element={<PrivacyPolicy />} />
<Route path="/cookie-policy" element={<CookiePolicy />} />
```

---

### Этап 4: Обновление модального окна cookie (2-3 дня)

#### 4.1. Проверить текущую реализацию

Открыть `frontend/src/App.jsx` и найти модальное окно cookie.

Текущая реализация уже должна содержать чекбоксы согласий. Нужно добавить:
- Ссылку на Cookie Policy
- Информацию о трансграничной передаче (для Telegram WebApp)

#### 4.2. Обновить текст согласия

```jsx
<label className="flex items-start gap-3 cursor-pointer group p-3 rounded-xl hover:bg-gray-50 border-2 border-orange-200 bg-orange-50">
  <input 
    type="checkbox" 
    checked={consents.transboundaryTransfer} 
    onChange={() => handleConsentChange('transboundaryTransfer')} 
    required 
  />
  <div>
    <span className="font-semibold text-orange-900">⚠️ Трансграничная передача данных</span>
    <p className="text-sm text-orange-800 mt-1">
      Я понимаю, что при использовании Telegram-бота мои данные будут передаваться 
      через серверы Telegram (Великобритания, ОАЭ). Я ознакомлен с рисками и добровольно 
      соглашаюсь на такую передачу.{' '}
      <a href="/privacy-policy#section-4" target="_blank" className="underline">
        Подробнее
      </a>
    </p>
  </div>
</label>

<div className="mt-4 text-sm text-gray-600">
  Подробная информация:{' '}
  <a href="/cookie-policy" target="_blank" className="text-blue-600 underline">
    Политика использования cookie-файлов
  </a>
</div>
```

---

### Этап 5: Тестирование (2-3 дня)

#### 5.1. Checklist тестирования

**Web-сайт:**
- [ ] Политика конфиденциальности доступна по ссылке /privacy-policy
- [ ] Cookie Policy доступна по ссылке /cookie-policy
- [ ] Ссылки на политики есть в footer
- [ ] Модальное окно cookie появляется при первом посещении
- [ ] Все чекбоксы работают корректно
- [ ] Кнопка "Принять" активна только при отмеченных всех чекбоксах
- [ ] После принятия модальное окно больше не показывается
- [ ] LocalStorage содержит cookiesAccepted=true

**Telegram-бот:**
- [ ] Команда /start запрашивает согласие (если еще не дано)
- [ ] Текст содержит информацию о трансграничной передаче
- [ ] Есть ссылка на web-сайт как альтернативу
- [ ] Согласие сохраняется в БД

**Документы:**
- [ ] Все placeholder'ы заполнены
- [ ] Нет битых ссылок
- [ ] Форматиров корректный
- [ ] Нумерация разделов правильная

---

### Этап 6: Деплой на production (1 день)

#### 6.1. Закоммитить все изменения

```bash
git add .
git commit -m "feat: Add Cookie Policy and update Privacy Policy with Telegram considerations

- Create comprehensive Cookie Policy (05-cookie-policy.md)
- Update Privacy Policy with transboundary transfer section
- Add references to Telegram privacy policies
- Include alternative communication channels
- Prepare for OAC compliance

Refs: 
- oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md
- oac/docs/PRIVACY-POLICY-UPDATE-SUMMARY-2026-05-20.md"
git push
```

#### 6.2. CI/CD автоматически задеплоит изменения

Проверить статус деплоя:
```bash
# На production сервере
cd /opt/novamedika-prod
docker-compose logs -f
```

#### 6.3. Проверить работу на production

- Открыть spravka.novamedika.com
- Проверить наличие ссылок в footer
- Открыть политики и убедиться в корректном отображении
- Протестировать модальное окно cookie

---

## ✅ CHECKLIST ГОТОВНОСТИ

### Документация:
- [x] Cookie Policy создана
- [x] Privacy Policy обновлена
- [ ] Placeholder'ы заполнены
- [ ] Приказ об утверждении подписан
- [ ] Документы сохранены в oac/docs/

### Frontend:
- [ ] Страницы для политик созданы
- [ ] Ссылки в footer добавлены
- [ ] Модальное окно cookie обновлено
- [ ] Роуты настроены

### Backend:
- [ ] Миграция БД для трансграничного согласия создана
- [ ] Telegram bot consent flow обновлен
- [ ] API endpoints для управления cookie (в будущем)

### Тестирование:
- [ ] Web-сайт протестирован
- [ ] Telegram-бот протестирован
- [ ] Модальное окно cookie протестировано
- [ ] Production проверен

---

## 📞 КОНТАКТЫ ДЛЯ ВОПРОСОВ

- **Юридические вопросы:** [EMAIL юриста]
- **Технические вопросы:** [EMAIL tech lead]
- **Тестирование:** [EMAIL QA engineer]

---

**Статус инструкции:** ✅ Готова к использованию  
**Автор:** AI-ассистент  
**Дата создания:** 20 мая 2026 г.
