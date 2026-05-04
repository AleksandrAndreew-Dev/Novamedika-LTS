# OAC Compliance - Immediate Action Checklist

**Created:** May 4, 2026  
**Based on:** Comprehensive audit report `OAC-COMPLIANCE-AUDIT-2026-05-04.md`  
**Purpose:** Quick reference for critical tasks to achieve OAC certification

---

## 🔴 CRITICAL (Must complete before certification)

### Week 1-2: Database Encryption Activation

- [ ] **Install pgcrypto extension in PostgreSQL**
  ```bash
  docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
  ```

- [ ] **Generate and configure ENCRYPTION_KEY**
  ```bash
  # Generate secure key
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  
  # Add to .env file
  echo "ENCRYPTION_KEY=<generated-key>" >> .env
  ```

- [ ] **Execute Alembic migration**
  ```bash
  cd backend
  alembic upgrade head
  
  # Verify migration applied
  alembic current
  ```

- [ ] **Verify encryption is working**
  ```sql
  -- Check encrypted fields exist
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'qa_users' AND column_name LIKE '%encrypted%';
  
  -- Sample check (should show base64 encoded data)
  SELECT telegram_id_encrypted, phone_encrypted FROM qa_users LIMIT 3;
  ```

- [ ] **Update application code to use encrypted fields**
  - [ ] Verify `User` model methods `set_telegram_id()`, `get_telegram_id()` work correctly
  - [ ] Verify `BookingOrder` model methods `set_customer_phone()`, `get_customer_phone()` work correctly
  - [ ] Check `Pharmacist` model needs similar encryption (if exists)
  - [ ] Test data retrieval in API endpoints

**Estimated time:** 2-3 days  
**Cost:** $0

---

### Week 1-2: Centralized Logging Setup

- [ ] **Deploy ELK Stack or Graylog**

  **Option A: ELK Stack (recommended)**
  ```yaml
  # Add to docker-compose.traefik.prod.yml
  services:
    elasticsearch:
      image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
      environment:
        - discovery.type=single-node
        - ES_JAVA_OPTS=-Xms512m -Xmx512m
      volumes:
        - es_data:/usr/share/elasticsearch/data
      networks:
        - traefik-public
      deploy:
        resources:
          limits:
            memory: 2G

    kibana:
      image: docker.elastic.co/kibana/kibana:8.11.0
      ports:
        - "5601:5601"
      depends_on:
        - elasticsearch
      networks:
        - traefik-public

    logstash:
      image: docker.elastic.co/logstash/logstash:8.11.0
      volumes:
        - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      depends_on:
        - elasticsearch
      networks:
        - traefik-public

  volumes:
    es_data:
  ```

- [ ] **Configure Docker logging driver**
  ```yaml
  # Update each service in docker-compose
  logging:
    driver: gelf
    options:
      gelf-address: "udp://logstash:12201"
      tag: "{{.Name}}"
  ```

- [ ] **Create Logstash configuration**
  ```conf
  # logstash.conf
  input {
    gelf {
      port => 12201
    }
  }

  filter {
    if [container_name] {
      mutate {
        add_field => { "service" => "%{container_name}" }
      }
    }
  }

  output {
    elasticsearch {
      hosts => ["http://elasticsearch:9200"]
      index => "novamedika-logs-%{+YYYY.MM.dd}"
    }
  }
  ```

- [ ] **Configure retention policy (365 days)**
  ```bash
  # Create Elasticsearch ILM policy
  curl -X PUT "http://localhost:9200/_ilm/policy/novamedika-logs-policy" -H 'Content-Type: application/json' -d'
  {
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_age": "30d",
              "max_size": "50gb"
            }
          }
        },
        "delete": {
          "min_age": "365d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'
  ```

- [ ] **Create Kibana dashboard for security monitoring**
  - [ ] Login to Kibana: http://localhost:5601
  - [ ] Create index pattern: `novamedika-logs-*`
  - [ ] Create visualizations:
    - Error rate over time
    - Failed login attempts
    - API response times
    - Container resource usage
  - [ ] Create alerts for:
    - High error rates
    - Multiple failed logins
    - Unusual traffic patterns

**Estimated time:** 3-5 days  
**Cost:** $50-100/month (hosting)

---

### Week 3-4: Penetration Testing

- [ ] **Run OWASP ZAP scan**
  ```bash
  # Using prepared script
  cd scripts
  chmod +x run-zap-scan.sh
  ./run-zap-scan.sh https://api.spravka.novamedika.com
  
  # Or direct Docker command
  docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t https://api.spravka.novamedika.com \
    -r /zap/wrk/zap-report.html \
    -I  # Ignore warnings
  ```

- [ ] **Review scan results**
  - [ ] Identify Critical severity issues
  - [ ] Identify High severity issues
  - [ ] Categorize Medium/Low issues

- [ ] **Fix Critical vulnerabilities**
  - [ ] Document each fix
  - [ ] Retest after fixes

- [ ] **Fix High vulnerabilities**
  - [ ] Document each fix
  - [ ] Retest after fixes

- [ ] **Generate final pentest report**
  ```markdown
  # Penetration Test Report
  
  ## Executive Summary
  - Date: [date]
  - Scope: https://api.spravka.novamedika.com, https://spravka.novamedika.com
  - Tool: OWASP ZAP 2.x
  - Tester: [name]
  
  ## Findings
  ### Critical: [count]
  ### High: [count]
  ### Medium: [count]
  ### Low: [count]
  
  ## Remediation Status
  - All Critical: ✅ Fixed
  - All High: ✅ Fixed
  - Medium: [status]
  - Low: [status]
  
  ## Conclusion
  System is ready for certification / requires additional work
  ```

**Alternative: External Audit**
- [ ] Research certified cybersecurity companies in Belarus
- [ ] Request quotes ($1000-5000)
- [ ] Schedule engagement
- [ ] Provide system access and documentation
- [ ] Receive official report

**Estimated time:** 2-5 days  
**Cost:** $0 (self) or $1000-5000 (external)

---

### Week 5-6: Certification Preparation

- [ ] **Form certification commission**
  - [ ] Minimum 3 members required
  - [ ] Include: IT manager, security officer, external expert (optional)
  - [ ] Issue management order appointing commission
  
  ```markdown
  # ПРИКАЗ № ___
  
  О создании комиссии по аттестации информационной системы
  
  В целях обеспечения защиты персональных данных и приведения 
  информационной системы NovaMedika2 в соответствие с требованиями 
  Приказа ОАЦ №66 от 20.02.2020
  
  ПРИКАЗЫВАЮ:
  
  1. Создать комиссию по аттестации ИС NovaMedika2 в составе:
     - Председатель: [ФИО, должность]
     - Члены комиссии:
       * [ФИО, должность]
       * [ФИО, должность]
  
  2. Комиссии провести аттестационные испытания в срок до [дата]
  
  Руководитель: _________________ / [ФИО] /
  Дата: [дата]
  ```

- [ ] **Appoint personal data protection officer**
  ```markdown
  # ПРИКАЗ № ___
  
  О назначении ответственного за защиту персональных данных
  
  В соответствии с п.3 ст.17 Закона РБ №99-З "О защите персональных данных"
  
  ПРИКАЗЫВАЮ:
  
  1. Назначить ответственным за организацию обработки и защиты 
     персональных данных в ИС NovaMedika2:
     [ФИО, должность]
  
  2. Возложить следующие обязанности:
     - Контроль соблюдения законодательства о ПД
     - Организация обучения работников
     - Рассмотрение обращений субъектов ПД
     - Взаимодействие с ОАЦ и НЦЗПД
  
  3. Контроль исполнения приказа оставляю за собой.
  
  Руководитель: _________________ / [ФИО] /
  Дата: [дата]
  ```

- [ ] **Create certification test program**
  ```markdown
  # Программа аттестационных испытаний ИС NovaMedika2
  
  ## 1. Общие положения
  - Наименование ИС: NovaMedika2
  - Класс ИС: 3-ин
  - Цель аттестации: Подтверждение соответствия требованиям Приказа ОАЦ №66
  
  ## 2. Состав комиссии
  [список членов комиссии]
  
  ## 3. Объекты аттестации
  - Сервер приложений (backend)
  - База данных PostgreSQL
  - Веб-интерфейс (frontend)
  - Telegram бот
  - Сетевая инфраструктура
  
  ## 4. Методика испытаний
  
  ### 4.1 Проверка шифрования данных
  - [ ] Проверить наличие pgcrypto расширения
  - [ ] Убедиться что телефон и telegram_id зашифрованы
  - [ ] Проверить работу методов шифрования/дешифрования
  
  ### 4.2 Проверка аутентификации
  - [ ] Протестировать JWT token generation
  - [ ] Проверить RBAC разграничение доступа
  - [ ] Убедиться что пароли скрыты при вводе
  
  ### 4.3 Проверка логирования
  - [ ] Убедиться что логи собираются централизованно
  - [ ] Проверить хранение логов ≥ 1 года
  - [ ] Проверить мониторинг событий ИБ
  
  ### 4.4 Проверка резервного копирования
  - [ ] Проверить наличие автоматических backup
  - [ ] Выполнить тестовое восстановление
  - [ ] Убедиться что retention policy настроен
  
  ### 4.5 Проверка сетевой безопасности
  - [ ] Убедиться что HTTPS/TLS настроен корректно
  - [ ] Проверить межсетевое экранирование
  - [ ] Проверить изоляцию Docker networks
  
  ## 5. Критерии успешности
  Все проверки раздела 4 должны быть выполнены успешно.
  
  ## 6. Срок проведения испытаний
  [дата начала] - [дата окончания]
  
  Председатель комиссии: _________________ / [ФИО] /
  ```

- [ ] **Prepare job descriptions**
  - [ ] Security officer responsibilities
  - [ ] Database administrator responsibilities
  - [ ] System administrator responsibilities

- [ ] **Create incident log template**
  ```markdown
  # Журнал учёта инцидентов информационной безопасности
  
  | № | Дата/Время | Описание инцидента | Категория | Принятые меры | Ответственный | Статус |
  |---|-----------|-------------------|----------|--------------|--------------|--------|
  | 1 |           |                   |          |              |              |        |
  
  Категории:
  - Несанкционированный доступ
  - Утечка персональных данных
  - Отказ системы защиты
  - Вредоносное ПО
  - Сетевая атака
  - Другое
  ```

**Estimated time:** 3-5 days  
**Cost:** $0 (internal work)

---

## 🟡 HIGH PRIORITY (Should complete soon)

### Backup Automation

- [ ] **Setup cron job for automated backups**
  ```bash
  # Edit crontab
  crontab -e
  
  # Add daily backup at 2:00 AM
  0 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1
  ```

- [ ] **Test backup restoration**
  ```bash
  # Restore from latest backup
  LATEST_BACKUP=$(ls -t /backups/db/*.sql.gz | head -1)
  gunzip -c $LATEST_BACKUP | docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB
  
  # Verify data integrity
  docker exec -it postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT COUNT(*) FROM qa_users;"
  ```

- [ ] **Configure offsite storage (S3)**
  ```bash
  # Install AWS CLI
  pip install awscli
  
  # Configure credentials
  aws configure
  
  # Add to backup.sh
  aws s3 cp $BACKUP_FILE s3://novamedika-backups/db_$DATE.sql.gz
  
  # Test S3 upload
  ./backup.sh
  aws s3 ls s3://novamedika-backups/
  ```

**Estimated time:** 1 day  
**Cost:** $10-20/month (S3 storage)

---

### Security Tools Installation

- [ ] **Install ClamAV (antivirus)**
  ```bash
  sudo apt-get update
  sudo apt-get install -y clamav clamav-daemon
  
  # Update virus database
  sudo freshclam
  
  # Enable and start service
  sudo systemctl enable clamav-daemon
  sudo systemctl start clamav-daemon
  
  # Configure daily scan
  sudo crontab -e
  0 3 * * * clamscan -r /app --log=/var/log/clamav/scan.log --infected
  ```

- [ ] **Install Fail2Ban (IDS/IPS)**
  ```bash
  sudo apt-get install -y fail2ban
  
  # Copy jail configuration
  sudo cp scripts/fail2ban-jail.local /etc/fail2ban/jail.local
  
  # Enable and start service
  sudo systemctl enable fail2ban
  sudo systemctl start fail2ban
  
  # Monitor
  sudo tail -f /var/log/fail2ban.log
  sudo fail2ban-client status
  ```

- [ ] **Configure session timeout**
  ```python
  # Add to backend/src/main.py or middleware file
  @app.middleware("http")
  async def session_timeout_middleware(request: Request, call_next):
      if hasattr(request.state, 'user') and request.state.user.is_authenticated:
          last_activity = request.session.get("last_activity")
          if last_activity:
              inactive_time = (datetime.utcnow() - last_activity).total_seconds()
              if inactive_time > 900:  # 15 minutes
                  # Clear session and redirect to login
                  request.session.clear()
                  return RedirectResponse(url="/login")
          request.session["last_activity"] = datetime.utcnow()
      
      response = await call_next(request)
      return response
  ```

**Estimated time:** 1-2 days  
**Cost:** $0 (open source)

---

## 📋 ADMINISTRATIVE TASKS

### Registry Registration

- [ ] **Register in Personal Data Operators Registry**
  - [ ] Visit: https://register.pdpa.gov.by/
  - [ ] Fill out registration form
  - [ ] Submit required documents:
    - Company registration certificate
    - IS description
    - Privacy policy
    - Contact information
  - [ ] Wait for confirmation (typically 5-10 business days)

- [ ] **Submit IS information to OAC**
  - [ ] Prepare submission package:
    - Certificate of conformity (after certification)
    - Technical report
    - Test protocol
    - IS description
  - [ ] Submit within 10 days after certification
  - [ ] Keep confirmation receipt

- [ ] **Submit training information to NCPDP**
  - [ ] Count employees requiring training
  - [ ] Submit by November 15 annually
  - [ ] Schedule training sessions (once per 3 years for security staff, once per 5 years for PD officers)

**Estimated time:** 2-3 days total  
**Cost:** Varies (training fees may apply)

---

## ✅ VERIFICATION CHECKLIST

Before submitting for certification, verify:

### Technical Measures
- [ ] Database encryption active and verified
- [ ] HTTPS/TLS working on all endpoints
- [ ] JWT authentication functioning
- [ ] RBAC access control tested
- [ ] Centralized logging operational (≥1 year retention)
- [ ] Automated backups running daily
- [ ] Backup restoration tested successfully
- [ ] Session timeout configured (15 min)
- [ ] Antivirus installed and scanning
- [ ] IDS/IPS (Fail2Ban) active
- [ ] Docker resource limits set
- [ ] Non-root containers confirmed

### Documentation
- [ ] All 13 OAC documents present and approved
- [ ] Commission formed and order issued
- [ ] Security officer appointed
- [ ] Job descriptions created
- [ ] Incident log template ready
- [ ] Test program and methodology approved
- [ ] Pentest report completed
- [ ] Privacy policy published on website
- [ ] Privacy policy accessible in Telegram Bot

### Administrative
- [ ] Registered in NCPDP Operators Registry
- [ ] Training schedule established
- [ ] Incident response procedure documented
- [ ] Cross-border transfer assessed (if applicable)

---

## 📊 PROGRESS TRACKING

Use this table to track weekly progress:

| Week | Tasks Completed | Issues Encountered | Next Steps |
|------|----------------|-------------------|------------|
| 1    |                |                   |            |
| 2    |                |                   |            |
| 3    |                |                   |            |
| 4    |                |                   |            |
| 5    |                |                   |            |
| 6    |                |                   |            |
| 7    |                |                   |            |
| 8    |                |                   |            |
| 9    |                |                   |            |

---

## 🆘 SUPPORT RESOURCES

If you encounter issues:

1. **Technical questions:**
   - Review `oac/guides/` directory for implementation guides
   - Check `backend/README.md` for backend setup
   - Consult Docker logs: `docker-compose logs -f [service]`

2. **Compliance questions:**
   - Refer to `origin-docs/` for regulatory requirements
   - Review `oac/docs/` for project-specific policies
   - Contact OAC: https://oac.gov.by/

3. **Legal questions:**
   - Consult IT law specialist
   - Review Law #99-З: `origin-docs/99-3n.md`
   - Contact NCPDP: https://pdpa.gov.by/

---

**Last Updated:** May 4, 2026  
**Next Review:** Weekly during implementation phase  
**Owner:** [Assign responsible person]
