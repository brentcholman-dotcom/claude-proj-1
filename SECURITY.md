# Security Documentation

## Overview
This document outlines the security measures implemented in the Multi-LLM Privacy Chat application and provides guidance for secure deployment.

## Current Security Rating: 8/10 (Production-Ready with Caveats)

---

## Implemented Security Features ✅

### 1. **API Key Protection**
- ✅ **Encrypted Storage**: API keys encrypted using Fernet (AES-256) before session storage
- ✅ **Server-Side Sessions**: Keys never sent to client, stored server-side only
- ✅ **Session Timeout**: 8-hour automatic timeout with configurable lifetime
- ✅ **Secure Cookies**: HTTPOnly, Secure (HTTPS), SameSite=Lax flags

### 2. **Rate Limiting**
- ✅ **API Key Validation**: 5 requests per minute (strict limit)
- ✅ **Query Processing**: 30 requests per minute
- ✅ **Global Limits**: 200 per day, 50 per hour per IP address
- ✅ **Strategy**: Fixed-window with in-memory storage

### 3. **Input Validation**
- ✅ **Query Length**: Maximum 50,000 characters
- ✅ **Character Filtering**: Removes control characters (except newlines/tabs)
- ✅ **Type Validation**: Ensures proper data types
- ✅ **API Key Length**: Maximum 500 characters

### 4. **Security Headers**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains (HTTPS only)
Content-Security-Policy: Restrictive policy for scripts/styles
```

### 5. **CORS Configuration**
- ✅ **Explicit Origins**: Only allows configured origins (no wildcards)
- ✅ **Credentials Control**: Credentials only for API routes
- ✅ **Method Restriction**: Only GET, POST, OPTIONS allowed
- ✅ **Environment-Based**: Configured via ALLOWED_ORIGINS in .env

### 6. **Error Handling**
- ✅ **Sanitized Messages**: Generic errors to prevent information leakage
- ✅ **Detailed Logging**: Full errors logged server-side with IP tracking
- ✅ **No Stack Traces**: Debug mode disabled in production
- ✅ **Graceful Degradation**: Corrupted sessions cleared automatically

### 7. **Security Logging**
- ✅ **Rotating Logs**: 10MB max file size, 10 backup files
- ✅ **IP Tracking**: Client IP logged for all security events
- ✅ **Event Types**: Failed auth, invalid input, rate limits, errors
- ✅ **Location**: `logs/security.log` (gitignored)

### 8. **Privacy Protection**
- ✅ **PII Detection**: Automatic detection of sensitive data
- ✅ **Anonymization**: Queries anonymized when sensitivity > 0.3
- ✅ **Pattern Detection**: SSNs, emails, phones, credit cards
- ✅ **User Control**: Configurable sensitivity thresholds

---

## Critical Security Requirements for Production ⚠️

### 1. **HTTPS/TLS (MANDATORY)**
```nginx
# Nginx configuration example
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. **Environment Configuration**
```bash
# REQUIRED: Generate unique SECRET_KEY
python3 -c 'import secrets; print(secrets.token_hex(32))'

# .env file (NEVER commit to git!)
SECRET_KEY=<your_generated_key>
FLASK_ENV=production
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
SESSION_COOKIE_SECURE=True
```

### 3. **Production WSGI Server**
```bash
# Install gunicorn
pip install gunicorn

# Run with 4 worker processes
gunicorn -w 4 -b 127.0.0.1:5000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  flask_backend:app

# Or use systemd service (recommended)
```

### 4. **Secret Key Management**
- ❌ **NEVER** commit `.env` file to git
- ✅ Use `.env.example` as template
- ✅ Generate unique key per environment
- ✅ Rotate keys if exposed (all sessions invalidated)
- ✅ Use secrets management service in production (AWS Secrets Manager, Vault)

---

## Additional Security Considerations

### Medium Priority

#### 1. **Session Storage (Current: Filesystem)**
**For Production Scale:**
- Consider Redis for session storage
- Enables horizontal scaling across servers
- Automatic expiration and cleanup
- Better performance under load

```python
# Example Redis configuration
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
```

#### 2. **CSRF Protection**
**Current:** SameSite cookies provide basic protection
**Enhancement:** Add CSRF tokens for state-changing operations
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

#### 3. **Dependency Scanning**
```bash
# Install security scanning tools
pip install pip-audit safety

# Scan for vulnerabilities
pip-audit
safety check

# Automate in CI/CD pipeline
```

#### 4. **API Authentication (Optional)**
For public-facing APIs, consider adding:
- API key authentication per user
- JWT tokens for session management
- OAuth2 for third-party integrations

### Low Priority

#### 5. **Monitoring & Alerting**
- Failed authentication attempts
- Rate limit violations
- Unusual traffic patterns
- Error rate spikes

#### 6. **Backup & Recovery**
- Regular backups of session storage
- Disaster recovery plan
- Key rotation procedures

#### 7. **Compliance**
- GDPR: Data retention policies, right to deletion
- CCPA: Privacy notices, opt-out mechanisms
- HIPAA: If handling health data (requires additional measures)

---

## Security Checklist for Deployment

### Pre-Deployment
- [ ] Generate unique SECRET_KEY for production
- [ ] Configure ALLOWED_ORIGINS with production domains
- [ ] Set FLASK_ENV=production
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Remove debug flags and test accounts
- [ ] Verify .env is NOT in git repository
- [ ] Run dependency security scan
- [ ] Test rate limiting functionality
- [ ] Test CORS configuration
- [ ] Verify HTTPS certificate validity

### Deployment
- [ ] Deploy behind reverse proxy (nginx/Apache)
- [ ] Use production WSGI server (gunicorn/uWSGI)
- [ ] Configure firewall rules (only 443/80 open)
- [ ] Set up log rotation and monitoring
- [ ] Configure automatic security updates
- [ ] Enable intrusion detection (fail2ban)
- [ ] Set up backup procedures

### Post-Deployment
- [ ] Monitor security logs daily
- [ ] Set up automated vulnerability scanning
- [ ] Configure uptime monitoring
- [ ] Test incident response procedures
- [ ] Schedule regular security audits
- [ ] Keep dependencies updated

---

## Vulnerability Disclosure

If you discover a security vulnerability, please:
1. **DO NOT** open a public issue
2. Email security concerns to: [your-email@domain.com]
3. Include detailed reproduction steps
4. Allow 90 days for patch before disclosure

---

## Security Contact

For security-related questions or concerns:
- **Email**: [security@yourdomain.com]
- **Response Time**: Within 24-48 hours
- **Updates**: Check this document for latest security guidance

---

## Changelog

### 2026-01-14
- ✅ Added encrypted API key storage
- ✅ Implemented rate limiting
- ✅ Added security headers
- ✅ Fixed CORS configuration (explicit origins)
- ✅ Improved error message sanitization
- ✅ Added security logging with rotation
- ✅ Disabled debug mode for production
- ✅ Rotated SECRET_KEY (git exposure)
- ✅ Created .env.example template

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)
