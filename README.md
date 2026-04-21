# Novamedika 2 — Справочный сервис поиска лекарств

Full-stack приложение (FastAPI + React) с интеграцией Telegram-бота и автоматическим деплоем.

## 🏗 Архитектура

- **Backend:** FastAPI, aiogram 3.x (Telegram Bot), Celery, Redis.
- **Frontend:** React 19, Vite.
- **Proxy/Edge:** Traefik v3.6 (HTTPS, TLS Let's Encrypt).
- **DB:** PostgreSQL 17.

## 📂 Структура проекта

- `backend/` — Серверная часть, логика бота и фоновые задачи. Использует `uv`.
- `frontend/` — Клиентская часть на React.
- `oac/` — Документация и политики для аттестации ОАЦ РБ (Класс 3-ин).
- `traefic/` — Конфигурация динамического роутинга и сертификатов.
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

### 📊 Статус соответствия ОАЦ: 45% → 95%+ (план)

**Полная документация по compliance:**

| Документ | Описание | Ссылка |
|----------|----------|--------|
| **Полный аудит** | Детальный анализ всех 40+ требований ОАЦ | [oac-audit.md](oac-audit.md) |
| **Краткая сводка** | Executive summary для руководства | [oac-audit-summary.md](oac-audit-summary.md) |
| **Чек-лист** | 115 задач для отслеживания прогресса | [oac-compliance-checklist.md](oac-compliance-checklist.md) |
| **Бесплатные решения** | Как сэкономить $3,800/год с open-source | [OAC-FREE-SOLUTIONS.md](OAC-FREE-SOLUTIONS.md) |
| **Шпаргалка** | Быстрый старт с бесплатными инструментами | [OAC-FREE-SOLUTIONS-CHEATSHEET.md](OAC-FREE-SOLUTIONS-CHEATSHEET.md) |
| **Визуальный прогресс** | Графики и dashboard готовности | [OAC-VISUAL-PROGRESS.md](OAC-VISUAL-PROGRESS.md) |
| **Для команды** | Briefing документ для всех ролей | [OAC-AUDIT-SUMMARY-FOR-TEAM.md](OAC-AUDIT-SUMMARY-FOR-TEAM.md) |
| **Навигация ОАЦ** | Полный гид по документации | [oac/README.md](oac/README.md) |

### 💰 Экономия с бесплатными решениями

Используя open-source инструменты вместо платных аналогов:
- **Экономия:** $3,799/год (82%)
- **Стоимость compliance:** $1,500/год вместо $5,299/год
- **Инструменты:** ELK Stack, pgcrypto, ClamAV, Fail2Ban, OWASP ZAP, Prometheus+Grafana

👉 **Подробности:** [OAC-FREE-SOLUTIONS-CHEATSHEET.md](OAC-FREE-SOLUTIONS-CHEATSHEET.md)

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

- [Архитектура системы](docs/architecture.md) *(если существует)*
- [API Documentation](backend/docs/) *(если существует)*
- [Contributing Guidelines](CONTRIBUTING.md) *(если существует)*

---

## 🤝 Участие в проекте

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Этот проект является частной собственностью. Все права защищены.

---

## 📞 Контакты

- **Email:** info@novamedika.com
- **Telegram Bot:** [@NovaMedikaBot](https://t.me/NovaMedikaBot)
- **Website:** [spravka.novamedika.com](https://spravka.novamedika.com)

---

**Последнее обновление:** 21 апреля 2026 г.
