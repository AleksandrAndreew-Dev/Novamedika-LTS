# 🛡️ NovaMedika2 — Документация ОАЦ compliance

**Навигатор по документам проекта.**
Для быстрого старта используй [QUICK-REFERENCE.md](QUICK-REFERENCE.md).

---

## 🗺️ Карта документов

```
oac/                            ← Корень всей compliance-документации
├── README.md                   ← Ты здесь (карта документов)
├── QUICK-REFERENCE.md          ← Шпаргалка "куда что сохранять"
├── CHANGELOG.md                ← Журнал всех изменений
├── DOCUMENTS-ORGANIZATION-RULES.md  ← Правила организации документов
│
├── docs/                       ← Основные документы compliance (01-15)
├── architecture/               ← Архитектурные решения (ADR)
├── audits/                     ← Отчёты об аудитах и проверках
├── guides/                     ← Инструкции и руководства
├── planning/                   ← Планы и дорожные карты
├── requirements/               ← Детализированные требования
├── telegram/                   ← Специфика Telegram-бота в контексте ОАЦ
├── dop/                        ← Дополнительные материалы
│   └── drafts/                 ← Черновики (не финальные)
│
└── oac.md                      ← Полный текст Приказа ОАЦ №66
```

---

## 📂 Что где лежит

### 1️⃣ `oac/docs/` — Основные документы compliance (01-15)

**Ядро аттестации.** Нумерованные документы, которые непосредственно проверяет ОАЦ.

| №  | Файл | О чём |
|----|------|-------|
| 01 | `01-act-class-3in.md` | Акт отнесения к классу защиты 3-ин |
| 02 | `02-structural-schema.md` | Структурная схема ИС |
| 03 | `03-logical-schema.md` | Логическая схема ИС |
| 04 | `04-privacy-policy.md` | Политика обработки персональных данных |
| 05 | `05-infosec-policy.md` | Политика информационной безопасности |
| 06 | `06-tech-spec.md` | Техническое задание на СЗИ |
| 07 | `07-ib-monitoring-reglament.md` | Регламент мониторинга ИБ |
| 08 | `08-backup-reglament.md` | Регламент резервного копирования |
| 09 | `09-data-retention-reglament.md` | Регламент хранения данных |
| 10 | `10-encryption-policy.md` | Политика шифрования |
| 11 | `11-antivirus-reglament.md` | Регламент антивирусной защиты |
| 12 | `12-ids-ips-reglament.md` | Регламент IDS/IPS |
| 13 | `13-vuln-scan-reglament.md` | Регламент сканирования уязвимостей |
| 14 | `14-personal-data-processing-architecture.md` | Архитектура обработки ПД |
| 15 | `15-cookie-policy.md` | Политика использования cookie |

---

### 2️⃣ `oac/architecture/` — Архитектурные решения (ADR)

Документы, описывающие архитектурные решения, влияющие на ОАЦ-compliance.

| Файл | Описание |
|------|----------|
| `PRESCRIPTION-PHOTO-ARCHITECTURE-SOLUTION.md` | Архитектурное решение по загрузке фото рецептов |
| `PRESCRIPTION-PHOTO-SOLUTION-SUMMARY.md` | Сводка решения по фото рецептов |
| `SIMPLIFIED-PRESCRIPTION-ARCHITECTURE.md` | Упрощённая архитектура для рецептов |
| `WEB-APP-CHAT-ARCHITECTURE.md` | Архитектура WebApp чата |

---

### 3️⃣ `oac/audits/` — Отчёты об аудитах

Результаты внутренних и внешних проверок.

| Файл | Описание |
|------|----------|
| `audit-personal-data-2026-06-08.md` | Аудит обработки ПД (июнь 2026) |
| `audit-policy-2026-05-20.md` | Аудит политик (май 2026) |
| `README.md` | Описание папки |

---

### 4️⃣ `oac/guides/` — Инструкции и руководства

Пошаговые инструкции для команды. Сгруппированы по темам.

**🛡️ Безопасность:**
- `QUICK-START-SECURITY.md` — Быстрый старт настройки безопасности
- `OPENSOURCE-SECURITY-SOLUTIONS.md` — Open Source решения для compliance
- `ATTESTATION-OAC-GUIDE.md` — Руководство по аттестации
- `MONITORING-STACK-GUIDE.md` — Настройка мониторинга
- `RECOMMENDATIONS-1.md`, `RECOMMENDATIONS-2.md` — Рекомендации

**🔐 Шифрование:**
- `ENCRYPTION-IMPLEMENTATION-GUIDE.md` — Внедрение шифрования
- `ENCRYPTION-QUICK-START.md` — Быстрый старт шифрования
- `ENCRYPTION-VISUAL-GUIDE.md` — Визуальное руководство
- `AUTO-ENCRYPTION-DEPLOYMENT-GUIDE.md` — Автоматическое развёртывание
- `PRODUCTION-DEPLOYMENT-ENCRYPTION.md` — Prod развёртывание
- `PRODUCTION-ENCRYPTION-SETUP.md` — Настройка в production
- `QUICK-ENCRYPTION-DEPLOYMENT.md` — Быстрое развёртывание
- `SUMMARY-ENCRYPTION-DEPLOYMENT.md` — Сводка
- `README-ENCRYPTION-DEPLOYMENT.md` — Описание

**✅ Согласия пользователей:**
- `CONSENT-CHECKBOXES-IMPLEMENTATION.md` — Чекбоксы согласия
- `CONSENT-MODAL-TROUBLESHOOTING.md` — Диагностика модального окна
- `TELEGRAM-WEB-CONSENT-GUIDE.md` — Согласия в Telegram и Web
- `IMPLEMENTATION-GUIDE-PRIVACY-COOKIE-POLICIES.md` — Политики приватности

**🔄 Трансграничная передача:**
- `IMPLEMENTATION-GUIDE-TRANSBOUNDARY-FIX.md` — Исправление трансграничной передачи

**🐛 Исправления:**
- `FIX-BOT-GUNICORN-WORKERS.md` — Фикс Gunicorn workers
- `FIX-BOT-WITHOUT-ENCRYPTION.md` — Фикс без шифрования
- `FRONTEND-IMPROVEMENTS-ROADMAP.md` — Дорожная карта фронтенда

---

### 5️⃣ `oac/planning/` — Планы работ

Дорожные карты и чек-листы.

| Файл | Описание |
|------|----------|
| `HOSTER-DIVISION-OF-WORK.md` | Распределение работ с хостинг-провайдером |
| `oac-compliance-checklist.md` | Чек-лист compliance (с маркерами ХОСТЕР/МЫ/СОВМЕСТНО) |
| `OAC-VISUAL-PROGRESS.md` | Визуальный прогресс выполнения |
| `README.md` | Описание папки |

---

### 6️⃣ `oac/requirements/` — Требования

Детальная расшифровка требований нормативных документов.

| Файл | Описание |
|------|----------|
| `oac-requirements.md` | Требования к классу 3-ин |
| `oac-sprint.md` | Sprint-план по выполнению требований |
| `transboundary-transfer-telegram-analysis-2026-05-20.md` | Анализ трансграничной передачи Telegram |
| `README.md` | Описание папки |

---

### 7️⃣ `oac/telegram/` — Telegram-специфика

Документы, связанные с Telegram-ботом в контексте ОАЦ (трансграничная передача данных).

| Файл | Описание |
|------|----------|
| `common-privacy.md` | Общая политика приватности Telegram |
| `telegram-cereits.md` | Сертификация Telegram |
| `telegram-receits2.md` | Чек-лист по рецептам |
| `explanations/` | Разъяснения (подпапка) |

---

### 8️⃣ `oac/dop/` — Дополнительные материалы

Вспомогательные документы, не вошедшие в основные разделы.

| Файл | Описание |
|------|----------|
| `OAC-COMPLIANCE-STATUS-REPORT.md` | Отчёт о статусе соответствия |
| `REQUIRED-DOCUMENTS-FOR-COMPLIANCE.md` | Список необходимых документов |
| `PRIKAZY-OTVETSTVENNYE-IB.md` | Приказы о назначении ответственных |
| `PRIKAZ-195-ANALYSIS-TEMPLATE.md` | Шаблон анализа Приказа №195 |
| `checklist-audit-pd-2026-06-08.md` | Чек-лист аудита ПД |
| `check-list-primeryy-proverky.md` | Примеры проверок |
| `check-list-zaschita.md` | Чек-лист защиты |
| `PRIVACY-POLICY-UPDATE-SUMMARY-2026-05-20.md` | Сводка обновления политик |
| `TECHNICAL-IMPLEMENTATION-SUMMARY-2026-05-20.md` | Сводка технической реализации |
| `DOCUMENTS-ORGANIZATION-PLAN-2026-06-08.md` | План реорганизации документов |
| `README.md` | Описание папки |
| **`drafts/`** | **Черновики (не финальные)** |
| └── `questions-for-lawyer-2026-05-04.md` | Вопросы юристу |

---

## 🧭 Как пользоваться этим навигатором

### Я — новый разработчик, с чего начать?

1. **Прочитать** [QUICK-REFERENCE.md](QUICK-REFERENCE.md) — 5 минут
2. **Посмотреть** `oac/docs/` — основные документы compliance (01-15)
3. **Ознакомиться** с `oac/guides/ATTESTATION-OAC-GUIDE.md` — процесс аттестации
4. **Проверить статус** — `oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md`

### Я хочу найти документ по теме:

| Тема | Куда смотреть |
|------|---------------|
| Шифрование данных | `oac/docs/10-encryption-policy.md` + `oac/guides/ENCRYPTION-*` |
| Telegram-бот | `oac/telegram/` + `oac/requirements/transboundary-transfer-*` |
| Аттестация в ОАЦ | `oac/guides/ATTESTATION-OAC-GUIDE.md` |
| Аудиты и проверки | `oac/audits/` |
| Архитектура | `oac/architecture/` |
| Планы работ | `oac/planning/` |
| Требования ОАЦ №66 | `oac/oac.md` |
| Нормативные документы | `origin-docs/` |

### Я сделал изменения — что обновить?

1. ✅ Сохранить файл в правильную папку (см. `DOCUMENTS-ORGANIZATION-RULES.md`)
2. ✅ Обновить `oac/CHANGELOG.md`
3. ✅ Проверить, не нужно ли обновить этот `README.md`

---

## 📋 Быстрая статистика

| Показатель | Значение |
|------------|----------|
| Всего документов | ~70 файлов |
| Основных compliance (docs/) | 15 |
| Руководств (guides/) | ~25 |
| Аудитов (audits/) | 2 |
| Папок всего | 11 |
| Черновиков (drafts/) | 1 |

---

## 🔗 Связанные ресурсы

- [`origin-docs/`](../origin-docs/) — Оригинальные тексты нормативных актов
- [`docs/`](../docs/) — Проектная документация (не ОАЦ)
- [`scripts/`](../scripts/) — Скрипты автоматизации

---

*Последнее обновление: 8 июня 2026 г.*
