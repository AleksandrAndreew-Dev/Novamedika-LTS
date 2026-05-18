#!/bin/bash
# ============================================================================
# Автоматическая настройка сервера для NovaMedika2 с security stack
# Запускать один раз при первоначальной настройке production сервера
# ============================================================================

set -euo pipefail

echo "=== NovaMedika2 Server Setup with Security Stack ==="
echo "Дата: $(date)"
echo "Сервер: $(hostname)"
echo ""

# Проверка root прав
if [ "$EUID" -ne 0 ]; then
    echo "❌ Этот скрипт требует root права"
    echo "Запустите: sudo $0"
    exit 1
fi

# ============================================================================
# ШАГ 1: Обновление системы и установка базовых пакетов
# ============================================================================
echo "[1/8] Обновление системы..."
apt update && apt upgrade -y

echo "[2/8] Установка необходимых пакетов..."
apt install -y \
    docker.io \
    docker-compose \
    fail2ban \
    ufw \
    mailutils \
    postfix \
    curl \
    wget \
    git \
    htop \
    jq \
    unzip

# Настройка Postfix для отправки email
echo "postfix postfix/main_mailer_type select 'Internet Site'" | debconf-set-selections
echo "postfix postfix/mailname string $(hostname)" | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt install -y postfix

# ============================================================================
# ШАГ 2: Настройка Docker
# ============================================================================
echo "[3/8] Настройка Docker..."

# Добавление текущего пользователя в группу docker
if [ -n "${SUDO_USER}" ]; then
    usermod -aG docker ${SUDO_USER}
    echo "✅ Пользователь ${SUDO_USER} добавлен в группу docker"
fi

# Создание директории для проектов
mkdir -p /opt/novamedika-prod
chown -R ${SUDO_USER:-root}:${SUDO_USER:-root} /opt/novamedika-prod

# Оптимизация Docker для ограниченных ресурсов
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
EOF

systemctl restart docker
echo "✅ Docker настроен"

# ============================================================================
# ШАГ 3: Настройка Firewall (UFW)
# ============================================================================
echo "[4/8] Настройка firewall..."

ufw default deny incoming
ufw default allow outgoing

# Разрешение необходимых портов
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 3000/tcp  # Grafana (опционально, можно убрать после настройки)
ufw allow 3100/tcp  # Loki (только для внутреннего использования)

ufw --force enable
echo "✅ Firewall настроен"

# ============================================================================
# ШАГ 4: Настройка Fail2ban
# ============================================================================
echo "[5/8] Настройка Fail2ban..."

# Создание backup оригинальной конфигурации
cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.conf.backup 2>/dev/null || true

# Настройка email уведомлений
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = auto
usedns = warn
logencoding = utf-8
enabled = true

# Email уведомления
destemail = admin@novamedika.com
sender = fail2ban@novamedika.com
mta = sendmail
action = %(action_mwl)s

# Игнорировать localhost
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
findtime = 600
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "✅ Fail2ban настроен"

# ============================================================================
# ШАГ 5: Создание структуры директорий
# ============================================================================
echo "[6/8] Создание структуры директорий..."

mkdir -p /opt/novamedika-prod/{config,dashboards,scripts,backups,reports}
mkdir -p /opt/reports/{openvas,security-audit}
mkdir -p /var/lib/docker/volumes

chown -R ${SUDO_USER:-root}:${SUDO_USER:-root} /opt/novamedika-prod
chown -R ${SUDO_USER:-root}:${SUDO_USER:-root} /opt/reports

echo "✅ Директории созданы"

# ============================================================================
# ШАГ 6: Настройка системных лимитов
# ============================================================================
echo "[7/8] Настройка системных лимитов..."

# Увеличение лимитов для Elasticsearch/Loki
cat >> /etc/sysctl.conf << 'EOF'

# NovaMedika2 optimizations
vm.max_map_count=262144
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
EOF

sysctl -p

# Настройка limits для пользователя
cat >> /etc/security/limits.conf << 'EOF'

# NovaMedika2 Docker limits
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

echo "✅ Системные лимиты настроены"

# ============================================================================
# ШАГ 7: Создание systemd сервисов для мониторинга
# ============================================================================
echo "[8/8] Создание systemd сервисов..."

# Сервис для Loki
cat > /etc/systemd/system/loki.service << 'EOF'
[Unit]
Description=Loki Log Aggregator
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker-compose -f /opt/novamedika-prod/docker-compose.monitoring.yml up loki
ExecStop=/usr/bin/docker-compose -f /opt/novamedika-prod/docker-compose.monitoring.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Сервис для Promtail
cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail Log Collector
After=docker.service loki.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker-compose -f /opt/novamedika-prod/docker-compose.monitoring.yml up promtail
ExecStop=/usr/bin/docker-compose -f /opt/novamedika-prod/docker-compose.monitoring.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✅ Systemd сервисы созданы"

# ============================================================================
# ФИНАЛ: Инструкция по дальнейшим действиям
# ============================================================================
echo ""
echo "=========================================="
echo "✅ НАСТРОЙКА СЕРВЕРА ЗАВЕРШЕНА"
echo "=========================================="
echo ""
echo "Следующие шаги:"
echo ""
echo "1. Клонируйте репозиторий:"
echo "   cd /opt/novamedika-prod"
echo "   git clone <repository-url> ."
echo ""
echo "2. Создайте .env файл:"
echo "   cp .env.example .env"
echo "   nano .env  # Заполните переменные окружения"
echo ""
echo "3. Подпишите приказы о назначении ответственных:"
echo "   oac/docs/PRIKAZY-OTVETSTVENNYE-IB.md"
echo ""
echo "4. Запустите деплой через GitHub Actions или вручную:"
echo "   docker-compose -f docker-compose.traefik.prod.yml up -d"
echo "   docker-compose -f docker-compose.monitoring.yml up -d"
echo ""
echo "5. Настройте Grafana Cloud (опционально):"
echo "   Зарегистрируйтесь на https://grafana.com/signup"
echo "   Получите API ключ и обновите config/promtail-config.yaml"
echo ""
echo "6. Проверьте работу сервисов:"
echo "   curl http://localhost:3100/ready  # Loki"
echo "   curl http://localhost:3000/api/health  # Grafana"
echo "   sudo fail2ban-client status  # Fail2ban"
echo ""
echo "7. Доступ к Grafana:"
echo "   URL: http://$(hostname -I | awk '{print $1}'):3000"
echo "   Login: admin"
echo "   Password: из переменной GRAFANA_PASSWORD в .env"
echo ""
echo "8. Настройте cron задачи:"
echo "   crontab -e"
echo "   # Добавьте задачи из SECURITY-IMPLEMENTATION-GUIDE.md"
echo ""
echo "=========================================="
echo "Документация: SECURITY-IMPLEMENTATION-GUIDE.md"
echo "=========================================="
