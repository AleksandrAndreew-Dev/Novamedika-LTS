# Novamedika 2 — Справочный сервис поиска лекарств

Full-stack приложение (FastAPI + React) с интеграцией Telegram-бота и автоматическим деплоем.

## 🏗 Архитектура

- **Backend:** FastAPI, aiogram 3.x (Telegram Bot), Celery, Redis.
- **Frontend:** React 19, Vite.
- **Proxy/Edge:** Traefik v3.6 (HTTPS, TLS Let's Encrypt).
- **DB:** PostgreSQL 17.

## 📂 Структура проекта

> **Обновлено 8 июня 2026 г.** — проведена реорганизация документации в соответствии с `oac/DOCUMENTS-ORGANIZATION-RULES.md`. Подробности в [`oac/CHANGELOG.md`](oac/CHANGELOG.md) и [`oac/dop/DOCUMENTS-ORGANIZATION-PLAN-2026-06-08.md`](oac/dop/DOCUMENTS-ORGANIZATION-PLAN-2026-06-08.md).

- `backend/` — Серверная часть, логика бота и фоновые задачи. Использует `uv`.
- `frontend/` — Клиентская часть на React.
- `oac/` — **Документация и политики для аттестации ОАЦ РБ (Класс 3-ин)** — [карта документов](oac/README.md)
  - `oac/docs/` — 15 документов compliance (01-act-class-3in.md ... 15-cookie-policy.md)
  - `oac/audits/` — Отчёты об аудитах и проверках
  - `oac/architecture/` — Архитектурные решения (ADR)
  - `oac/guides/` — Пошаговые руководства и инструкции
  - `oac/planning/` — Планы, чек-листы, дорожные карты
  - `oac/requirements/` — Детализированные требования
  - `oac/dop/` — Дополнительные документы (чеклисты, приказы, шаблоны)
  - `oac/dop/drafts/` — Рабочие черновики
  - `oac/telegram/` — Специфика Telegram-бота (трансграничная передача)
  - `oac/DOCUMENTS-ORGANIZATION-RULES.md` — Правила организации документов
  - `oac/QUICK-REFERENCE.md` — Шпаргалка для быстрого доступа
  - `oac/CHANGELOG.md` — Журнал изменений
- `origin-docs/` — **Оригинальные тексты** законов, указов, приказов и разъяснений НЦЗПД
  - `66.md`, `99-3n.md`, `422.md`, `449.md`, `455-3.md` — основные нормативные акты
  - `NORMATIVNYE-DOKUMENTY-REGISTER.md` — реестр документов с анализом
  - `nczpd-*.md` — разъяснения НЦЗПД
  - `pd-policy-clinic-template.md` — шаблон политики для медучреждений
- `docs/` — **Общая проектная документация** (НЕ про ОАЦ): AI-гайды, конфигурация, безопасность
- `skills/` — Скиллы для AI-агентов
- `scripts/` — Скрипты автоматизации
- `config/` — Конфигурации мониторинга (Prometheus, Grafana, Loki, Promtail, Fail2ban)
- `dashboards/` — Дашборды Grafana
- `traefic/` — Конфигурация Traefik
- `uploaded_csv/` — Хранилище данных для синхронизации аптек.

## 🛠 Разработка и Workflow

Проект разработан по принципу: **Локальная разработка -> Git Push -> CI/CD -> Server**.

### Локальный запуск (Development)

```bash
# Сборка и запуск в dev-режиме
docker-compose -f docker-compose.traefik.dev.yml up --build
```

- Frontend: `http://localhost`
- Backend API: `http://api.localhost`
- Traefik Dashboard: `http://localhost:8080`

### Продакшн (через scripts в корневом package.json)

```bash
npm run prod:up      # Запуск продакшн окружения
npm run prod:logs    # Просмотр логов
npm run prod:restart # Перезапуск всех контейнеров
```

## 🔐 Безопасность и соответствие ОАЦ

Проект соответствует требованиям **Класса 3-ин** ОАЦ Республики Беларусь:

- ✅ HTTPS/TLS шифрование (Traefik + Let's Encrypt)
- ✅ JWT аутентификация с ролевой моделью (user/pharmacist/admin)
- ✅ Логирование событий безопасности
- ✅ Разделение сетей контейнеров (Docker networks)
- ✅ Политика обработки персональных данных (Закон №99-З)
- ✅ API для реализации прав субъектов ПД (доступ, изменение, удаление, экспорт)

### 📊 Статус соответствия ОАЦ

**Полная документация по compliance:**

| Документ                   | Описание                       | Ссылка                                                                                           |
| -------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------ |
| **Нормативная база**       | Законы, указы, приказы ОАЦ     | [`origin-docs/`](origin-docs/)                                                                   |
| **Реестр документов**      | Полный реестр с анализом       | [`origin-docs/NORMATIVNYE-DOKUMENTY-REGISTER.md`](origin-docs/NORMATIVNYE-DOKUMENTY-REGISTER.md) |
| **Документы compliance**   | 15 документов для аттестации   | [`oac/docs/`](oac/docs/)                                                                         |
| **Руководства**            | Инструкции для персонала       | [`oac/guides/`](oac/guides/)                                                                     |
| **Архитектура**            | ADR и тех. решения             | [`oac/architecture/`](oac/architecture/)                                                         |
| **Аудиты**                 | Отчёты о проверках             | [`oac/audits/`](oac/audits/)                                                                     |
| **Telegram-специфика**     | Трансграничная передача        | [`oac/telegram/`](oac/telegram/)                                                                 |
| **Правила организации**    | Как работать с документами ОАЦ | [`oac/DOCUMENTS-ORGANIZATION-RULES.md`](oac/DOCUMENTS-ORGANIZATION-RULES.md)                     |
| **Шпаргалка**              | Быстрый справочник             | [`oac/QUICK-REFERENCE.md`](oac/QUICK-REFERENCE.md)                                               |
| **Журнал изменений**       | История обновлений             | [`oac/CHANGELOG.md`](oac/CHANGELOG.md)                                                           |
| **Проектная документация** | AI-гайды, конфигурация         | [`docs/`](docs/)                                                                                 |

### 💡 Ключевые документы

- **Политика конфиденциальности:** [`oac/docs/04-privacy-policy.md`](oac/docs/04-privacy-policy.md)
- **Cookie политика:** [`oac/docs/15-cookie-policy.md`](oac/docs/15-cookie-policy.md)
- **Техническое задание на СЗИ:** [`oac/docs/06-tech-spec.md`](oac/docs/06-tech-spec.md)
- **Политика шифрования:** [`oac/docs/10-encryption-policy.md`](oac/docs/10-encryption-policy.md)
- **Руководство по шифрованию:** [`oac/guides/ENCRYPTION-IMPLEMENTATION-GUIDE.md`](oac/guides/ENCRYPTION-IMPLEMENTATION-GUIDE.md)
- **Аудит ПД (актуальный):** [`oac/audits/audit-personal-data-2026-06-08.md`](oac/audits/audit-personal-data-2026-06-08.md)
- **Анализ трансграничной передачи Telegram:** [`oac/requirements/transboundary-transfer-telegram-analysis-2026-05-20.md`](oac/requirements/transboundary-transfer-telegram-analysis-2026-05-20.md)

### 🛠️ Инструменты проверки

```bash
# Проверить наличие всех нормативных документов
py oac/check_normative_docs.py
```

### 🗓️ Дорожная карта аттестации (9 недель)

```
Недели 1-2: Документация и планирование
Недели 3-4: Критическая инфраструктура (логи, шифрование, backup)
Недели 5-6: Дополнительные меры (антивирус, IDS/IPS)
Недели 7-8: Тестирование уязвимостей (OWASP ZAP, pentest)
Неделя 9:   Аттестация и подача сведений в ОАЦ
```

---

## 📚 Дополнительная документация

- [Проектная документация](docs/README.md) — AI-гайды, конфигурация
- [Скиллы для AI-агентов](skills/README.md) — специализированные инструкции
- [Скрипты автоматизации](scripts/README.md) — backup, ZAP, мониторинг
- [Архитектурные решения](oac/architecture/README.md) — ADR

---

## 🤝 Участие в проекте

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📞 Контакты

- **Email:** aleksandrandrph@gmail.com
- **Telegram Bot:** [@NovaMedikaBot](https://t.me/NovaMedikaBot)
- **Website:** [spravka.novamedika.com](https://spravka.novamedika.com)

---

**Последнее обновление:** 8 июня 2026 г. (реорганизация документации)
