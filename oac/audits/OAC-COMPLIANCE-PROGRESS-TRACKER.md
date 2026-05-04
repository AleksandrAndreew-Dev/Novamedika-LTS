# OAC Compliance Progress Tracker

**Project:** Novamedika2  
**Class:** 3-in  
**Start Date:** May 4, 2026  
**Target Completion:** July 6, 2026 (9 weeks)  
**Last Updated:** May 4, 2026

---

## 📊 Overall Progress

```
Overall Readiness: ████████████░░░░░░░░ 65%

Critical Gaps:     ███░░░░░░░░░░░░░░░░░ 15% (0/4 completed)
High Priority:     ██░░░░░░░░░░░░░░░░░░ 10% (0/3 completed)
Documentation:     ████████████████████ 100% (13/13 complete)
Technical:         ████████░░░░░░░░░░░░ 40% (estimated)
Administrative:    █░░░░░░░░░░░░░░░░░░░  5% (estimated)
```

---

## 🔴 Critical Gaps Progress

### Gap 1: Database Encryption Activation
**Status:** ⚠️ IN PROGRESS (Code ready, activation pending)  
**Priority:** CRITICAL  
**Owner:** [Assign]  
**Deadline:** Week 2 (May 18, 2026)

```
Progress: ██████████░░░░░░░░░░ 50%

Tasks:
✅ Code models updated with encrypted fields
✅ Migration created (3b81fefeff37)
✅ Encryption utilities implemented (utils/encryption.py)
⏳ Install pgcrypto extension in PostgreSQL
⏳ Generate and configure ENCRYPTION_KEY
⏳ Execute Alembic migration on production
⏳ Verify encryption working
⏳ Update all API endpoints to use encrypted fields
```

**Blockers:** None  
**Next Action:** Install pgcrypto extension

---

### Gap 2: Centralized Logging
**Status:** ❌ NOT STARTED  
**Priority:** CRITICAL  
**Owner:** [Assign]  
**Deadline:** Week 2 (May 18, 2026)

```
Progress: ░░░░░░░░░░░░░░░░░░░░ 0%

Tasks:
⏳ Deploy ELK Stack or Graylog
⏳ Configure Docker logging driver (GELF)
⏳ Create Logstash configuration
⏳ Set retention policy (365 days)
⏳ Create Kibana dashboard for security monitoring
⏳ Configure alerts for security events
```

**Blockers:** Budget approval needed ($50-100/month)  
**Next Action:** Decide between ELK vs Graylog, get budget approval

---

### Gap 3: Penetration Testing
**Status:** ❌ NOT STARTED  
**Priority:** CRITICAL  
**Owner:** [Assign]  
**Deadline:** Week 4 (June 1, 2026)

```
Progress: ░░░░░░░░░░░░░░░░░░░░ 0%

Tasks:
⏳ Choose approach: OWASP ZAP (free) or External audit ($1000-5000)
⏳ Run OWASP ZAP scan OR engage external auditor
⏳ Review scan results
⏳ Fix Critical vulnerabilities
⏳ Fix High vulnerabilities
⏳ Retest after fixes
⏳ Generate final pentest report
```

**Blockers:** None  
**Next Action:** Run initial OWASP ZAP scan using `scripts/run-zap-scan.sh`

---

### Gap 4: Security System Certification
**Status:** ❌ NOT STARTED  
**Priority:** CRITICAL  
**Owner:** [Assign]  
**Deadline:** Week 9 (July 6, 2026)

```
Progress: ░░░░░░░░░░░░░░░░░░░░ 0%

Tasks:
⏳ Form certification commission (minimum 3 members)
⏳ Issue management order appointing commission
⏳ Appoint personal data protection officer
⏳ Create certification test program and methodology
⏳ Prepare job descriptions
⏳ Create incident log template
⏳ Conduct certification tests
⏳ Prepare test protocol
⏳ Prepare technical report
⏳ Sign commissioning act
⏳ Obtain certificate of conformity
⏳ Submit information to OAC (within 10 days)
```

**Blockers:** Depends on Gaps 1-3 completion  
**Next Action:** Identify potential commission members

---

## 🟡 High Priority Tasks Progress

### Task 1: Backup Automation
**Status:** ⚠️ PARTIAL (Script exists, not automated)  
**Priority:** HIGH  
**Owner:** [Assign]  
**Deadline:** Week 2 (May 18, 2026)

```
Progress: █████░░░░░░░░░░░░░░░ 25%

Tasks:
✅ Backup script created (scripts/backup.sh)
✅ Retention policy configured (365 days)
✅ Integrity check implemented
⏳ Setup cron job for daily execution
⏳ Test backup restoration
⏳ Configure offsite storage (S3)
```

**Blockers:** None  
**Next Action:** Setup cron job and test restoration

---

### Task 2: Security Tools Installation
**Status:** ❌ NOT STARTED  
**Priority:** MEDIUM  
**Owner:** [Assign]  
**Deadline:** Week 4 (June 1, 2026)

```
Progress: ░░░░░░░░░░░░░░░░░░░░ 0%

Tasks:
⏳ Install ClamAV antivirus
⏳ Configure daily scanning schedule
⏳ Install Fail2Ban IDS/IPS
⏳ Configure jail rules for SSH, HTTP
⏳ Configure session timeout (15 min)
```

**Blockers:** None  
**Next Action:** Install ClamAV and Fail2Ban

---

### Task 3: Registry Registration
**Status:** ❌ NOT STARTED  
**Priority:** HIGH  
**Owner:** [Assign]  
**Deadline:** Week 6 (June 15, 2026)

```
Progress: ░░░░░░░░░░░░░░░░░░░░ 0%

Tasks:
⏳ Register in NCPDP Operators Registry
⏳ Submit IS information to OAC (after certification)
⏳ Submit training information to NCPDP (by Nov 15)
```

**Blockers:** Requires certificate of conformity for OAC submission  
**Next Action:** Start NCPDP registration process (can be done early)

---

## 📋 Documentation Status

All 13 required documents are **COMPLETE**:

| # | Document | File | Status |
|---|----------|------|--------|
| 1 | Акт отнесения к классу 3-ин | `oac/docs/01-act-class-3in.md` | ✅ DONE |
| 2 | Структурная схема | `oac/docs/02-structural-schema.md` | ✅ DONE |
| 3 | Логическая схема | `oac/docs/03-logical-schema.md` | ✅ DONE |
| 4 | Политика конфиденциальности | `oac/docs/04-privacy-policy.md` | ✅ DONE |
| 5 | Политика ИБ | `oac/docs/05-infosec-policy.md` | ✅ DONE |
| 6 | Техническое задание | `oac/docs/06-tech-spec.md` | ✅ DONE |
| 7 | Регламент мониторинга ИБ | `oac/docs/07-ib-monitoring-reglament.md` | ✅ DONE |
| 8 | Регламент резервного копирования | `oac/docs/08-backup-reglament.md` | ✅ DONE |
| 9 | Регламент хранения данных | `oac/docs/09-data-retention-reglament.md` | ✅ DONE |
| 10 | Политика шифрования | `oac/docs/10-encryption-policy.md` | ✅ DONE |
| 11 | Регламент антивирусной защиты | `oac/docs/11-antivirus-reglament.md` | ✅ DONE |
| 12 | Регламент IDS/IPS | `oac/docs/12-ids-ips-reglament.md` | ✅ DONE |
| 13 | Регламент сканирования уязвимостей | `oac/docs/13-vuln-scan-reglament.md` | ✅ DONE |

**Additional Documents Needed:**
- [ ] Program and methodology for certification tests
- [ ] Test protocol (after testing)
- [ ] Technical report (after testing)
- [ ] Certificate of conformity (after certification)
- [ ] Incident log template
- [ ] Job descriptions for responsible persons
- [ ] Management orders (commission appointment, security officer)

---

## 🗓️ Weekly Milestones

### Week 1 (May 4-10, 2026)
**Goal:** Activate database encryption

- [ ] Install pgcrypto extension
- [ ] Generate ENCRYPTION_KEY
- [ ] Execute Alembic migration
- [ ] Verify encryption working
- [ ] Setup cron job for backups
- [ ] Test backup restoration

**Expected Progress:** 65% → 70%

---

### Week 2 (May 11-17, 2026)
**Goal:** Deploy centralized logging

- [ ] Deploy ELK Stack
- [ ] Configure Docker logging
- [ ] Set retention policy
- [ ] Create Kibana dashboard
- [ ] Configure S3 offsite backup

**Expected Progress:** 70% → 75%

---

### Week 3 (May 18-24, 2026)
**Goal:** Begin penetration testing

- [ ] Run OWASP ZAP scan
- [ ] Review results
- [ ] Start fixing Critical vulnerabilities
- [ ] Install ClamAV
- [ ] Install Fail2Ban

**Expected Progress:** 75% → 80%

---

### Week 4 (May 25-31, 2026)
**Goal:** Complete pentest and security tools

- [ ] Fix all Critical vulnerabilities
- [ ] Fix all High vulnerabilities
- [ ] Retest after fixes
- [ ] Generate pentest report
- [ ] Configure session timeout
- [ ] Configure ClamAV daily scans

**Expected Progress:** 80% → 85%

---

### Week 5 (June 1-7, 2026)
**Goal:** Prepare for certification

- [ ] Form certification commission
- [ ] Issue management orders
- [ ] Appoint security officer
- [ ] Create test program and methodology
- [ ] Prepare job descriptions
- [ ] Create incident log template

**Expected Progress:** 85% → 88%

---

### Week 6 (June 8-14, 2026)
**Goal:** Register in official registries

- [ ] Register in NCPDP Operators Registry
- [ ] Finalize all documentation
- [ ] Review all technical measures
- [ ] Conduct internal pre-audit

**Expected Progress:** 88% → 90%

---

### Week 7 (June 15-21, 2026)
**Goal:** Conduct certification tests

- [ ] Execute test program
- [ ] Verify all technical measures
- [ ] Document test results
- [ ] Prepare test protocol
- [ ] Prepare technical report

**Expected Progress:** 90% → 95%

---

### Week 8 (June 22-28, 2026)
**Goal:** Obtain certificate

- [ ] Commission review of test results
- [ ] Sign commissioning act
- [ ] Issue certificate of conformity
- [ ] Address any remaining issues

**Expected Progress:** 95% → 98%

---

### Week 9 (June 29 - July 6, 2026)
**Goal:** Finalize OAC compliance

- [ ] Submit IS information to OAC
- [ ] Submit copies of certificate, reports
- [ ] Complete all administrative tasks
- [ ] Final compliance review

**Expected Progress:** 98% → 100% ✅

---

## 📈 Progress History

| Date | Overall % | Key Achievements | Issues |
|------|-----------|------------------|--------|
| May 4, 2026 | 65% | Audit completed, action plan created | - |
| | | | |
| | | | |
| | | | |

---

## 🎯 Key Metrics

### Budget Tracking
| Item | Budget | Spent | Remaining |
|------|--------|-------|-----------|
| Pentest | $0-5000 | $0 | $0-5000 |
| Specialist work | $8000-12000 | $0 | $8000-12000 |
| ELK hosting | $50-100/mo | $0 | $50-100/mo |
| S3 storage | $10-20/mo | $0 | $10-20/mo |
| Training | $200-500 | $0 | $200-500 |
| **Total (Year 1)** | **$8920-19180** | **$0** | **$8920-19180** |

### Time Tracking
| Phase | Planned | Actual | Variance |
|-------|---------|--------|----------|
| Weeks 1-2 | 10 days | - | - |
| Weeks 3-4 | 10 days | - | - |
| Weeks 5-6 | 10 days | - | - |
| Weeks 7-8 | 10 days | - | - |
| Week 9 | 5 days | - | - |
| **Total** | **45 days** | **-** | **-** |

---

## 🚨 Risks & Mitigation Status

| Risk | Probability | Impact | Mitigation Status |
|------|------------|---------|-------------------|
| Server outside Belarus | Medium | High | ⏳ Pending server location verification |
| Insufficient pentest budget | High | Medium | ⏳ Awaiting decision on OWASP ZAP vs external |
| Lack of OAC expertise | Medium | High | ⏳ Consider hiring consultant |
| OAC requirement changes | Low | Medium | ✅ Monitoring oac.gov.by |
| Registry registration overdue | High | High | ⏳ Should start immediately |
| Personal data breach | Medium | Critical | ⏳ Will be mitigated after Gap 1-3 closure |

---

## 👥 Team Assignments

| Role | Name | Contact | Responsibilities |
|------|------|---------|------------------|
| Project Manager | [TBD] | | Overall coordination, budget management |
| Technical Lead | [TBD] | | Database encryption, ELK deployment |
| Security Officer | [TBD] | | Pentest coordination, compliance oversight |
| DevOps Engineer | [TBD] | | Infrastructure setup, backup automation |
| Legal Advisor | [TBD] | | Regulatory compliance, document review |

---

## 📞 Communication Plan

### Weekly Standup
- **When:** Every Monday, 10:00 AM
- **Duration:** 30 minutes
- **Agenda:**
  1. Progress since last meeting
  2. Blockers and issues
  3. Plan for current week
  4. Budget updates

### Monthly Review
- **When:** Last Friday of each month
- **Duration:** 1 hour
- **Attendees:** All team members + management
- **Agenda:**
  1. Overall progress review
  2. Budget vs actual
  3. Risk assessment update
  4. Adjust timeline if needed

### Emergency Contact
For critical security incidents:
- **Security Officer:** [Phone/Email]
- **Technical Lead:** [Phone/Email]
- **Management:** [Phone/Email]

---

## ✅ Definition of Done

A task is considered **DONE** when:

1. ✅ Implementation completed according to specifications
2. ✅ Tested in staging environment
3. ✅ Tested in production environment
4. ✅ Documented in relevant files
5. ✅ Verified by peer review
6. ✅ No regressions introduced
7. ✅ Monitoring/alerting configured (if applicable)

---

## 📝 Notes & Comments

*Use this section for important notes, decisions, or context:*

- **May 4, 2026:** Initial audit completed. Project at 65% readiness. Four critical gaps identified requiring immediate attention.
- 
- 
- 

---

**Template Version:** 1.0  
**Last Updated:** May 4, 2026  
**Next Update:** May 11, 2026 (or upon significant progress)
