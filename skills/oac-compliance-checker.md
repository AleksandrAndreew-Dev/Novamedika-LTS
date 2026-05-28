# Skill: OAC Compliance Checker

## When to use this skill:
- Adding new API endpoints
- Modifying user data handling
- Changing authentication/authorization
- Working with personal data fields
- Implementing new features that process user data

## Checklist for OAC Class 3-in Compliance:

### 1. Authentication & Authorization
- [ ] Endpoint requires JWT authentication?
- [ ] Role-based access control implemented (user/pharmacist/admin)?
- [ ] Check `backend/src/auth/` for existing patterns

### 2. Data Encryption
- [ ] Personal data fields encrypted at rest?
- [ ] Check `oac/docs/10-encryption-policy.md` for requirements
- [ ] Verify encryption in `backend/src/db/models*.py`
- [ ] Reference: `oac/guides/ENCRYPTION-IMPLEMENTATION-GUIDE.md`

### 3. Audit Logging
- [ ] Action logged in audit_logs table?
- [ ] Check `backend/src/middleware/` for logging patterns
- [ ] Required for: login, data access, data modification, deletion

### 4. User Consent
- [ ] User consent obtained for data processing?
- [ ] Check `oac/docs/04-privacy-policy.md`
- [ ] Consent checkboxes in frontend?
- [ ] Reference: `oac/guides/CONSENT-CHECKBOXES-IMPLEMENTATION.md`

### 5. Cross-Border Transfer
- [ ] Does data leave Belarus? (Telegram = YES!)
- [ ] Check `oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md`
- [ ] User informed about cross-border transfer?
- [ ] Explicit consent for cross-border transfer?

### 6. Data Rights
- [ ] Can user access their data?
- [ ] Can user modify their data?
- [ ] Can user delete their data?
- [ ] Can user export their data?
- [ ] Check existing endpoints in `backend/src/routers/users.py`

### 7. Documentation Updates
- [ ] Update relevant OAC documents if architecture changed?
- [ ] Check `oac/docs/14-personal-data-processing-architecture.md`
- [ ] Update `oac/audits/` if significant changes

## Quick Commands:
```bash
# Check compliance
py oac/check_normative_docs.py

# View encryption status
bash agent/diagnostics.sh db  # Check encrypted fields

# Review audit logs
bash agent/diagnostics.sh backend | grep -i "audit"
```

## Common Patterns:

### Adding new endpoint with personal data:
```python
# 1. Add route with auth dependency
@router.post("/endpoint")
async def create_something(
    data: DataSchema,
    current_user: User = Depends(get_current_active_user),  # Auth required
    db: Session = Depends(get_db)
):
    # 2. Log action
    audit_log = AuditLog(
        user_id=current_user.id,
        action="CREATE_SOMETHING",
        details=f"Created something for user {current_user.id}"
    )
    db.add(audit_log)
    
    # 3. Process with encryption if personal data
    # ... implementation
    
    db.commit()
    return {"status": "success"}
```

### Frontend consent checkbox:
```jsx
<input 
  type="checkbox" 
  checked={consentGiven}
  onChange={(e) => setConsentGiven(e.target.checked)}
/>
<label>I agree to personal data processing</label>
```

## Red Flags (Stop and Review):
- ❌ Storing personal data without encryption
- ❌ No audit log for sensitive operations
- ❌ Missing role checks on admin endpoints
- ❌ No user consent mechanism
- ❌ Cross-border transfer without explicit consent
- ❌ No way for users to delete their data

## Resources:
- `oac/docs/` - All 13 compliance documents
- `oac/checklist/checklist.md` - Detailed checklist
- `.ai-rules.md` - AI agent rules (always follow!)
