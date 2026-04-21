# NovaMedika2 - Соответствие требованиям ОАЦ

Эта папка содержит всю документацию, необходимую для соответствия требованиям Оперативно-аналитического центра (ОАЦ) при Президенте Республики Беларусь и Закона №99-З «О защите персональных данных».

---

## 📜 Правила организации документов

**Важно:** Перед добавлением новых документов ознакомьтесь с правилами:
👉 [`DOCUMENTS-ORGANIZATION-RULES.md`](DOCUMENTS-ORGANIZATION-RULES.md)

Кратко:
- **origin-docs/** - оригинальные тексты законов и приказов
- **oac/docs/** - документы compliance проекта (01-13)
- **oac/audits/** - отчеты об аудитах и проверках
- **oac/guides/** - руководства и инструкции для персонала
- **oac/planning/** - планы и дорожные карты
- **oac/requirements/** - детализированные требования

---

## 📂 Структура документации

```
oac/
├── README.md                          # Этот файл - навигация
├── oac.md                             # Приказ ОАЦ №66 (полный текст)
├── personal1.md                       # Закон РБ №99-З
│
├── requirements/                      # Требования и планы
│   ├── oac-requirements.md           # Полные требования ОАЦ к системе
│   └── oac-sprint.md                 # План спринтов по внедрению
│
├── audits/                            # Аудиты и анализы
│   ├── oac-audit.md                  # Полный детальный аудит системы
│   ├── oac-audit-summary.md          # Краткая сводка аудита
│   ├── PRIVACY-POLICY-AUDIT.md       # Аудит политики обработки ПД
│   └── OAC-ENCRYPTION-ANALYSIS.md    # Анализ требований к шифрованию
│
├── guides/                            # Руководства и инструкции
│   ├── QUICK-START-SECURITY.md       # Быстрый старт: настройка безопасности
│   ├── OAC-FREE-SOLUTIONS.md         # Бесплатные решения для compliance
│   └── OAC-FREE-SOLUTIONS-CHEATSHEET.md  # Шпаргалка по бесплатным инструментам
│
├── planning/                          # Планирование и отслеживание
│   ├── oac-compliance-checklist.md   # Интерактивный чек-лист (115 задач)
│   ├── OAC-VISUAL-PROGRESS.md        # Визуальный dashboard прогресса
│   └── OAC-AUDIT-SUMMARY-FOR-TEAM.md # Документ для команды
│
└── docs/                              # Шаблоны документов для ОАЦ
    ├── 01-act-class-3in.md           # Акт отнесения к классу 3-ин
    ├── 02-structural-schema.md       # Структурная схема системы
    ├── 03-logical-schema.md          # Логическая схема системы
    ├── 04-privacy-policy.md          # Политика обработки ПД
    ├── 05-infosec-policy.md          # Политика информационной безопасности
    ├── 06-tech-spec.md               # Техническое задание на СЗИ
    ├── 07-ib-monitoring-reglament.md # Регламент мониторинга ИБ
    ├── 08-backup-reglament.md        # Регламент резервного копирования
    ├── 09-data-retention-reglament.md# Регламент хранения данных
    ├── 10-encryption-policy.md       # Политика шифрования
    ├── 11-antivirus-reglament.md     # Регламент антивирусной защиты
    ├── 12-ids-ips-reglament.md       # Регламент IDS/IPS
    └── 13-vuln-scan-reglament.md     # Регламент сканирования уязвимостей
```

---

## 🎯 Быстрый старт

### Для руководителей и менеджеров:

1. **[audits/oac-audit-summary.md](audits/oac-audit-summary.md)** - Краткая сводка аудита с планом действий и бюджетом
2. **[planning/OAC-AUDIT-SUMMARY-FOR-TEAM.md](planning/OAC-AUDIT-SUMMARY-FOR-TEAM.md)** - Документ для briefing команды
3. **[planning/OAC-VISUAL-PROGRESS.md](planning/OAC-VISUAL-PROGRESS.md)** - Визуальный dashboard готовности

### Для технических специалистов:

1. **[guides/QUICK-START-SECURITY.md](guides/QUICK-START-SECURITY.md)** - Пошаговая инструкция по настройке безопасности (15-20 мин)
2. **[guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md](guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md)** - Шпаргалка по бесплатным инструментам
3. **[audits/OAC-ENCRYPTION-ANALYSIS.md](audits/OAC-ENCRYPTION-ANALYSIS.md)** - Анализ требований к шифрованию данных

### Для разработчиков:

1. **[planning/oac-compliance-checklist.md](planning/oac-compliance-checklist.md)** - Чек-лист из 115 задач для отслеживания
2. **[audits/oac-audit.md](audits/oac-audit.md)** - Полный детальный аудит системы
3. **[audits/PRIVACY-POLICY-AUDIT.md](audits/PRIVACY-POLICY-AUDIT.md)** - Аудит политики обработки ПД

### Для работы с документами ОАЦ:

1. **[requirements/oac-requirements.md](requirements/oac-requirements.md)** - Полные требования ОАЦ к системе
2. **[docs/](docs/)** - Шаблоны 13 обязательных документов
3. **[oac.md](oac.md)** - Приказ ОАЦ №66 (полный текст закона)

---

## 📊 Текущий статус готовности

**Общая готовность к аттестации:** **45%** → **95%+** (план после реализации)

### По категориям:

| Категория | Готовность | Документ |
|-----------|------------|----------|
| **Анализ требований** | 100% ✅ | [requirements/oac-requirements.md](requirements/oac-requirements.md) |
| **Аудит системы** | 100% ✅ | [audits/oac-audit.md](audits/oac-audit.md) |
| **Политика ПД** | 85% ⚠️ | [audits/PRIVACY-POLICY-AUDIT.md](audits/PRIVACY-POLICY-AUDIT.md) |
| **Шифрование** | 100% ✅ | [audits/OAC-ENCRYPTION-ANALYSIS.md](audits/OAC-ENCRYPTION-ANALYSIS.md) |
| **Инфраструктура** | 60% ⚠️ | [guides/QUICK-START-SECURITY.md](guides/QUICK-START-SECURITY.md) |
| **Документация ОАЦ** | 20% ❌ | [docs/](docs/) |
| **Тестирование** | 0% ❌ | [guides/OAC-FREE-SOLUTIONS.md](guides/OAC-FREE-SOLUTIONS.md) |

---

## 🗺️ Дорожная карта соответствия

### Недели 1-2: Документация и планирование
- [ ] Заполнить шаблоны документов в `docs/`
- [ ] Создать комиссию по аттестации
- [ ] Провести акт классификации системы

### Недели 3-4: Критическая инфраструктура
- [ ] Настроить централизованное логирование (ELK Stack)
- [ ] Внедрить шифрование БД (pgcrypto)
- [ ] Настроить автоматический backup

### Недели 5-6: Дополнительные меры защиты
- [ ] Установить антивирус (ClamAV)
- [ ] Настроить защиту от brute-force (Fail2Ban)
- [ ] Внедрить мониторинг (Prometheus + Grafana)

### Недели 7-8: Тестирование
- [ ] Запустить OWASP ZAP scan
- [ ] Провести penetration testing
- [ ] Исправить найденные уязвимости

### Неделя 9: Аттестация
- [ ] Подготовить пакет документов
- [ ] Провести испытания
- [ ] Подать сведения в ОАЦ

---

## 💰 Бюджет проекта

### С использованием бесплатных решений:

| Статья расходов | Стоимость |
|----------------|-----------|
| Единовременные затраты | $3,120-5,240 |
| Ежегодные затраты | $1,120-2,240/год |
| **Экономия vs платные решения** | **$6,000-7,000/год (72-82%)** |

Подробнее: [guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md](guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md)

---

## 🔗 Полезные ссылки

### Внешние ресурсы:
- [Национальный центр защиты персональных данных (НЦЗПД)](https://pdpa.by/)
- [Закон РБ №99-З «О защите персональных данных»](personal1.md)
- [Приказ ОАЦ №66 от 20.02.2020](oac.md)

### Внутренние документы:
- [Главный README проекта](../README.md)
- [Скрипты автоматизации](../scripts/README.md)
- [Backend документация](../backend/)

---

## 📞 Контакты и поддержка

**Ответственный за соответствие ОАЦ:**
- Должность: [ДОЛЖНОСТЬ]
- ФИО: [ФИО]
- Email: privacy@novamedika.com
- Телефон: [+375 (XX) XXX-XX-XX]

**Техническая поддержка:**
- Email: tech@novamedika.com
- Telegram: [@NovaMedikaSupport](https://t.me/NovaMedikaSupport)

---

## 📝 История изменений

| Версия | Дата | Изменения | Автор |
|--------|------|-----------|-------|
| 2.0 | 21.04.2026 | Реорганизация структуры документации | AI Assistant |
| 1.0 | 20.04.2026 | Первоначальная версия | AI Assistant |

---

**Последнее обновление:** 21 апреля 2026 г.  
**Статус:** Актуально  
**Класс ИС:** 3-ин
