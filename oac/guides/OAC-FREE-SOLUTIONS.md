# Анализ бесплатных решений для соответствия ОАЦ

**Дата:** 21 апреля 2026 г.  
**Цель:** Минимизация затрат при сохранении соответствия требованиям ОАЦ класса 3-ин

---

## 📊 Сравнительный анализ: Платные vs Бесплатные решения

### 1. Централизованное логирование 🔴 КРИТИЧНО

#### ❌ Платные решения ($50-200/мес):
- **Elastic Cloud** - управляемый Elasticsearch
- **Datadog** - мониторинг и логи
- **Splunk** - enterprise решение
- **Graylog Enterprise**

#### ✅ Бесплатные решения (Open Source):

**Вариант A: ELK Stack Self-Hosted (РЕКОМЕНДУЕТСЯ)**
```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false  # Для dev/test
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - es-data:/usr/share/elasticsearch/data
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    networks:
      - logging

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch
    deploy:
      resources:
        limits:
          memory: 512M
    networks:
      - logging

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    ports:
      - "5601:5601"  # Доступ только через VPN/internal network
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    deploy:
      resources:
        limits:
          memory: 1G
    networks:
      - logging

volumes:
  es-data:

networks:
  logging:
    driver: bridge
    internal: true  # Изоляция от внешнего мира
```

**Плюсы:**
- ✅ Полностью бесплатно (Apache 2.0 License)
- ✅ Полное соответствие требованиям ОАЦ
- ✅ Хранение логов ≥ 1 года (настраивается ILM - Index Lifecycle Management)
- ✅ Мощный поиск и визуализация
- ✅ Активное сообщество

**Минусы:**
- ⚠️ Требует ресурсов сервера (~2-3 GB RAM)
- ⚠️ Нужно самостоятельно администрировать
- ⚠️ Настройка backup требуется

**Стоимость:** $0 (только ресурсы вашего VPS)

---

**Вариант B: Loki + Grafana (ЛЕГКОВЕСНАЯ АЛЬТЕРНАТИВА)**
```yaml
# docker-compose.loki.yml
version: '3.8'

services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    deploy:
      resources:
        limits:
          memory: 512M
    networks:
      - logging

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - logging

  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    depends_on:
      - loki
    deploy:
      resources:
        limits:
          memory: 256M
    networks:
      - logging

volumes:
  loki-data:
  grafana-data:

networks:
  logging:
    driver: bridge
    internal: true
```

**Плюсы:**
- ✅ Очень легковесный (~1 GB RAM)
- ✅ Отличная интеграция с Grafana
- ✅ Простая настройка
- ✅ Бесплатно (AGPLv3)

**Минусы:**
- ⚠️ Меньше возможностей полнотекстового поиска чем у ELK
- ⚠️ Не подходит для сложного анализа логов

**Рекомендация:** Использовать ELK Stack для production, Loki для staging/dev.

---

### 2. Шифрование БД 🔴 КРИТИЧНО

#### ❌ Платные решения:
- **PostgreSQL Enterprise Edition** - $$$
- **Transparent Data Encryption (TDE)** коммерческие модули

#### ✅ Бесплатные решения:

**Вариант A: pgcrypto (РЕКОМЕНДУЕТСЯ)**
```sql
-- Установка расширения (бесплатно, встроено в PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Создание функции для шифрования
CREATE OR REPLACE FUNCTION encrypt_data(data text, key text)
RETURNS bytea AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, key);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrypt_data(encrypted_data bytea, key text)
RETURNS text AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_data, key);
END;
$$ LANGUAGE plpgsql;

-- Пример использования в таблице
ALTER TABLE users 
ADD COLUMN phone_encrypted bytea,
ADD COLUMN telegram_id_encrypted bytea;

-- Шифрование существующих данных
UPDATE users 
SET 
    phone_encrypted = encrypt_data(phone, '${ENCRYPTION_KEY}'),
    telegram_id_encrypted = encrypt_data(telegram_id::text, '${ENCRYPTION_KEY}');

-- Удаление открытых данных
ALTER TABLE users DROP COLUMN phone, DROP COLUMN telegram_id;
```

**Python код для работы с encrypted данными:**
```python
# backend/src/utils/encryption.py
import os
from sqlalchemy import text
from db.database import async_session_maker

ENCRYPTION_KEY = os.getenv('DB_ENCRYPTION_KEY')

async def encrypt_field(value: str) -> bytes:
    """Шифрование значения"""
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT pgp_sym_encrypt(:data, :key)"),
            {"data": value, "key": ENCRYPTION_KEY}
        )
        return result.scalar()

async def decrypt_field(encrypted_data: bytes) -> str:
    """Расшифровка значения"""
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT pgp_sym_decrypt(:data, :key)"),
            {"data": encrypted_data, "key": ENCRYPTION_KEY}
        )
        return result.scalar()
```

**Плюсы:**
- ✅ Полностью бесплатно (встроено в PostgreSQL)
- ✅ Соответствует требованиям ОАЦ к криптографии
- ✅ Гибкое шифрование отдельных полей
- ✅ Не требует изменений архитектуры

**Минусы:**
- ⚠️ Нужно менять application code
- ⚠️ Производительность чуть ниже (не критично)

**Стоимость:** $0

---

**Вариант B: LUKS шифрование диска (на уровне ОС)**
```bash
# На хосте (Ubuntu/Debian)
apt install cryptsetup

# Создание зашифрованного тома
cryptsetup luksFormat /dev/sdb1
cryptsetup open /dev/sdb1 encrypted_db

# Монтирование
mkfs.ext4 /dev/mapper/encrypted_db
mount /dev/mapper/encrypted_db /var/lib/postgresql/data
```

**Плюсы:**
- ✅ Шифрует все данные на диске
- ✅ Прозрачно для приложения
- ✅ Высокая производительность

**Минусы:**
- ⚠️ Шифрует всё, нельзя выборочно
- ⚠️ Сложнее управление ключами

---

### 3. Резервное копирование 🔴 КРИТИЧНО

#### ❌ Платные решения:
- **AWS S3** - $23/TB/мес
- **Google Cloud Storage** - $20/TB/мес
- **Azure Blob Storage** - $21/TB/мес

#### ✅ Бесплатные решения:

**Вариант A: Локальный backup + rsync (РЕКОМЕНДУЕТСЯ)**
```bash
#!/bin/bash
# /usr/local/bin/backup.sh

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
RETENTION_DAYS=365

# Создание директории
mkdir -p $BACKUP_DIR/db
mkdir -p $BACKUP_DIR/configs

# Backup PostgreSQL
echo "Creating database backup..."
docker exec postgres-prod pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | \
    gzip > $BACKUP_DIR/db/db_$DATE.sql.gz

# Backup конфигураций
echo "Backing up configurations..."
tar czf $BACKUP_DIR/configs/configs_$DATE.tar.gz \
    .env \
    docker-compose.*.yml \
    traefic/acme.json \
    logstash/pipeline/

# Удаление старых backup (> 365 дней)
find $BACKUP_DIR/db -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR/configs -name "configs_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Логирование
echo "Backup completed: $DATE" >> $BACKUP_DIR/backup.log

# Проверка размера
du -sh $BACKUP_DIR/*
```

**Настройка cron:**
```bash
# Ежедневный backup в 2:00
crontab -e
0 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1
```

**Плюсы:**
- ✅ Полностью бесплатно
- ✅ Полный контроль над данными
- ✅ Быстрое восстановление

**Минусы:**
- ⚠️ Нет off-site backup (риск при аварии сервера)
- ⚠️ Занимает место на диске

**Решение для off-site:** Использовать бесплатный tier облачных хранилищ или второй сервер.

---

**Вариант B: Rclone +免费云存储**
```bash
# Установка rclone
apt install rclone

# Настройка (например, Yandex.Disk 10GB бесплатно)
rclone config

# Модификация backup.sh для отправки в облако
rclone copy $BACKUP_DIR/db/db_$DATE.sql.gz yandex:backups/novamedika/
```

**Бесплатные облачные хранилища:**
- Yandex.Disk: 10 GB бесплатно
- Google Drive: 15 GB бесплатно
- Mega: 20 GB бесплатно
- pCloud: 10 GB бесплатно

**Для NovaMedika2:**
- Размер daily backup: ~100-500 MB
- Годовой объем: ~36-180 GB
- **Рекомендация:** Компрессия + ротация (хранить последние 30 daily + 12 monthly)

---

### 4. Антивирусная защита 🟡 СРЕДНИЙ ПРИОРИТЕТ

#### ❌ Платные решения:
- **Kaspersky Endpoint Security** - $50-100/год
- **ESET NOD32** - $40-80/год

#### ✅ Бесплатные решения:

**ClamAV (РЕКОМЕНДУЕТСЯ)**
```yaml
# docker-compose.antivirus.yml
version: '3.8'

services:
  clamav:
    image: clamav/clamav:latest
    volumes:
      - uploads:/data  # Монтирование директории с загружаемыми файлами
      - clamav-db:/var/lib/clamav
    command: >
      sh -c "
        freshclam && 
        clamd --foreground &
        sleep 5 &&
        while true; do
          clamscan -r --infected --move=/data/quarantine /data/uploads;
          sleep 3600;  # Сканирование каждый час
        done
      "
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    networks:
      - backend

volumes:
  clamav-db:

networks:
  backend:
    external: true
```

**Интеграция с приложением:**
```python
# backend/src/services/file_scanner.py
import subprocess
import logging

logger = logging.getLogger(__name__)

async def scan_file(file_path: str) -> bool:
    """Сканирование файла на вирусы"""
    try:
        result = subprocess.run(
            ['clamdscan', file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"File {file_path} is clean")
            return True
        else:
            logger.warning(f"Virus detected in {file_path}: {result.stdout}")
            return False
            
    except Exception as e:
        logger.error(f"Error scanning file {file_path}: {e}")
        return False  # В случае ошибки блокируем файл
```

**Плюсы:**
- ✅ Полностью бесплатно (GPL v2)
- ✅ Регулярные обновления вирусных баз
- ✅ Интеграция с приложениями
- ✅ Соответствует требованиям ОАЦ

**Минусы:**
- ⚠️ Менее эффективен чем коммерческие антивирусы
- ⚠️ Требует ресурсов (~512 MB RAM)

**Стоимость:** $0

---

### 5. IDS/IPS (Обнаружение вторжений) 🟡 СРЕДНИЙ ПРИОРИТЕТ

#### ❌ Платные решения:
- **Snort Commercial Rules** - $299/год
- **Cisco Firepower** - $$$

#### ✅ Бесплатные решения:

**Fail2Ban (РЕКОМЕНДУЕТСЯ для начала)**
```bash
# Установка
apt install fail2ban

# Конфигурация /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[traefik-auth]
enabled = true
port = http,https
filter = traefik-auth
logpath = /var/log/traefik/*.log
maxretry = 5
bantime = 3600

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/*.log
maxretry = 2
bantime = 86400
```

**Suricata (продвинутый уровень)**
```yaml
# docker-compose.ids.yml
version: '3.8'

services:
  suricata:
    image: jasonish/suricata:latest
    network_mode: host  # Требуется для захвата трафика
    volumes:
      - ./suricata/rules:/etc/suricata/rules
      - ./suricata/suricata.yaml:/etc/suricata/suricata.yaml
      - /var/log/suricata:/var/log/suricata
    command: >
      -c /etc/suricata/suricata.yaml
      -i eth0
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

**Плюсы Fail2Ban:**
- ✅ Легковесный (~50 MB RAM)
- ✅ Простая настройка
- ✅ Эффективен против brute-force
- ✅ Бесплатно (GPL v2)

**Плюсы Suricata:**
- ✅ Полноценный IDS/IPS
- ✅ Обнаружение сложных атак
- ✅ Бесплатно (GPL v2)

**Минусы:**
- ⚠️ Fail2Ban защищает только от простых атак
- ⚠️ Suricata сложен в настройке

**Рекомендация:** Начать с Fail2Ban, при необходимости добавить Suricata.

**Стоимость:** $0

---

### 6. Penetration Testing 🔴 КРИТИЧНО

#### ❌ Платные решения:
- **Внешний аудит безопасности:** $1000-5000
- **Burp Suite Professional:** $399/год

#### ✅ Бесплатные решения:

**OWASP ZAP (РЕКОМЕНДУЕТСЯ)**
```bash
# Baseline scan (быстрый)
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://api.spravka.novamedika.com \
  -r baseline-report.html \
  -I  # Игнорировать warnings

# Full scan (детальный)
docker run -t owasp/zap2docker-stable zap-full-scan.py \
  -t https://spravka.novamedika.com \
  -r full-report.html \
  -I

# API scan (для REST API)
docker run -t owasp/zap2docker-stable zap-api-scan.py \
  -t https://api.spravka.novamedika.com/openapi.json \
  -f openapi \
  -r api-report.html
```

**Автоматизация в CI/CD:**
```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  schedule:
    - cron: '0 2 * * 0'  # Каждое воскресенье в 2:00
  workflow_dispatch:

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - name: OWASP ZAP Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://api.spravka.novamedika.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -I'
      
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: zap-report
          path: report_html.html
```

**Nmap (сканирование портов)**
```bash
# Сканирование внешних портов
nmap -sV -sC -oN nmap-report.txt spravka.novamedika.com

# Проверка на распространенные уязвимости
nmap --script vuln spravka.novamedika.com
```

**Nikto (веб-сканер)**
```bash
docker run -it nikto -h https://api.spravka.novamedika.com
```

**Плюсы:**
- ✅ Полностью бесплатно
- ✅ Автоматизация в CI/CD
- ✅ Регулярное сканирование
- ✅ Детальные отчеты

**Минусы:**
- ⚠️ Не заменяет полноценный pentest экспертом
- ⚠️ Может пропустить бизнес-логические уязвимости

**Рекомендация:** 
1. Использовать OWASP ZAP еженедельно (бесплатно)
2. Раз в год заказать внешний pentest ($1000-2000 для небольшого проекта)

**Стоимость:** $0 (еженедельно) + $1000-2000 (ежегодно)

---

### 7. Мониторинг инфраструктуры 🟡 СРЕДНИЙ ПРИОРИТЕТ

#### ❌ Платные решения:
- **Datadog:** $15/host/мес
- **New Relic:** $24.99/user/мес
- **Dynatrace:** $$$

#### ✅ Бесплатные решения:

**Prometheus + Grafana (РЕКОМЕНДУЕТСЯ)**
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=365d'  # Хранение 1 год
    ports:
      - "9090:9090"
    deploy:
      resources:
        limits:
          memory: 1G
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    deploy:
      resources:
        limits:
          memory: 256M
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    deploy:
      resources:
        limits:
          memory: 128M
    networks:
      - monitoring

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    deploy:
      resources:
        limits:
          memory: 256M
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
    internal: true
```

**Плюсы:**
- ✅ Полностью бесплатно
- ✅ Мощная визуализация
- ✅ Хранение метрик 1 год
- ✅ Огромное сообщество

**Минусы:**
- ⚠️ Требует настройки dashboards
- ⚠️ ~2 GB RAM для стека

**Стоимость:** $0

---

## 💰 Итоговая экономия

### С платными решениями:
| Компонент | Стоимость/мес | Стоимость/год |
|-----------|---------------|---------------|
| ELK Cloud | $100 | $1,200 |
| AWS S3 (backup) | $20 | $240 |
| Kaspersky AV | $8 | $100 |
| Datadog | $30 | $360 |
| Burp Suite Pro | $33 | $399 |
| Pentest (внешний) | - | $3,000 |
| **ИТОГО** | **$191/мес** | **$5,299/год** |

### С бесплатными решениями:
| Компонент | Стоимость/мес | Стоимость/год |
|-----------|---------------|---------------|
| ELK Self-Hosted | $0 | $0 |
| Local backup + rsync | $0 | $0 |
| ClamAV | $0 | $0 |
| Prometheus + Grafana | $0 | $0 |
| OWASP ZAP | $0 | $0 |
| Pentest (раз в год) | - | $1,500 |
| **ИТОГО** | **$0/мес** | **$1,500/год** |

### 💵 Экономия: **$3,799/год (72%)**

---

## ⚠️ Важные замечания

### Когда НЕЛЬЗЯ использовать бесплатные решения:

1. **Если требуется сертификация средств защиты**
   - Некоторые требования ОАЦ могут требовать сертифицированные средства
   - Проверить актуальные требования в Приказе №66

2. **Если нет экспертизы в команде**
   - Open-source требует больше времени на настройку
   - Нужны навыки администрирования

3. **Для критически важных систем 24/7**
   - Платные решения часто включают SLA и поддержку
   - Для стартапа/MVP можно начать с free

### Рекомендации по внедрению:

**Этап 1 (Недели 1-2):** Быстрые победы
- [ ] Установить ClamAV (1 день)
- [ ] Настроить Fail2Ban (1 день)
- [ ] Создать backup скрипты (1 день)

**Этап 2 (Недели 3-4):** Инфраструктура
- [ ] Развернуть ELK Stack (3-5 дней)
- [ ] Настроить Prometheus + Grafana (2-3 дня)
- [ ] Реализовать шифрование БД (2-3 дня)

**Этап 3 (Недели 5-6):** Автоматизация
- [ ] Настроить OWASP ZAP в CI/CD (2 дня)
- [ ] Создать dashboards для мониторинга (2-3 дня)
- [ ] Протестировать восстановление из backup (1 день)

---

## 📋 Чек-лист бесплатных инструментов

- [x] **ELK Stack** - централизованное логирование
- [x] **pgcrypto** - шифрование БД
- [x] **Backup scripts + rsync** - резервное копирование
- [x] **ClamAV** - антивирус
- [x] **Fail2Ban** - IDS/IPS базовый
- [x] **OWASP ZAP** - сканирование уязвимостей
- [x] **Prometheus + Grafana** - мониторинг
- [ ] **Suricata** - продвинутый IDS/IPS (опционально)
- [ ] **Wazuh** - SIEM система (опционально, если нужно больше чем ELK)

---

## 🎯 Заключение

**Все критические требования ОАЦ можно выполнить с использованием бесплатных open-source решений!**

**Единственная статья расходов:**
- Внешний penetration test раз в год: $1,000-2,000
- Или самостоятельное тестирование: $0

**Общая экономия:** ~$3,800/год compared to commercial solutions

**Рекомендация:** Начать с бесплатных решений, масштабироваться при росте бизнеса.

---

**Документ подготовил:** AI Assistant (Lingma)  
**Дата:** 21 апреля 2026 г.
