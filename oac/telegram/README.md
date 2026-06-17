# Telegram-специфика NovaMedika2 (контекст ОАЦ)

**Назначение папки:** Документы, описывающие специфику работы NovaMedika2 через Telegram Bot в контексте требований ОАЦ (трансграничная передача, согласия, особенности GDPR/Закон №99-З).

---

## 📋 Назначение

Telegram-бот — один из основных каналов взаимодействия с пользователями (наряду с Web-сайтом). Использование Telegram Bot API создаёт **трансграничную передачу персональных данных** (Telegram Messenger LLP зарегистрировано в Великобритании, серверы распределены по миру), что требует специального документирования и информирования субъектов ПД.

**Важно:** Это НЕ про сам Telegram Bot, а про **его соответствие требованиям ОАЦ**.

---

## 📂 Содержимое

| Документ | Назначение |
|----------|------------|
| [common-privacy.md](common-privacy.md) | Общая политика конфиденциальности (применимая в т.ч. к Telegram) |
| [telegram-cereits.md](telegram-cereits.md) | Сценарии/согласия (consents) для Telegram-бота |
| [telegram-receits2.md](telegram-receits2.md) | Дополнительные сценарии (receipts) для Telegram |
| [explanations/](explanations/) | Пояснения и обоснования по специфике Telegram |

---

## 🔗 Связанные папки и документы

- [`../docs/04-privacy-policy.md`](../docs/04-privacy-policy.md) — Политика обработки ПД (раздел 4 — трансграничная передача через Telegram)
- [`../requirements/transboundary-transfer-telegram-analysis-2026-05-20.md`](../requirements/transboundary-transfer-telegram-analysis-2026-05-20.md) — Правовой анализ трансграничной передачи
- [`../guides/TELEGRAM-WEB-CONSENT-GUIDE.md`](../guides/TELEGRAM-WEB-CONSENT-GUIDE.md) — Гайд по реализации согласий
- [`../guides/IMPLEMENTATION-GUIDE-TRANSBOUNDARY-FIX.md`](../guides/IMPLEMENTATION-GUIDE-TRANSBOUNDARY-FIX.md) — Инструкция по исправлению политики

---

**Последнее обновление:** 8 июня 2026 г.
**Причина перемещения:** Реорганизация структуры — `telegram-privacy/` из корня проекта перенесён в `oac/telegram/` как логически связанный с ОАЦ-compliance
