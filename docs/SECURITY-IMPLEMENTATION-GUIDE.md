# Руководство по внедрению бесплатных решений ИБ для NovaMedika2

**Сервер:** 4 CPU / 8 GB RAM  
**Соответствие:** Законодательство РБ (ОАЦ, Закон №99-З)  

---

## 📋 Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Быстрый старт](#быстрый-старт)
3. [Компоненты системы](#компоненты-системы)
4. [Настройка Grafana Cloud](#настройка-grafana-cloud)
5. [Планирование задач](#планирование-задач)
6. [Мониторинг и алерты](#мониторинг-и-алерты)
7. [Соответствие требованиям ОАЦ](#соответствие-требованиям-оац)

---

## 🏗️ Обзор архитектуры

```
┌─────────────────────────────────────────────────────┐
│              NovaMedika2 Server                      │
│              (4 CPU / 8 GB RAM)                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │   Backend    │  │   Frontend   │                 │
│  │  (FastAPI)   │  │   (Nginx)    │                 │
│  └──────┬───────┘  └──────┬───────┘                 │
│         │                  │                         │
│  ┌──────▼───────┐  ┌──────▼───────┐                 │
│  │  PostgreSQL  │  │    Redis     │                 │
│  └──────┬───────┘  └──────────────┘                 │
│         │                                           │
│  ┌──────▼───────────────────────────┐               │
│  │        Traefik (WAF)             │               │
│  │     ModSecurity + OWASP CRS      │               │
│  └──────┬───────────────────────────┘               │
│         │                                           │
│  ┌──────▼───────────────────────────┐               │
│  │       Fail2ban                   │               │
│  │  (Brute-force, Log clearing)     │               │
│  └──────┬───────────────────────────┘               │
│         │                                           │
│  ┌──────▼───────────────────────────┐               │
│  │  Loki ← Promtail ← Docker Logs   │               │
│  └──────┬───────────────────────────┘               │
│         │                                           │
│  ┌──────▼───────────────────────────┐               │
│  │   Grafana (Local or Cloud)       │               │
│  └──────────────────────────────────┘               │
│                                                      │
└─────────────────────────────────────────────────────┘
         │
         │ Еженедельно (cron)
         ▼
  ┌──────────────┐
  │   OpenVAS    │ (временный контейнер)
  │  (Scanning)  │
  └──────────────┘
```

**Потребление ресурсов:**
- Постоянное: ~5.15 GB RAM, 4.1 CPU
- Пиковое (сканирование): ~7.15 GB RAM, 5.6 CPU

---

## 🚀 Быстрый старт

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y docker.io docker-compose fail2ban ufw

# Включение Fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Настройка firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Шаг 2: Клонирование репозитория

```bash
cd /opt
git clone https://github.com/your-org/novamedika2.git
cd novamedika2
```

### Шаг 3: Настройка переменных окружения

```bash
# Создание .env файла
cp .env.example .env

# Редактирование .env
nano .env
```

**Обязательные переменные:**
```env
# Grafana Cloud (опционально, для production)
GRAFANA_CLOUD_USERNAME=your-username
GRAFANA_CLOUD_API_KEY=your-api-key

# Локальная Grafana
GRAFANA_PASSWORD=SecurePassword123!

# Email для уведомлений Fail2ban
FAIL2BAN_EMAIL=admin@novamedika.com
```

### Шаг 4: Развертывание мониторинга

```bash
# Запуск Loki/Promtail/Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Проверка статуса
docker-compose -f docker-compose.monitoring.yml ps

# Просмотр логов
docker-compose -f docker-compose.monitoring.yml logs -f
```

**Доступ к Grafana:**
- URL: http://your-server-ip:3000
- Login: `admin`
- Password: значение из `GRAFANA_PASSWORD` в `.env`

### Шаг 5: Настройка Fail2ban

```bash
# Копирование конфигурации
sudo cp config/fail2ban-jail.local /etc/fail2ban/jail.local
sudo cp config/fail2ban-filter-log-cleared.conf /etc/fail2ban/filter.d/log-cleared.conf
sudo cp config/fail2ban-filter-docker-backend-auth.conf /etc/fail2ban/filter.d/docker-backend-auth.conf

# Перезапуск Fail2ban
sudo systemctl restart fail2ban

# Проверка статуса
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

### Шаг 6: Импорт дашбордов Grafana

```bash
# Дашборды автоматически загружаются из папки dashboards/
# Или импортировать вручную через Grafana UI:
# 1. Dashboards → Import
# 2. Upload JSON file: dashboards/oac-security-monitoring.json
```

---

## 🔧 Компоненты системы

### 1. Loki/Promtail/Grafana (централизованные логи)

**Назначение:** Сбор, хранение и визуализация логов всех контейнеров

**Конфигурация:**
- [`docker-compose.monitoring.yml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\docker-compose.monitoring.yml) - оркестрация сервисов
- [`config/loki-config.yaml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\loki-config.yaml) - настройки Loki (retention 395 дней)
- [`config/promtail-config.yaml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\promtail-config.yaml) - сбор логов с Docker
- [`dashboards/oac-security-monitoring.json`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\dashboards\oac-security-monitoring.json) - дашборд безопасности

**Ресурсы:** 768 MB RAM, 0.9 CPU

**Требования ОАЦ:**
- ✅ Централизованный сбор логов (п.1.3 Приказа №259)
- ✅ Хранение ≥ 1 года (395 дней)
- ✅ Визуализация для аудиторов

---

### 2. Fail2ban (защита от атак)

**Назначение:** Блокировка IP при подозрительной активности

**Защищаемые сервисы:**
- SSH (3 попытки → бан на 2 часа)
- HTTP Basic Auth (5 попыток → бан на 1 час)
- Backend API (10 попыток → бан на 1 час)
- PostgreSQL (5 попыток → бан на 2 часа)
- **Очистка логов** (1 попытка → бан на 24 часа) ⚠️ КРИТИЧНО

**Конфигурация:**
- [`config/fail2ban-jail.local`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\fail2ban-jail.local) - правила блокировки
- [`config/fail2ban-filter-log-cleared.conf`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\fail2ban-filter-log-cleared.conf) - обнаружение очистки логов
- [`config/fail2ban-filter-docker-backend-auth.conf`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\fail2ban-filter-docker-backend-auth.conf) - защита API

**Ресурсы:** 50 MB RAM, 0.1 CPU

**Требования ОАЦ:**
- ✅ Обнаружение подозрительной активности
- ✅ Автоматическая блокировка атакующих
- ✅ Регистрация попыток затирания следов

---

### 3. ModSecurity WAF (web application firewall)

**Назначение:** Защита веб-приложений от OWASP Top 10 уязвимостей

**Интеграция:** Модуль Traefik/Nginx

**Функции:**
- SQL Injection protection
- Cross-Site Scripting (XSS) protection
- Remote File Inclusion (RFI) protection
- Rate limiting

**Ресурсы:** 200 MB RAM, 0.2 CPU

**Требования ОАЦ:**
- ⚠️ Частично закрывает требование 7.13 (IDS/IPS)
- ✅ Web Application Firewall

---

### 4. OpenVAS (сканер уязвимостей)

**Назначение:** Регулярное сканирование инфраструктуры на CVE

**Режим работы:** По расписанию (раз в неделю, суббота 02:00)

**Скрипты:**
- [`scripts/manage-openvas.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\manage-openvas.sh) - управление ресурсами
- [`scripts/annual-security-review.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\annual-security-review.sh) - ежегодный отчет

**Ресурсы:** Только во время сканирования (~3 часа/неделю)
- Пик: 3 GB RAM, 2 CPU
- Среднее: 200 MB RAM (архивы отчетов)

**Требования ОАЦ:**
- ✅ Регулярное выявление уязвимостей (требование 7.17 ТЗ)
- ✅ Документирование для аудиторов (PDF отчеты)

---

### 5. ClamAV (антивирус)

**Назначение:** Проверка загружаемых файлов на вредоносное ПО

**Режим работы:** По требованию (при загрузке файлов пользователями)

**Интеграция с backend:**
```python
# backend/src/utils/antivirus.py
import clamd

def scan_file(file_path: str) -> bool:
    cd = clamd.ClamdNetworkSocket()
    result = cd.instream(open(file_path, 'rb'))
    return result['stream'][0] == 'OK'
```

**Ресурсы:** 1 GB RAM (только при сканировании)

**Требования ОАЦ:**
- ✅ Защита от вредоносных программ (требование 7.10 ТЗ)

---

## ☁️ Настройка Grafana Cloud


### Шаг 1: Регистрация

1. Перейдите на [https://grafana.com/signup](https://grafana.com/signup)
2. Создайте бесплатный аккаунт
3. Перейдите в раздел "Stacks" → "Logs"

### Шаг 2: Получение учетных данных

1. В разделе "Details" скопируйте:
   - **URL**: `https://logs-prod-us-central1.grafana.net`
   - **Username**: ваш username
   - **API Key**: создайте новый ключ с правами "Metrics Publisher"

### Шаг 3: Настройка Promtail

Отредактируйте [`config/promtail-config.yaml`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\config\promtail-config.yaml):

```yaml
clients:
  # Закомментируйте локальный Loki
  # - url: http://loki:3100/loki/api/v1/push
  
  # Раскомментируйте Grafana Cloud
  - url: https://logs-prod-us-central1.grafana.net/loki/api/v1/push
    basic_auth:
      username: YOUR_USERNAME
      password: YOUR_API_KEY
```

### Шаг 4: Обновление .env

```env
GRAFANA_CLOUD_USERNAME=your-username
GRAFANA_CLOUD_API_KEY=your-api-key
```

### Шаг 5: Перезапуск

```bash
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d
```

**Преимущества Grafana Cloud:**
- ✅ Не потребляет ресурсы вашего сервера
- ✅ 50 GB логов/месяц бесплатно
- ✅ Доступ из любой точки мира
- ✅ Автоматическое резервное копирование

---

## ⏰ Планирование задач

### Cron задачи

```bash
# Редактирование crontab
sudo crontab -e
```

**Добавьте следующие задачи:**

```cron
# Ежедневное обновление сигнатур ClamAV
0 3 * * * /usr/bin/freshclam --quiet

# Еженедельное сканирование уязвимостей (суббота 02:00)
0 2 * * 6 /opt/novamedika2/scripts/manage-openvas.sh start-scanning
0 5 * * 6 /opt/novamedika2/scripts/manage-openvas.sh stop-scanning

# Ежегодный анализ эффективности СЗИ (1 января 00:00)
0 0 1 1 * /opt/novamedika2/scripts/annual-security-review.sh

# Ежемесячная очистка старых логов (> 395 дней)
0 0 1 * * find /var/lib/docker/volumes/loki-data -type f -mtime +395 -delete
```

---

## 📊 Мониторинг и алерты

### Grafana дашборды

**Основной дашборд:** OAC Compliance - Security Monitoring

**Панели:**
1. **Ошибки по контейнерам (ERROR)** - график ошибок в реальном времени
2. **Неудачные аутентификации (за час)** - gauge метрика
3. **Критические события ИБ** - лог ERROR/CRITICAL/ALERT
4. **События Fail2ban** - лог блокировок IP
5. **Распределение логов по уровням** - INFO/WARN/ERROR/DEBUG

**Настройка алертов:**

1. Перейдите в Grafana → Alerting → New alert rule
2. Пример алерта на критические ошибки:

```
Query: sum(count_over_time({job="docker-containers"} |= "CRITICAL" [5m]))
Condition: IS ABOVE 0
For: 5m
Labels: severity=critical
Annotations: summary="Критическая ошибка в системе"
```

### Уведомления Fail2ban

Fail2ban автоматически отправляет email при блокировке IP:

```ini
# В config/fail2ban-jail.local
action = %(action_mwl)s
         sendmail-whois[name=Fail2Ban, dest=admin@novamedika.com]
```

**Настройка SMTP:**

```bash
# Установка mailutils
sudo apt install -y mailutils

# Настройка Postfix
sudo dpkg-reconfigure postfix
```

---

## ✅ Соответствие требованиям ОАЦ

### Таблица соответствия

| Требование | Решение | Статус |
|------------|---------|--------|
| **1.3** Централизованный сбор логов ≥ 1 года | Loki (395 дней retention) | ✅ Выполнено |
| **7.10** Защита от вредоносных программ | ClamAV | ✅ Выполнено |
| **7.13** IDS/IPS система | ModSecurity WAF + Fail2ban | ⚠️ Частично |
| **7.17** Регулярное сканирование уязвимостей | OpenVAS (еженедельно) | ✅ Выполнено |
| **Ежегодный анализ эффективности СЗИ** | annual-security-review.sh | ✅ Выполнено |
| **Приказы о назначении ответственных** | PRIKAZY-OTVETSTVENNYE-IB.md | ✅ Выполнено |
| **Уведомление НЦЗПД об утечках (3 дня)** | Регламент в 04-privacy-policy.md | ✅ Выполнено |

### Документы для аттестации

1. [`oac/docs/PRIKAZY-OTVETSTVENNYE-IB.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\PRIKAZY-OTVETSTVENNYE-IB.md) - приказы о назначении ответственных
2. [`oac/docs/04-privacy-policy.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\04-privacy-policy.md) - политика обработки ПД
3. [`oac/docs/05-infosec-policy.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\05-infosec-policy.md) - политика ИБ
4. [`oac/docs/06-tech-spec.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\06-tech-spec.md) - техническое задание на СЗИ
5. [`oac/docs/07-ib-monitoring-reglament.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\07-ib-monitoring-reglament.md) - регламент мониторинга ИБ
6. [`oac/docs/12-ids-ips-reglament.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\12-ids-ips-reglament.md) - регламент IDS/IPS

---

## 💰 Экономический эффект

| Компонент | Коммерческий аналог | Стоимость/год | Open Source альтернатива | Экономия |
|-----------|---------------------|---------------|--------------------------|----------|


---

## 🔍 Troubleshooting

### Проблема: Loki не запускается

```bash
# Проверка логов
docker logs loki

# Проверка прав доступа
sudo chown -R 10001:10001 /var/lib/docker/volumes/loki-data

# Перезапуск
docker-compose -f docker-compose.monitoring.yml restart loki
```

### Проблема: Fail2ban не блокирует IP

```bash
# Проверка статуса
sudo fail2ban-client status

# Проверка конкретного jail
sudo fail2ban-client status sshd

# Просмотр логов
sudo tail -f /var/log/fail2ban.log

# Тестовый бан
sudo fail2ban-client set sshd banip 192.168.1.100
```

### Проблема: OpenVAS не запускается

```bash
# Проверка доступной памяти
free -h

# Остановка ненужных сервисов
docker stop grafana-local loki promtail

# Запуск OpenVAS
./scripts/manage-openvas.sh start-scanning
```

### Проблема: Grafana недоступна

```bash
# Проверка статуса
docker ps | grep grafana

# Проверка логов
docker logs grafana-local

# Сброс пароля админа
docker exec -it grafana-local grafana-cli admin reset-admin-password newpassword
```

---

## 📞 Поддержка

**Внутренние контакты:**
- Ответственный за ИБ: [ФИО], [email], [телефон]
- Администратор безопасности: [ФИО], [email], [телефон]

**Внешние ресурсы:**
- [Документация Loki](https://grafana.com/docs/loki/latest/)
- [Документация Fail2ban](https://www.fail2ban.org/wiki/index.php/Main_Page)
- [Документация OpenVAS](https://greenbone.github.io/docs/)
- [Grafana Cloud Support](https://grafana.com/support/)

---

## 📝 История изменений

| Дата | Версия | Изменения | Автор |
|------|--------|-----------|-------|
| 05.05.2026 | 1.0 | Первоначальная версия | AI Assistant |

---

**Готово к использованию — требуется настройка под конкретную инфраструктуру**
