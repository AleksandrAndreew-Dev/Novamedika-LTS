# AI Agent Quick Start - Novamedika2

## 🚀 Быстрый старт для AI-агента

### Перед началом работы:

1. **Прочитай эти файлы (в порядке важности):**
   ```
   1. .ai-rules.md                    ← ПРАВИЛА ПОВЕДЕНИЯ (обязательно!)
   2. .clinerules/rules.md            ← Основная справка по проекту
   3. .cursorrules                    ← Конфигурация IDE
   4. skills/README.md                ← Описание навыков
   5. AI-OPTIMIZATION-GUIDE.md        ← Полное руководство
   ```

2. **Запомни критические правила:**
   - ❌ НИКОГДА не говори "✅ FULLY IMPLEMENTED", "Works perfectly"
   - ✅ ВСЕГДА используй "Код изменен, требуется проверка"
   - 📋 ВСЕГДА используй структуру отчета с разделами "Что сделано", "Что НЕ проверено", "Следующие шаги"

---

## 🎯 Когда какую задачу выполнять

### Задача: Добавить новый API endpoint

**Используй skill:** `skills/oac-compliance-checker.md`

**Быстрый чеклист:**
```bash
# 1. Проверь аутентификацию
grep -r "get_current_active_user" backend/src/routers/

# 2. Проверь шифрование
cat backend/src/db/models.py | grep -i "personal\|email\|phone"

# 3. Проверь audit logs
grep -r "AuditLog" backend/src/routers/

# 4. Запусти проверку OAC
py oac/check_normative_docs.py
```

---

### Задача: Деплой изменений

**Используй skill:** `skills/deployment-diagnostics.md`

**Быстрый чеклист:**
```bash
# 1. Pre-deployment check
bash agent/diagnostics.sh status

# 2. Commit и push
git add .
git commit -m "description"
git push  # CI/CD автоматически задеплоит

# 3. Post-deployment verification
bash agent/diagnostics.sh all
cat agent/server-logs/*_errors-only.txt | tail -20
```

---

### Задача: Бот не работает

**Используй skill:** `skills/telegram-bot-debugger.md`

**Быстрая диагностика:**
```bash
# 1. Полная диагностика бота
bash agent/diagnostics.sh bot

# 2. Проверь логи backend
bash agent/diagnostics.sh backend | grep -i "bot\|aiogram"

# 3. Проверь webhook
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq

# 4. Перезапусти backend
npm run prod:restart-backend
```

---

## 🔍 Быстрый поиск кода

### Найти конкретную функцию/класс:
```python
# Используй search_symbol
search_symbol(query="AuthService.authenticate")
search_symbol(query="UserModel Prescription Order")
```

### Найти код по концепции:
```python
# Используй search_codebase
search_codebase(query="JWT token generation authentication")
search_codebase(query="encryption personal data fields")
```

### Найти текстовый паттерн:
```python
# Используй grep_code
grep_code(include_pattern="*.py", regex="@router\.(get|post|put|delete)")
grep_code(include_pattern="backend/src/**/*.py", regex="class.*\(Base\)")
```

### Прочитать файл с зависимостями:
```python
# Всегда используй view_dependencies=true при модификации
read_file(file_path="backend/src/auth/service.py", view_dependencies=true)
```

---

## 💡 Экономия токенов - лучшие практики

### ❌ ПЛОХО (тратит много токенов):
```python
# Чтение всего файла
read_file("backend/src/main.py", read_entire_file=true)

# Загрузка всей документации
read_file("oac/docs/01-act-class-3in.md", read_entire_file=true)
read_file("oac/docs/02-structural-schema.md", read_entire_file=true)

# Ручной сбор логов
docker logs backend > log.txt
docker logs frontend >> log.txt
```

### ✅ ХОРОШО (экономит токены):
```python
# Чтение конкретной секции
read_file("backend/src/main.py", start_line=50, end_line=100)

# Поиск по ключевым словам
grep_code(include_pattern="oac/docs/*.md", regex="encryption.*requirements")

# Использование diagnostics скрипта
run_in_terminal(command="bash agent/diagnostics.sh all")
```

---

## 📋 Обязательная структура ответа

Всегда используй этот шаблон:

```markdown
## Статус выполнения

**Что сделано:**
- Изменен файл X, строки Y-Z
- Добавлена функция ABC
- Обновлена конфигурация DEF

**Что НЕ проверено:**
- Не тестировалось в production среде
- Требуется проверка пользователем
- Нужно подтвердить работу функционала

**Следующие шаги:**
1. Деплой изменений на сервер
2. Тестирование в реальной среде
3. Подтверждение от пользователя о работоспособности
```

---

## 🚨 Экстренные ситуации

### Сервер упал / ничего не работает:
```bash
# 1. Проверь статус всех контейнеров
bash agent/diagnostics.sh status

# 2. Посмотри ошибки
bash agent/diagnostics.sh logs
cat agent/server-logs/*_errors-only.txt | head -50

# 3. Перезапусти всё
npm run prod:restart

# 4. Если не помогло - полный рестарт
npm run prod:down
npm run prod:up
```

### Бот не отвечает:
```bash
# Быстрая диагностика
bash agent/diagnostics.sh bot

# Перезапуск backend
npm run prod:restart-backend

# Проверка webhook
bash agent/diagnostics.sh bot | grep -i "webhook"
```

### Frontend белый экран:
```bash
# Проверь frontend
bash agent/diagnostics.sh frontend

# Проверь API connectivity
bash agent/diagnostics.sh frontend | grep -i "api"

# Перезапуск frontend
npm run prod:restart-frontend
```

---

## 📁 Ключевые файлы проекта

### Backend:
- `backend/src/main.py` - Точка входа FastAPI
- `backend/src/auth/` - Аутентификация и JWT
- `backend/src/bot/` - Telegram бот
- `backend/src/routers/` - API endpoints
- `backend/src/tasks/` - Celery задачи
- `backend/src/db/models*.py` - Модели базы данных

### Frontend:
- `frontend/src/App.jsx` - Главный компонент
- `frontend/src/pages/` - Страницы
- `frontend/src/components/` - Компоненты
- `frontend/src/api/` - API клиенты

### Конфигурация:
- `docker-compose.traefik.prod.yml` - Production
- `.env.example` - Переменные окружения
- `traefic/traefik.yml` - Traefik настройки

### Документация:
- `.ai-rules.md` - **ПРАВИЛА AI-АГЕНТА**
- `oac/docs/` - OAC compliance документы
- `skills/` - Шаблоны навыков

---

## 🛠️ Основные команды

### Диагностика:
```bash
bash agent/diagnostics.sh all       # Всё
bash agent/diagnostics.sh status    # Статус контейнеров
bash agent/diagnostics.sh logs      # Логи с фильтрацией ошибок
bash agent/diagnostics.sh backend   # Backend логи
bash agent/diagnostics.sh frontend  # Frontend + API тесты
bash agent/diagnostics.sh bot       # Telegram бот
bash agent/diagnostics.sh db        # База данных + Redis
```

### Управление средой:
```bash
npm run prod:up              # Запустить
npm run prod:down            # Остановить
npm run prod:restart         # Перезапустить всё
npm run prod:restart-backend # Только backend
npm run prod:restart-frontend# Только frontend
npm run prod:logs            # Логи
npm run prod:ps              # Статус
```

### Безопасность:
```bash
py oac/check_normative_docs.py    # OAC compliance
sh scripts/run-zap-scan.sh        # OWASP ZAP scan
```

---

## ⚠️ OAC Class 3-in Compliance - Критично!

Все изменения должны учитывать:

1. **Шифрование** персональных данных
   - См. `oac/docs/10-encryption-policy.md`
   
2. **Трансграничная передача** (Telegram = трансграничная!)
   - См. `oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md`
   
3. **Audit logs** всех действий
   - Логин, доступ к данным, изменение, удаление
   
4. **Согласие пользователя** на обработку данных
   - Чекбоксы в frontend
   - Явное согласие для трансграничной передачи
   
5. **Права пользователей** на данные
   - Доступ, изменение, удаление, экспорт

---

## 🎓 Checklist перед ответом

Перед каждым ответом проверь:

- [ ] Избегал ли я абсолютных утверждений ("работает", "готово")?
- [ ] Использовал ли правильную структуру отчета?
- [ ] Указал ли что НЕ проверено?
- [ ] Предложил ли конкретные шаги проверки?
- [ ] Учел ли OAC compliance требования?
- [ ] Использовал ли оптимальные инструменты поиска?
- [ ] Не загрузил ли слишком много контекста?

Если хотя бы один пункт ❌ - исправь перед отправкой!

---

## 📞 Где искать помощь

### Документация:
- `AI-OPTIMIZATION-GUIDE.md` - Полное руководство по оптимизации
- `.clinerules/rules.md` - Справка по проекту
- `skills/README.md` - Описание навыков

### Skills (шаблоны действий):
- `skills/oac-compliance-checker.md` - Проверка compliance
- `skills/deployment-diagnostics.md` - Деплой и диагностика
- `skills/telegram-bot-debugger.md` - Отладка бота

### Инструменты:
- `agent/diagnostics.sh` - Главная диагностика
- `oac/check_normative_docs.py` - Проверка OAC
- `scripts/` - Различные утилиты

---

**Версия:** 1.0  
**Создано:** 2026-05-28  
**Для:** Всех AI-агентов работающих с Novamedika2  
**Обязательно к прочтению:** ДА
