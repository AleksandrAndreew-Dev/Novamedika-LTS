# Критические изменения для соответствия ОАЦ - Отчет о реализации

**Дата:** 2026-05-05  
**Статус:** ✅ Реализовано (требует тестирования)

---

## 📋 Выполненные задачи

### 1. ✅ Включение Prometheus метрик в Traefik

**Файлы изменены:**
- [`docker-compose.traefik.prod.yml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\docker-compose.traefik.prod.yml)
- [`docker-compose.monitoring.yml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\docker-compose.monitoring.yml)
- [`config/prometheus.yml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\prometheus.yml)
- [`config/grafana-datasources.yaml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\grafana-datasources.yaml)
- [`dashboards/oac-security-monitoring.json`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\dashboards\oac-security-monitoring.json)

**Что добавлено:**
```yaml
# Traefik command flags
- --metrics.prometheus=true
- --metrics.prometheus.addEntryPointsLabels=true
- --metrics.prometheus.addServicesLabels=true
- --metrics.prometheus.entryPoint=metrics
```

**Prometheus scraper настроен для:**
- Traefik (метрики API gateway)
- PostgreSQL (метрики БД)
- Redis (метрики кэша)

**Grafana dashboard обновлен:**
- Добавлена секция "Traefik Metrics (Prometheus)" с панелями:
  - Запросы по entrypoints (req/s)
  - HTTP ошибки (4xx/5xx)
  - P95 Latency
  - Топ-10 сервисов по запросам

**Соответствие требованиям ОАЦ:**
- ✅ п.1.5 Мониторинг функционирования СВТ (систем вычислительной техники)
- ✅ Возможность создания алертов на аномальный трафик

---

### 2. ✅ Аудит доступа к персональным данным

**Файлы созданы/изменены:**
- [`backend/src/db/models.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\models.py) - модель AuditLog
- [`backend/src/middleware/__init__.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\middleware\__init__.py) - новый пакет middleware
- [`backend/src/middleware/audit_middleware.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\middleware\audit_middleware.py) - middleware автоматического логирования
- [`backend/src/utils/auth.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\utils\auth.py) - shared auth utilities
- [`backend/src/routers/admin.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\admin.py) - admin endpoints
- [`backend/src/main.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\main.py) - подключение middleware и роутера
- [`backend/alembic/versions/6cfa51de7ac5_add_audit_logs_table.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\alembic\versions\6cfa51de7ac5_add_audit_logs_table.py) - миграция БД

#### Модель AuditLog

**Таблица:** `audit_logs`

**Поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| user_id | UUID (nullable) | ID пользователя (если авторизован) |
| user_type | String(20) | Тип: user/pharmacist/admin/system/anonymous |
| action | String(50) | Действие: read/create/update/delete/export |
| resource_type | String(50) | Тип ресурса: user/pharmacist/order/question/consent |
| resource_id | UUID (nullable) | ID затронутого ресурса |
| ip_address | String(45) | IPv4 или IPv6 адрес клиента |
| user_agent | String(500) | User-Agent браузера/клиента |
| request_method | String(10) | HTTP метод: GET/POST/PUT/DELETE |
| endpoint | String(255) | URL endpoint |
| status_code | String(3) | HTTP статус код ответа |
| success | Boolean | Успешность операции |
| details | JSON (nullable) | Дополнительная информация |
| created_at | DateTime | Временная метка события |

**Индексы:**
- `idx_audit_user_id` - поиск по пользователю
- `idx_audit_action` - фильтрация по типу действия
- `idx_audit_resource` - поиск по типу ресурса и ID
- `idx_audit_created_at` - временные запросы

#### Middleware автоматического логирования

**Класс:** `AuditLoggingMiddleware`

**Автоматически логирует запросы к:**
- `/api/users/*` - данные пользователей
- `/api/pharmacist/*` - данные фармацевтов
- `/api/orders/*` - данные заказов
- `/api/questions/*` - вопросы и ответы
- `/api/privacy/*` - согласия на обработку ПД

**Логика работы:**
1. Перехватывает каждый HTTP запрос
2. Проверяет, относится ли endpoint к audited
3. Извлекает контекст (user_id, IP, user-agent, method)
4. Определяет тип действия из HTTP метода (GET→read, POST→create, etc.)
5. Выполняет запрос через call_next()
6. После выполнения записывает событие в audit_logs таблицу
7. При ошибке всё равно логирует событие с success=False

**Обработка ошибок:**
- Ошибки логирования НЕ прерывают основной поток запроса
- Все ошибки middleware логируются в application log
- Graceful degradation при недоступности БД

#### Admin Endpoints

**Endpoint 1:** `GET /api/admin/audit-logs`

**Назначение:** Получение логов аудита с пагинацией и фильтрацией

**Параметры запроса:**
- `page` (int, default=1) - номер страницы
- `page_size` (int, default=50, max=500) - размер страницы
- `user_id` (UUID, optional) - фильтр по пользователю
- `user_type` (string, optional) - фильтр по типу пользователя
- `action` (string, optional) - фильтр по действию
- `resource_type` (string, optional) - фильтр по типу ресурса
- `date_from` (datetime, optional) - начальная дата
- `date_to` (datetime, optional) - конечная дата

**Headers:**
- `X-API-Key: <ADMIN_API_KEY>` (обязательно)

**Ответ:**
```json
{
  "total": 1234,
  "logs": [
    {
      "id": "uuid",
      "user_id": "uuid-or-null",
      "user_type": "pharmacist",
      "action": "read",
      "resource_type": "user",
      "resource_id": "uuid",
      "ip_address": "192.168.1.1",
      "endpoint": "/api/users/uuid",
      "status_code": "200",
      "success": true,
      "created_at": "2026-05-05T13:30:00"
    }
  ],
  "page": 1,
  "page_size": 50
}
```

**Endpoint 2:** `GET /api/admin/audit-logs/stats`

**Назначение:** Статистика по audit logs за период

**Параметры:**
- `days` (int, default=7, max=365) - количество дней

**Ответ:**
```json
{
  "period_days": 7,
  "date_from": "2026-04-28T00:00:00",
  "total_events": 5000,
  "by_action": [
    {"action": "read", "count": 4000},
    {"action": "update", "count": 800},
    {"action": "delete", "count": 200}
  ],
  "by_resource": [
    {"resource_type": "user", "count": 3000},
    {"resource_type": "question", "count": 1500},
    {"resource_type": "order", "count": 500}
  ],
  "top_users": [
    {"user_id": "uuid", "user_type": "pharmacist", "count": 1000},
    ...
  ]
}
```

**Безопасность:**
- Оба endpoint требуют валидный ADMIN_API_KEY
- Ключи читаются из env var `ADMIN_API_KEYS` (поддержка нескольких ключей через запятую)
- При отсутствии ключей endpoint возвращает 500 error

---

## 🔧 Инструкция по деплою

### Шаг 1: Применение миграции БД

```bash
cd backend
python -m alembic upgrade head
```

Или автоматически через entrypoint.sh (уже настроено в docker-compose).

### Шаг 2: Настройка переменных окружения

Добавьте в `.env`:

```bash
# Admin API Keys для доступа к audit logs endpoint
ADMIN_API_KEYS=your-secret-key-1,your-secret-key-2

# (Опционально) Если нужно изменить retention period для audit logs
# AUDIT_LOG_RETENTION_DAYS=395
```

**Важно:** Сгенерируйте безопасные ключи:
```bash
openssl rand -hex 32
```

### Шаг 3: Перезапуск сервисов

```bash
# Monitoring stack (Prometheus + Grafana)
docker-compose -f docker-compose.monitoring.yml up -d

# Backend (применит миграции и включит middleware)
docker-compose -f docker-compose.backend.prod.yml up -d

# Traefik (включит metrics endpoint)
docker-compose -f docker-compose.traefik.prod.yml up -d
```

### Шаг 4: Проверка работоспособности

#### 4.1 Проверка Traefik метрик

```bash
curl http://localhost:8080/metrics | head -20
```

Ожидаемый результат: должны быть метрики вида `traefik_entrypoint_requests_total`, `traefik_service_request_duration_seconds_bucket`.

#### 4.2 Проверка Prometheus

Откройте http://localhost:9090/targets - все targets должны быть в состоянии UP.

#### 4.3 Проверка Grafana dashboard

1. Откройте http://localhost:3000
2. Перейдите в Dashboards → OAC Security Monitoring
3. Проверьте наличие новых панелей "Traefik Metrics"
4. Данные должны отображаться (может потребоваться 1-2 минуты для сбора первых метрик)

#### 4.4 Проверка audit logging

Сделайте тестовый запрос к защищенному endpoint:

```bash
# Пример: получение списка пользователей
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/users/me

# Проверка audit logs
curl -H "X-API-Key: your-secret-key-1" \
     http://localhost:8000/api/admin/audit-logs?page=1&page_size=10
```

Ожидаемый результат: в ответе должен быть хотя бы один audit log entry с действием "read" на ресурс "user".

#### 4.5 Проверка статистики

```bash
curl -H "X-API-Key: your-secret-key-1" \
     http://localhost:8000/api/admin/audit-logs/stats?days=7
```

---

## 📊 Соответствие требованиям ОАЦ

| Требование | Решение | Статус |
|-----------|---------|--------|
| **п.1.1 Регистрация событий ИБ** | Audit middleware логирует все обращения к ПД | ✅ Реализовано |
| **п.1.2 Хранение логов ≥ 1 года** | Loki retention=395 дней + backup.sh архивация | ✅ Реализовано ранее |
| **п.1.3 Централизованный сбор логов** | Loki/Promtail собирают логи со всех контейнеров | ✅ Реализовано ранее |
| **п.1.4 Мониторинг уполномоченными лицами** | Grafana dashboard + daily review procedure | ⚠️ Требуется процедура |
| **п.1.5 Мониторинг функционирования СВТ** | Prometheus метрики Traefik + health checks | ✅ Реализовано сейчас |
| **п.2.1 Защита от вторжений (IDS/IPS)** | Fail2ban + ModSecurity WAF | ✅ Реализовано ранее |
| **п.2.2 Обнаружение аномалий** | Prometheus alerts (требуется настройка) | ⚠️ Частично |

---

## ⚠️ Известные ограничения

1. **Audit logs не имеют автоматической очистки**
   - Таблица будет расти бесконечно
   - Рекомендуется добавить Celery задачу для удаления записей старше 395 дней
   
2. **Нет Grafana алертов**
   - Метрики собираются, но алерты не настроены
   - Требуется создать alert rules в Grafana или Prometheus

3. **Middleware логирует ВСЕ запросы к audited endpoints**
   - Может создавать большую нагрузку на БД при высоком трафике
   - Рекомендуется мониторить размер таблицы audit_logs

4. **Шифрование персональных данных активировано частично**
   - Согласно документации, есть пробелы в использовании encrypted setters
   - Требуется отдельный аудит кода

---

## 🎯 Следующие шаги (рекомендуемые)

### Высокий приоритет:
1. **Настроить Grafana alerts:**
   - Alert на >10 неудачных аутентификаций за 5 минут
   - Alert на ERROR rate > 5%
   - Alert на disk usage > 80%

2. **Добавить автоматическую очистку audit_logs:**
   ```python
   # Celery задача
   @celery.task
   def cleanup_old_audit_logs():
       cutoff_date = datetime.utcnow() - timedelta(days=395)
       db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff_date))
   ```

3. **Протестировать в staging environment перед production**

### Средний приоритет:
4. **Реализовать права субъектов ПД:**
   - `GET /api/users/me/data-export` - экспорт всех ПД
   - `DELETE /api/users/me` - удаление аккаунта
   - `POST /api/consent/withdraw` - отзыв согласия

5. **Активировать шифрование во всех точках создания/обновления пользователей**

### Низкий приоритет:
6. **Добавить Request ID middleware для трассировки запросов**
7. **Интеграция с Grafana Cloud (опционально)**

---

## 📝 Примечания для разработчиков

### Добавление нового endpoint под аудит

Если нужно добавить новый endpoint в список audited:

1. Откройте [`backend/src/middleware/audit_middleware.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\middleware\audit_middleware.py)
2. Добавьте путь в список `AUDITED_ENDPOINTS`:
   ```python
   AUDITED_ENDPOINTS = [
       "/api/users",
       "/api/pharmacist",
       "/api/orders",
       "/api/questions",
       "/api/privacy",
       "/api/new-endpoint",  # <-- добавьте здесь
   ]
   ```
3. Обновите метод `_get_resource_type()` если нужен новый тип ресурса

### Расширение модели AuditLog

Для добавления новых полей:

1. Измените модель в [`backend/src/db/models.py`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\models.py)
2. Создайте новую миграцию:
   ```bash
   cd backend
   python -m alembic revision -m "add_new_field_to_audit_logs"
   ```
3. Примените миграцию:
   ```bash
   python -m alembic upgrade head
   ```

### Тестирование middleware

Unit тест для middleware (пример):

```python
import pytest
from fastapi.testclient import TestClient
from main import app

def test_audit_logging_on_user_endpoint():
    client = TestClient(app)
    
    # Делаем запрос к audited endpoint
    response = client.get("/api/users/me", headers={
        "Authorization": "Bearer valid_jwt_token"
    })
    
    assert response.status_code == 200
    
    # Проверяем, что запись появилась в БД
    # (требуется mock или test database)
```

---

## 🔐 Безопасность

### Рекомендации по ADMIN_API_KEYS

1. **Никогда не коммитьте ключи в git**
2. **Используйте разные ключи для staging и production**
3. **Регулярно ротируйте ключи (каждые 90 дней)**
4. **Логируйте использование ключей (уже реализовано в audit_logs)**

### Защита audit_logs таблицы

1. **Ограничьте доступ к таблице только для admin роли**
2. **Не позволяйте пользователям удалять свои audit logs**
3. **Рассмотрите возможность WORM storage (write-once-read-many) для compliance**

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи backend:
   ```bash
   docker-compose logs -f backend
   ```

2. Проверьте статус миграций:
   ```bash
   cd backend
   python -m alembic current
   ```

3. Проверьте подключение Prometheus к Traefik:
   ```bash
   curl http://traefik:8080/metrics | grep traefik_entrypoint
   ```

4. Проверьте Grafana datasources:
   - Откройте http://localhost:3000/datasources
   - Убедитесь что Prometheus и Loki в состоянии "Connected"

---

**Автор:** AI Assistant (Lingma)  
**Дата создания:** 2026-05-05  
**Версия документа:** 1.0  
**Статус:** Готово к ревью и тестированию
