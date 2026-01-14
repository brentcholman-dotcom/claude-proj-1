# Security Fixes Required for Multi-LLM Privacy Chat

## Critical Issues (Immediate Action Required)

### 1. Enable HTTPS (CRITICAL)
**Risk:** API keys transmitted in plaintext over network

**Solutions:**

#### Production (Recommended):
```bash
# Install nginx and certbot
sudo apt install nginx certbot python3-certbot-nginx

# Get free SSL certificate
sudo certbot --nginx -d yourdomain.com

# Nginx config (/etc/nginx/sites-available/default)
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Development/Testing:
```python
# Add to flask_backend.py
if __name__ == '__main__':
    # Generate self-signed cert
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # NEVER True in production
        ssl_context=context
    )
```

---

### 2. Encrypt API Keys at Rest (CRITICAL)
**Risk:** Session files contain plaintext API keys

**Fix - Add cryptography module:**

```python
# Add to requirements.txt
cryptography>=41.0.0

# Create new file: secure_session.py
from cryptography.fernet import Fernet
import os
import base64
from hashlib import sha256

class SecureSessionManager:
    def __init__(self):
        # Derive key from SECRET_KEY
        secret = os.environ.get('SECRET_KEY', os.urandom(32))
        key_material = sha256(str(secret).encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_material))

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key before storing in session"""
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key from session"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

# Update flask_backend.py
secure_manager = SecureSessionManager()

@app.route('/api/set-provider', methods=['POST'])
def set_provider():
    # ... validation code ...

    # Encrypt before storing
    encrypted_key = secure_manager.encrypt_api_key(api_key)
    session['provider'] = provider
    session['api_key_enc'] = encrypted_key  # Store encrypted
    # DON'T store: session['api_key'] = api_key

    return jsonify({'success': True, ...})

@app.route('/api/query', methods=['POST'])
def process_query():
    # Decrypt when needed
    encrypted_key = session.get('api_key_enc')
    api_key = secure_manager.decrypt_api_key(encrypted_key)

    # Use decrypted key
    result = router.enhanced_process_query(query, provider, api_key)
    return jsonify(result)
```

---

### 3. Disable Debug Mode (CRITICAL)
**Risk:** Stack traces expose implementation details, debug console allows code execution

**Fix:**
```python
# flask_backend.py - Line ~460
if __name__ == '__main__':
    # Production settings
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # MUST be False in production
        ssl_context='adhoc'  # Or use proper certs
    )
```

**Better - Use Production WSGI Server:**
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:5000 flask_backend:app

# Or uWSGI
pip install uwsgi
uwsgi --http 0.0.0.0:5000 --wsgi-file flask_backend.py --callable app --processes 4
```

---

### 4. Fix Session Secret Key (HIGH)
**Risk:** SECRET_KEY regenerates on restart, invalidating all sessions

**Current Code:**
```python
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
```

**Fix:**
```bash
# Generate persistent secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output: a1b2c3d4e5f6...

# Add to .env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

```python
# Update flask_backend.py
import os
from dotenv import load_dotenv

load_dotenv()

# Require SECRET_KEY to be set
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in environment or .env file")

app.config['SECRET_KEY'] = SECRET_KEY
```

---

## High Priority Issues

### 5. Add Rate Limiting (HIGH)
**Risk:** API abuse, brute force attacks, DoS

**Fix:**
```bash
pip install Flask-Limiter
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Apply to sensitive endpoints
@app.route('/api/set-provider', methods=['POST'])
@limiter.limit("5 per minute")  # Only 5 API key attempts per minute
def set_provider():
    # ...

@app.route('/api/query', methods=['POST'])
@limiter.limit("30 per minute")  # 30 queries per minute
def process_query():
    # ...
```

---

### 6. Add Input Validation (HIGH)
**Risk:** Injection attacks, DoS via large inputs

**Fix:**
```python
from wtforms import Form, StringField, validators

class QueryForm(Form):
    query = StringField('Query', [
        validators.DataRequired(),
        validators.Length(min=1, max=10000)  # Reasonable limit
    ])

@app.route('/api/query', methods=['POST'])
def process_query():
    data = request.get_json()

    # Validate input
    if not data or 'query' not in data:
        return jsonify({'error': 'Query required'}), 400

    query = data['query']

    # Check length
    if len(query) > 10000:
        return jsonify({'error': 'Query too long (max 10000 chars)'}), 400

    if len(query) < 1:
        return jsonify({'error': 'Query cannot be empty'}), 400

    # Sanitize (remove null bytes, control characters)
    query = ''.join(char for char in query if ord(char) >= 32 or char in '\n\r\t')

    # Process query...
```

---

### 7. Add Session Timeout (HIGH)
**Risk:** Stolen sessions valid indefinitely

**Fix:**
```python
from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # 8 hour timeout

@app.route('/api/set-provider', methods=['POST'])
def set_provider():
    # ... after successful validation ...
    session.permanent = True  # Enable timeout
    session['provider'] = provider
    session['api_key_enc'] = encrypted_key
    session['created_at'] = datetime.utcnow().isoformat()
```

---

### 8. Add CSRF Protection (MEDIUM)
**Risk:** Cross-site request forgery

**Fix:**
```bash
pip install Flask-WTF
```

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Exempt API endpoints that handle CORS properly
@csrf.exempt
@app.route('/api/query', methods=['POST'])
def process_query():
    # Verify origin header instead
    origin = request.headers.get('Origin')
    if origin and origin not in ALLOWED_ORIGINS:
        return jsonify({'error': 'Invalid origin'}), 403
    # ...
```

---

### 9. Improve PII Detection (MEDIUM)
**Risk:** Regex-only detection can be bypassed

**Current:**
```python
# Only regex patterns
'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
```

**Enhanced Fix:**
```python
# Add fuzzy matching for obfuscated PII
'ssn_variants': [
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    re.compile(r'\b\d{3}\s+\d{2}\s+\d{4}\b'),  # Spaces
    re.compile(r'\b\d{9}\b'),  # No separators
]

# Add context-aware detection
def enhanced_pii_detection(text):
    # Check for phrases like "my SSN is", "social security number"
    context_patterns = [
        r'(?:ssn|social\s+security)[\s:]+(\d{3}[-\s]?\d{2}[-\s]?\d{4})',
        r'(?:email|e-mail)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    ]
    # ... detection logic
```

---

### 10. Add Security Headers (MEDIUM)
**Fix:**
```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response
```

---

## Medium Priority Issues

### 11. Update Deprecated Dependencies (MEDIUM)
**Risk:** Known vulnerabilities in old packages

**Fix:**
```txt
# requirements.txt - Update
flask>=3.0.0
flask-cors>=4.0.0
flask-session>=0.6.0
anthropic>=0.18.0
openai>=1.12.0
google-genai>=0.3.0  # Use new package, not google.generativeai
cryptography>=42.0.0
```

```bash
pip install --upgrade -r requirements.txt
```

---

### 12. Add Logging & Monitoring (MEDIUM)
**Risk:** No visibility into security events

**Fix:**
```python
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
handler = RotatingFileHandler('security.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Log security events
@app.route('/api/set-provider', methods=['POST'])
def set_provider():
    try:
        # ... validation ...
        if validation_success:
            app.logger.info(f"API key validated for provider: {provider} from IP: {request.remote_addr}")
        else:
            app.logger.warning(f"Invalid API key attempt for {provider} from IP: {request.remote_addr}")
    except Exception as e:
        app.logger.error(f"Security exception: {e} from IP: {request.remote_addr}")
```

---

### 13. Don't Run as Root (MEDIUM)
**Risk:** Compromise has system-wide impact

**Fix:**
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash llmchat
sudo chown -R llmchat:llmchat /path/to/app

# Run as user
sudo -u llmchat python3 flask_backend.py

# Or use systemd service
sudo nano /etc/systemd/system/llmchat.service

[Unit]
Description=Multi-LLM Privacy Chat
After=network.target

[Service]
Type=simple
User=llmchat
WorkingDirectory=/path/to/app
ExecStart=/usr/bin/python3 /path/to/app/flask_backend.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Testing Checklist

### Security Testing Needed:

- [ ] **Penetration Testing**
  - Try SQL injection in query field
  - Test XSS with `<script>alert('xss')</script>`
  - Test path traversal: `../../../etc/passwd`
  - Brute force API key validation endpoint

- [ ] **Session Security**
  - Verify sessions expire after timeout
  - Test session fixation attacks
  - Check session cookies have HttpOnly, Secure, SameSite flags

- [ ] **API Security**
  - Test rate limiting effectiveness
  - Verify CORS configuration
  - Test without authentication
  - Test with expired/invalid sessions

- [ ] **PII Protection**
  - Test with obfuscated SSNs: `123 45 6789`, `123456789`
  - Test email variations: `user+tag@domain.com`
  - Test phone numbers: various formats
  - Verify anonymization works

- [ ] **Transport Security**
  - Verify HTTPS enforced
  - Check SSL/TLS configuration (use ssllabs.com)
  - Test downgrade attacks

- [ ] **Input Validation**
  - Send 1MB query
  - Send null bytes, control characters
  - Test Unicode edge cases
  - Send malformed JSON

---

## Quick Security Audit Script

```python
#!/usr/bin/env python3
# security_audit.py

import requests
import json

BASE_URL = 'http://localhost:5000'

print("🔍 Running Security Audit...")

# 1. Check HTTPS
if BASE_URL.startswith('http://'):
    print("❌ CRITICAL: Not using HTTPS")
else:
    print("✅ Using HTTPS")

# 2. Test rate limiting
print("\n📊 Testing rate limiting...")
for i in range(10):
    r = requests.post(f'{BASE_URL}/api/query', json={'query': 'test'})
    if r.status_code == 429:
        print(f"✅ Rate limiting active (blocked at request {i+1})")
        break
else:
    print("❌ No rate limiting detected")

# 3. Check security headers
r = requests.get(BASE_URL)
headers = r.headers
required_headers = [
    'X-Content-Type-Options',
    'X-Frame-Options',
    'X-XSS-Protection',
    'Strict-Transport-Security'
]
for header in required_headers:
    if header in headers:
        print(f"✅ {header}: {headers[header]}")
    else:
        print(f"❌ Missing header: {header}")

# 4. Test session security
r = requests.get(f'{BASE_URL}/api/current-provider')
if 'Set-Cookie' in r.headers:
    cookie = r.headers['Set-Cookie']
    if 'HttpOnly' in cookie:
        print("✅ Session cookie has HttpOnly")
    else:
        print("❌ Session cookie missing HttpOnly")
    if 'Secure' in cookie:
        print("✅ Session cookie has Secure flag")
    else:
        print("❌ Session cookie missing Secure flag")
```

Run with: `python3 security_audit.py`

---

## Summary of Security Posture

### Current State:
- ⚠️ **Security Score: 4/10** (Development-grade, NOT production-ready)

### After Fixes:
- ✅ **Projected Score: 8/10** (Production-ready with monitoring)

### Still Needs (Beyond Code):
- Security audit by professional
- Penetration testing
- Compliance review (GDPR, CCPA if applicable)
- Bug bounty program consideration
- Incident response plan

---

## Priority Order for Implementation:

1. **Enable HTTPS** (1 hour)
2. **Encrypt API keys at rest** (2 hours)
3. **Disable debug mode** (5 minutes)
4. **Fix SECRET_KEY** (10 minutes)
5. **Add rate limiting** (1 hour)
6. **Add input validation** (1 hour)
7. **Add session timeout** (30 minutes)
8. **Add security headers** (30 minutes)
9. **Update dependencies** (30 minutes)
10. **Setup logging** (1 hour)
11. **Run as non-root** (30 minutes)
12. **Add CSRF protection** (1 hour)
13. **Enhance PII detection** (2 hours)
14. **Run security audit script** (15 minutes)

**Total estimated time: ~12 hours**

---

Would you like me to implement any of these fixes immediately?
