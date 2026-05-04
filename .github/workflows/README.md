# GitHub Actions CI/CD для Novamedika2

## 🚀 Быстрый старт

### Запуск деплоя вручную

```bash
# Через GitHub UI: Actions → Deploy to Production → Run workflow
# Или через CLI:
gh workflow run deploy.yml --ref main
```

## ⚠️ Решение проблем с таймаутом

### Симптомы проблемы

Если в логах видите:
```
Downloading [===========================================>       ]  48.28MB/55.69MB
...
2026/05/04 13:40:44 Run Command Timeout
```

**Это проблема на стороне runner'а**, а не вашего кода.

### Причины

1. **Медленная сеть на сервере** - загрузка образов занимает >10 минут
2. **Нет кэширования базовых образов** между запусками
3. **Нехватка дискового пространства** на runner'е
4. **Ограничение времени выполнения команды** в self-hosted runner

### Примененные решения

В файле `.github/workflows/deploy.yml` добавлены:

1. ✅ **Явные таймауты** для каждого job (30-45 минут)
2. ✅ **Предварительная загрузка базовых образов** (python, node, nginx)
3. ✅ **Диагностика окружения** перед сборкой (диск, память, CPU, сеть)

### Дополнительные меры на сервере

#### 1. Очистка дискового пространства

**Проблема:** Docker образы и контейнеры накапливаются и занимают всё место

**Решение:** Настроить автоматическую очистку

```bash
# Подключиться к серверу
ssh user@your-server

# Разовая очистка
docker system prune -af --volumes

# Автоматическая еженедельная очистка
sudo crontab -e
# Добавить строку:
0 3 * * 0 /usr/bin/docker system prune -af --volumes >> /var/log/docker-cleanup.log 2>&1
```

#### 2. Проверка здоровья runner'а

Создать скрипт мониторинга:

```bash
cat > /opt/actions-runner/check-health.sh << 'EOF'
#!/bin/bash
echo "=== Runner Health Check ==="
echo "Time: $(date)"

# Диск
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
echo "Disk usage: ${DISK_USAGE}%"
if [ $DISK_USAGE -gt 85 ]; then
  echo "⚠️ CRITICAL: Disk usage > 85%, cleaning..."
  docker system prune -af --volumes
fi

# Память
MEMORY_FREE=$(free -m | awk 'NR==2{printf "%.0f", $4*100/$2}')
echo "Memory free: ${MEMORY_FREE}%"
if [ $MEMORY_FREE -lt 10 ]; then
  echo "⚠️ WARNING: Low memory"
fi

# Docker образы
echo "Docker images count: $(docker images -q | wc -l)"
echo "Docker total size: $(docker system df | tail -1)"

# Runner статус
RUNNER_STATUS=$(curl -s http://localhost:8080/health || echo "unknown")
echo "Runner health: $RUNNER_STATUS"
EOF

chmod +x /opt/actions-runner/check-health.sh

# Запускать перед каждым билдом
crontab -e
# Добавить:
*/15 * * * * /opt/actions-runner/check-health.sh >> /var/log/runner-health.log 2>&1
```

#### 3. Оптимизация Docker BuildKit

Создать конфигурацию `/etc/docker/daemon.json`:

```json
{
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "5GB",
      "policy": [
        { "keepStorage": "2GB", "all": false },
        { "keepStorage": "500MB", "all": true }
      ]
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Перезапустить Docker:
```bash
sudo systemctl restart docker
```

#### 4. Проверка скорости сети

```bash
# Установить speedtest-cli
sudo apt install speedtest-cli

# Проверить скорость
speedtest-cli

# Минимальные требования:
# - Download: >10 Mbps
# - Upload: >5 Mbps
# - Latency: <100ms
```

Если скорость низкая:
- Проверить нагрузку на сеть (`iftop`, `nethogs`)
- Рассмотреть использование зеркала Docker Hub в вашем регионе
- Настроить proxy для Docker

### Диагностика при проблеме

Если таймаут повторяется:

1. **Проверить логи диагностики** в GitHub Actions:
   - Найти шаг "Check runner environment"
   - Посмотреть вывод: диск, память, CPU
   - **Важно:** Если видите `Error: Process completed with exit code 141` - это SIGPIPE ошибка от `docker images | head`, она не критична и исправлена добавлением `|| true`

2. **Подключиться к серверу и проверить:**
```bash
# Диск
df -h /
du -sh /var/lib/docker/* | sort -rh | head -5

# Память
free -h
top -bn1 | head -20

# Сеть
ping -c 3 github.com
time curl -o /dev/null https://ghcr.io

# Docker процессы
docker ps
docker system df
```

3. **Проверить системные логи:**
```bash
# Логи runner'а
tail -100 /opt/actions-runner/_diag/*.log

# Системные логи
journalctl -u actions.runner.* -n 50 --no-pager
dmesg | tail -20
```

### Рекомендуемые ресурсы сервера

**Минимальные требования:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 50 GB SSD
- Network: 10+ Mbps

**Рекомендуемые:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 100 GB SSD
- Network: 50+ Mbps

## 📊 Мониторинг

### Метрики для отслеживания

1. **Время сборки** (должно быть <15 минут)
2. **Использование диска** (должно быть <80%)
3. **Успешность деплоя** (>95%)
4. **Время отклика API** после деплоя

### Настройка алертов

```bash
# Простой мониторинг через cron
cat > /opt/monitor-runner.sh << 'EOF'
#!/bin/bash
ALERT_EMAIL="admin@example.com"

# Проверка диска
DISK=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK -gt 90 ]; then
  echo "CRITICAL: Disk ${DISK}%" | mail -s "Runner Alert" $ALERT_EMAIL
fi

# Проверка runner процесса
if ! pgrep -f "actions.runner" > /dev/null; then
  echo "CRITICAL: Runner process not running" | mail -s "Runner Down" $ALERT_EMAIL
  systemctl restart actions.runner
fi
EOF

chmod +x /opt/monitor-runner.sh
crontab -e
# Добавить:
*/5 * * * * /opt/monitor-runner.sh
```

## 🔧 Обновление runner'а

```bash
# Остановить runner
cd /opt/actions-runner
./svc.sh stop

# Обновить
git pull origin main
./config.sh remove --token $TOKEN
./config.sh --url https://github.com/your-org --token $NEW_TOKEN

# Запустить
./svc.sh start
```

## 📝 Чеклист перед деплоем

- [ ] Диск имеет >10GB свободного места
- [ ] Памяти свободно >1GB
- [ ] Сеть стабильна (проверить пинг до github.com)
- [ ] Runner процесс запущен и активен
- [ ] Нет активных сборок (чтобы избежать конфликтов)
- [ ] Базовые образы закэшированы (`docker images | grep -E "python|node|nginx"`)

## 🆘 Экстренные действия

Если деплой завис или упал:

1. **Отменить текущий workflow** в GitHub UI
2. **Проверить состояние контейнеров:**
```bash
docker-compose -f docker-compose.traefik.prod.yml ps
```
3. **Если контейнеры не запустились:**
```bash
docker-compose -f docker-compose.traefik.prod.yml logs --tail=100
docker-compose -f docker-compose.traefik.prod.yml up -d --force-recreate
```
4. **Очистить место если нужно:**
```bash
docker system prune -af --volumes
```
5. **Перезапустить деплой**

---

**Последнее обновление:** 2026-05-04
**Версия документа:** 1.1