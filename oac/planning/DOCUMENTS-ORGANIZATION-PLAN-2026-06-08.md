# ПЛАН РЕОРГАНИЗАЦИИ ДОКУМЕНТОВ

**Дата:** 8 июня 2026 г.
**Автор плана:** AI-ассистент (Cline)
**Статус:** ⏳ Ожидает утверждения
**Связанные документы:**
- [`oac/DOCUMENTS-ORGANIZATION-RULES.md`](../DOCUMENTS-ORGANIZATION-RULES.md) — целевые правила
- [`oac/README.md`](../README.md) — навигация
- [`oac/CHANGELOG.md`](../CHANGELOG.md) — журнал изменений

---

## 📋 НАЗНАЧЕНИЕ

Документ фиксирует план приведения структуры папок проекта NovaMedika2 в соответствие с [`oac/DOCUMENTS-ORGANIZATION-RULES.md`](../DOCUMENTS-ORGANIZATION-RULES.md) и обеспечения логичной, единообразной организации всех документов по **контексту и применению**.

---

## 🎯 ПРИНЦИПЫ ОРГАНИЗАЦИИ

| № | Принцип | Применение |
|---|---------|------------|
| 1 | **Оригинал ≠ Проектный документ** | `origin-docs/` — только тексты законов/приказов, `oac/docs/` — наши compliance-документы |
| 2 | **Один тип = одна папка** | Гайды → `guides/`, аудиты → `audits/`, планы → `planning/` (НЕ смешивать) |
| 3 | **Соответствие = нумерация** | `oac/docs/` — строго 01-14 + дополнительные с новым номером |
| 4 | **OAC ≠ Проект** | Всё про ОАЦ-соответствие → `oac/`, прочая проектная документация → `docs/` в корне |
| 5 | **Telegram-специфика = подпапка OAC** | `telegram-privacy/` → `oac/telegram/` (логически часть ОАЦ-compliance) |

---

## 📂 ЦЕЛЕВАЯ СТРУКТУРА

```
Novamedika2/
├── README.md                       # Главное описание проекта
├── docs/                           # 🆕 Проектная документация (НЕ про ОАЦ)
│   ├── README.md
│   ├── AI-OPTIMIZATION-GUIDE.md
│   ├── AI-QUICK-START.md
│   ├── CONFIGURATION-SUMMARY.md
│   ├── DEPLOYMENT-MONITORING-ENHANCEMENT.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── SECURITY-IMPLEMENTATION-GUIDE.md
│
├── origin-docs/                    # Оригинальные тексты законов/приказов
│   ├── README.md                   # 🆕 Создать
│   ├── NORMATIVNYE-DOKUMENTY-REGISTER.md  # 🆕 Перенести из oac/dop/
│   ├── 66.md                       # Приказ ОАЦ №66
│   ├── 99-3n.md                    # Закон №99-З
│   ├── 422.md                      # Указ №422
│   ├── 449.md                      # Указ №449
│   ├── 455-3.md                    # Закон №455-З
│   ├── ask.md                      # Шаблон/вопросник
│   ├── nczpd-clarifications-2021-12-03.md  # 🆕 Переименовать из oac/personal1.md
│   ├── pd-policy-clinic-template.md        # 🆕 Перенести из oac/privacy-policy/
│   ├── nczpd-recommendations-healthcare.md  # 🆕 Перенести
│   └── nczpd-recommendations-business.md    # 🆕 Перенести
│
├── oac/                            # Всё про соответствие ОАЦ
│   ├── README.md                   # Навигация
│   ├── oac.md                      # Приказ №66 (по правилам - в корне oac/)
│   ├── CHANGELOG.md                # Журнал изменений
│   ├── DOCUMENTS-ORGANIZATION-RULES.md
│   ├── QUICK-REFERENCE.md
│   │
│   ├── docs/                       # Compliance документы (01-14 + дополнительные)
│   │   ├── 01-act-class-3in.md
│   │   ├── 02-structural-schema.md
│   │   ├── 03-logical-schema.md
│   │   ├── 04-privacy-policy.md
│   │   ├── 05-infosec-policy.md
│   │   ├── 06-tech-spec.md
│   │   ├── 07-ib-monitoring-reglament.md
│   │   ├── 08-backup-reglament.md
│   │   ├── 09-data-retention-reglament.md
│   │   ├── 10-encryption-policy.md
│   │   ├── 11-antivirus-reglament.md
│   │   ├── 12-ids-ips-reglament.md
│   │   ├── 13-vuln-scan-reglament.md
│   │   ├── 14-personal-data-processing-architecture.md
│   │   └── 15-cookie-policy.md     # 🆕 Переименовать из 05-cookie-policy.md
│   │
│   ├── architecture/               # 🆕 Архитектурные решения
│   │   ├── README.md
│   │   ├── PRESCRIPTION-PHOTO-ARCHITECTURE-SOLUTION.md  # 🆕 Из oac/docs/
│   │   ├── PRESCRIPTION-PHOTO-SOLUTION-SUMMARY.md      # 🆕 Из oac/docs/
│   │   ├── SIMPLIFIED-PRESCRIPTION-ARCHITECTURE.md      # 🆕 Из oac/docs/
│   │   └── WEB-APP-CHAT-ARCHITECTURE.md                 # 🆕 Из oac/docs/
│   │
│   ├── audits/                     # Отчёты об аудитах
│   │   ├── README.md
│   │   ├── audit-personal-data-2026-06-08.md  # 🆕 Из oac/privacy-policy/
│   │   └── audit-policy-2026-05-20.md         # 🆕 Из oac/privacy-policy/
│   │
│   ├── guides/                     # Пошаговые инструкции
│   │   ├── README.md
│   │   ├── CONSENT-CHECKBOXES-IMPLEMENTATION.md
│   │   ├── CONSENT-MODAL-TROUBLESHOOTING.md
│   │   ├── ENCRYPTION-IMPLEMENTATION-GUIDE.md
│   │   ├── ENCRYPTION-QUICK-START.md
│   │   ├── ENCRYPTION-VISUAL-GUIDE.md
│   │   ├── FIX-BOT-GUNICORN-WORKERS.md
│   │   ├── FIX-BOT-WITHOUT-ENCRYPTION.md
│   │   ├── FRONTEND-IMPROVEMENTS-ROADMAP.md
│   │   ├── IMPLEMENTATION-GUIDE-PRIVACY-COOKIE-POLICIES.md  # 🆕 Из oac/docs/
│   │   ├── IMPLEMENTATION-GUIDE-TRANSBOUNDARY-FIX.md        # 🆕 Из oac/privacy-policy/
│   │   ├── MONITORING-STACK-GUIDE.md
│   │   ├── OAC-FREE-SOLUTIONS-CHEATSHEET.md
│   │   ├── OAC-FREE-SOLUTIONS.md
│   │   ├── PRODUCTION-ENCRYPTION-SETUP.md
│   │   ├── QUICK-ENCRYPTION-DEPLOYMENT.md
│   │   ├── QUICK-START-SECURITY.md
│   │   ├── README-ENCRYPTION-DEPLOYMENT.md
│   │   ├── RECOMMENDATIONS-OPEN-SOURCE.md    # 🆕 Объединить 4 файла из oac/help/
│   │   ├── SUMMARY-ENCRYPTION-DEPLOYMENT.md
│   │   └── TELEGRAM-WEB-CONSENT-GUIDE.md
│   │
│   ├── planning/                   # Планы и дорожные карты
│   │   ├── README.md
│   │   ├── HOSTER-DIVISION-OF-WORK.md
│   │   ├── oac-compliance-checklist.md
│   │   └── OAC-VISUAL-PROGRESS.md
│   │
│   ├── requirements/               # Детализированные требования
│   │   ├── README.md
│   │   ├── oac-requirements.md
│   │   ├── oac-sprint.md
│   │   └── transboundary-transfer-telegram-analysis-2026-05-20.md  # 🆕 Из oac/privacy-policy/
│   │
│   ├── dop/                        # Дополнительные документы
│   │   ├── README.md
│   │   ├── check-list-primeryy-proverky.md
│   │   ├── check-list-zaschita.md
│   │   ├── OAC-COMPLIANCE-STATUS-REPORT.md
│   │   ├── PRIKAZ-195-ANALYSIS-TEMPLATE.md
│   │   ├── PRIKAZY-OTVETSTVENNYE-IB.md      # 🆕 Из oac/docs/
│   │   ├── REQUIRED-DOCUMENTS-FOR-COMPLIANCE.md
│   │   ├── DOCUMENTS-ORGANIZATION-PLAN-2026-06-08.md  # Этот файл
│   │   └── drafts/                  # 🆕 Рабочие черновики
│   │       ├── README.md
│   │       └── questions-for-lawyer-2026-05-04.md  # 🆕 Из oac/questions-for-lawyer.md
│   │
│   └── telegram/                   # 🆕 Telegram-специфика (из telegram-privacy/)
│       ├── README.md
│       ├── common-privacy.md
│       ├── telegram-cereits.md
│       ├── telegram-receits2.md
│       └── explanations/
│
├── scripts/                        # Без изменений
├── skills/                         # Без изменений
├── config/                         # Без изменений
├── dashboards/                     # Без изменений
├── traefic/                        # Без изменений
├── backend/                        # Без изменений
├── frontend/                       # Без изменений
└── uploaded_csv/                   # Без изменений
```

---

## 🚀 ПЛАН ВЫПОЛНЕНИЯ

### Этап 1: Подготовка инфраструктуры
- [ ] Создать новые папки: `docs/`, `oac/architecture/`, `oac/telegram/`, `oac/dop/drafts/`
- [ ] Создать README.md в каждой новой папке

### Этап 2: Очистка `oac/docs/`
- [ ] Переименовать `oac/docs/05-cookie-policy.md` → `oac/docs/15-cookie-policy.md`
- [ ] Переместить `oac/docs/AUTO-ENCRYPTION-DEPLOYMENT-GUIDE.md` → `oac/guides/`
- [ ] Переместить `oac/docs/PRODUCTION-DEPLOYMENT-ENCRYPTION.md` → `oac/guides/`
- [ ] Переместить `oac/docs/IMPLEMENTATION-GUIDE-PRIVACY-COOKIE-POLICIES.md` → `oac/guides/`
- [ ] Переместить `oac/docs/PRESCRIPTION-PHOTO-ARCHITECTURE-SOLUTION.md` → `oac/architecture/`
- [ ] Переместить `oac/docs/PRESCRIPTION-PHOTO-SOLUTION-SUMMARY.md` → `oac/architecture/`
- [ ] Переместить `oac/docs/SIMPLIFIED-PRESCRIPTION-ARCHITECTURE.md` → `oac/architecture/`
- [ ] Переместить `oac/docs/WEB-APP-CHAT-ARCHITECTURE.md` → `oac/architecture/`
- [ ] Переместить `oac/docs/PRIKAZY-OTVETSTVENNYE-IB.md` → `oac/dop/`

### Этап 3: Консолидация `oac/audits/`
- [ ] Переместить `oac/privacy-policy/audit-personal-data-2026-06-08.md` → `oac/audits/`
- [ ] Переместить `oac/privacy-policy/audit-policy-2026-05-20.md` → `oac/audits/`

### Этап 4: Нормативные тексты в `origin-docs/`
- [ ] Переименовать `oac/personal1.md` → `origin-docs/nczpd-clarifications-2021-12-03.md`
- [ ] Переместить `oac/privacy-policy/politika-policliniki.md` → `origin-docs/pd-policy-clinic-template.md`
- [ ] Переместить `oac/privacy-policy/recomendations-minzdrav-zdravoohrannie.md` → `origin-docs/nczpd-recommendations-healthcare.md`
- [ ] Переместить `oac/privacy-policy/recommendations-business.md` → `origin-docs/nczpd-recommendations-business.md`
- [ ] Переместить `oac/dop/NORMATIVNYE-DOKUMENTY-REGISTER.md` → `origin-docs/`
- [ ] Создать `origin-docs/README.md`

### Этап 5: Аналитика и гайды
- [ ] Переместить `oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md` → `oac/requirements/`
- [ ] Переместить `oac/privacy-policy/IMPLEMENTATION-GUIDE-TRANSBOUNDARY-FIX.md` → `oac/guides/`

### Этап 6: Telegram-специфика
- [ ] Переместить `telegram-privacy/*` → `oac/telegram/`
- [ ] Создать `oac/telegram/README.md`

### Этап 7: Рабочие черновики
- [ ] Переместить `oac/questions-for-lawyer.md` → `oac/dop/drafts/questions-for-lawyer-2026-05-04.md`

### Этап 8: Рекомендации
- [ ] Объединить `oac/help/recomends1.md`, `recomends2.md`, `recomends3.md`, `opensource.md` → `oac/guides/RECOMMENDATIONS-OPEN-SOURCE.md`
- [ ] Удалить пустые папки `oac/help/`, `oac/checklist/`, `oac/privacy-policy/`

### Этап 9: Проектная документация (корень → docs/)
- [ ] Переместить `AI-OPTIMIZATION-GUIDE.md` → `docs/`
- [ ] Переместить `AI-QUICK-START.md` → `docs/`
- [ ] Переместить `CONFIGURATION-SUMMARY.md` → `docs/`
- [ ] Переместить `DEPLOYMENT-MONITORING-ENHANCEMENT.md` → `docs/`
- [ ] Переместить `IMPLEMENTATION_SUMMARY.md` → `docs/`
- [ ] Переместить `SECURITY-IMPLEMENTATION-GUIDE.md` → `docs/`
- [ ] Создать `docs/README.md`

### Этап 10: Обновление документации
- [ ] Обновить `oac/README.md` (отразить новую структуру)
- [ ] Обновить корневой `README.md` (ссылки на `docs/`)
- [ ] Обновить `oac/CHANGELOG.md` (запись о реорганизации)

---

## ⚠️ РИСКИ И ОГРАНИЧЕНИЯ

| Риск | Описание | Митигация |
|------|----------|-----------|
| Сломанные ссылки | В файлах есть относительные ссылки на старые пути | Обновить ссылки в затронутых файлах |
| Git история | Перемещение не сохраняет историю | Использовать `git mv` где возможно (если не в git-репо) |
| Не прочитанное содержимое | Я не читал все 50+ файлов | Возможна ошибка в классификации — отметить в CHANGELOG |
| Параллельная работа | CHANGELOG правится разными людьми | Использовать новую секцию "Реорганизация 2026-06-08" |

---

## 📝 ЧЕКЛИСТ ПЕРЕД НАЧАЛОМ РАБОТ

- [x] Прочитаны правила `oac/DOCUMENTS-ORGANIZATION-RULES.md`
- [x] Прочитан `oac/README.md`, `oac/CHANGELOG.md`, `README.md`
- [x] Проверено содержимое всех ключевых папок (`oac/*`, `origin-docs/`, корень)
- [ ] Подтверждение от пользователя по 4 открытым вопросам (см. ниже)

---

## ❓ ОТКРЫТЫЕ ВОПРОСЫ

1. **Объединять ли `oac/help/*` в один файл `RECOMMENDATIONS-OPEN-SOURCE.md`** или оставить 4 файла?
   - Рекомендация: объединить, так как они все про рекомендации

2. **Создавать ли `docs/` в корне** для проектной документации (AI-гайды, конфигурация)?
   - Рекомендация:
