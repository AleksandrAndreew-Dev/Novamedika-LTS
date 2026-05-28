# AI Agent Skills for Novamedika2

Эта директория содержит шаблоны навыков (skills) для AI-агента, работающего с проектом Novamedika2.

## 📚 Доступные Skills

### 1. [OAC Compliance Checker](oac-compliance-checker.md)
**Когда использовать:**
- Добавление новых API endpoints
- Изменение обработки пользовательских данных
- Работа с персональными данными
- Реализация аутентификации/авторизации

**Что проверяет:**
- ✅ Аутентификация и авторизация (JWT + RBAC)
- ✅ Шифрование персональных данных
- ✅ Audit logging всех действий
- ✅ Согласие пользователя на обработку данных
- ✅ Трансграничная передача данных
- ✅ Права пользователей на данные

### 2. [Deployment & Diagnostics](deployment-diagnostics.md)
**Когда использовать:**
- Перед коммитом кода (pre-deployment check)
- После деплоя (верификация)
- Когда сервисы не работают
- Проблемы с производительностью
- Падение или перезапуск контейнеров

**Что включает:**
- ✅ Pre-deployment checklist
- ✅ Post-deployment verification
- ✅ Troubleshooting common issues
- ✅ Emergency procedures
- ✅ Monitoring stack access

### 3. [Telegram Bot Debugger](telegram-bot-debugger.md)
**Когда использовать:**
- Бот не отвечает на сообщения
- Ошибки webhook
- Проблемы с FSM states
- Проблемы аутентификации в боте
- Падение бота

**Что включает:**
- ✅ Quick diagnostic flow
- ✅ Common issues & solutions
- ✅ Bot architecture overview
- ✅ Manual testing procedures
- ✅ Performance optimization
- ✅ Emergency procedures

## 🎯 Как использовать Skills

### Для AI-агента:

1. **Определите тип задачи:**
   - Работа с данными пользователей → OAC Compliance Checker
   - Деплой или проблемы инфраструктуры → Deployment & Diagnostics
   - Проблемы Telegram бота → Telegram Bot Debugger

2. **Следуйте чеклисту из соответствующего skill файла:**
   - Выполните все проверки по порядку
   - Используйте указанные команды
   - Обратитесь к ресурсам при необходимости

3. **Задокументируйте результаты:**
   - Что было проверено
   - Какие проблемы найдены
   - Какие решения применены
   - Что требует дополнительной проверки

### Для разработчика:

1. **При код-ревью:**
   - Проверьте, что AI-агент использовал соответствующий skill
   - Убедитесь, что все пункты чеклиста выполнены
   - Проверьте соответствие требованиям OAC

2. **При проблемах:**
   - Откройте соответствующий skill файл
   - Следуйте инструкциям по диагностике
   - Используйте готовые команды и процедуры

## 🔧 Добавление новых Skills

Для добавления нового skill:

1. Создайте файл `skill-name.md` в этой директории
2. Используйте следующую структуру:

```markdown
# Skill: [Название навыка]

## When to use this skill:
- [Ситуация 1]
- [Ситуация 2]

## Checklist/Procedure:
[Пошаговые инструкции]

## Common Issues & Solutions:
[Типичные проблемы и решения]

## Quick Commands:
[Команды для выполнения]

## Resources:
[Ссылки на документацию]
```

3. Обновите этот README, добавив новый skill в список

## 📊 Интеграция с MCP (Model Context Protocol)

В будущем эти skills могут быть интегрированы с MCP серверами для:

- **Автоматической проверки compliance** при каждом изменении кода
- **Интеллектуальной диагностики** на основе логов
- **Контекстных рекомендаций** на основе состояния системы
- **Автоматического выполнения** рутинных проверок

### Пример MCP интеграции:

```python
# Концептуальный пример MCP сервера для OAC compliance
class OACComplianceServer(MCPServer):
    def check_endpoint_compliance(self, endpoint_code):
        # Автоматическая проверка требований OAC
        return {
            "auth_required": True,
            "audit_logging": True,
            "encryption_needed": True,
            "issues": []
        }
    
    def get_compliance_requirements(self, data_type):
        # Возвращает требования для типа данных
        return requirements_db.query(data_type)
```

## 💡 Best Practices

### Для AI-агента:
1. **Всегда проверяйте skill файлы** перед выполнением задач
2. **Используйте готовые чеклисты** вместо импровизации
3. **Ссылайтесь на конкретные sections** в отчетах
4. **Обновляйте skills** когда находите новые паттерны

### Для проекта:
1. **Регулярно обновляйте skills** на основе реального опыта
2. **Добавляйте новые skills** для повторяющихся задач
3. **Проверяйте актуальность** команд и процедур
4. **Документируйте edge cases** и их решения

## 🔗 Связанные ресурсы

- `.ai-rules.md` - Основные правила AI-агента
- `.clinerules/rules.md` - Расширенная конфигурация проекта
- `.cursorrules` - Настройки для Cursor IDE
- `agent/diagnostics.sh` - Главный инструмент диагностики
- `oac/docs/` - Документация OAC Class 3-in

## 📝 Version History

- **v1.0** (2026-05-28) - Initial skills created:
  - OAC Compliance Checker
  - Deployment & Diagnostics
  - Telegram Bot Debugger

---

**Maintained by:** Novamedika2 Development Team  
**Last updated:** 2026-05-28
