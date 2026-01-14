# Claude AI Chat with Privacy Protection

A web-based chat interface powered by Claude from Anthropic, with built-in privacy filtering.

## Features

- Clean, modern chat interface
- All queries processed by Claude (Anthropic)
- **Automatic PII detection and anonymization**
- **Sensitivity analysis for every query**
- Flask backend with Python
- Real-time conversation history
- Privacy-first design: sensitive data is stripped before sending to Claude

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Anthropic API key in `.env`:
```
ANTHROPIC_API_KEY=your-api-key-here
```

3. Run the application:
```bash
python3 flask_backend.py
```

4. Open your browser to `http://localhost:5000`

## Privacy Protection

The application automatically analyzes every query for sensitive information and applies anonymization when needed:

### What Gets Detected
- **PII**: Email addresses, SSNs, phone numbers, credit cards, physical addresses
- **Health Information**: Medical symptoms, diagnoses, medications, therapy mentions
- **Financial Details**: Personal income, debt, loans, credit scores, account numbers
- **Personal Context**: Relationship details, mental health, legal issues
- **Context Indicators**: Personal pronouns ("my", "I am", "I have")

### How It Works
1. Every query is analyzed for sensitivity (scored 0.0 to 1.0)
2. Queries with sensitivity > 0.3 are automatically anonymized
3. PII is removed or replaced with placeholders
4. Personal pronouns are converted to generic forms
5. Only the anonymized version is sent to Claude
6. You see a "Privacy Protected" indicator when anonymization occurs

### Example
- **Original**: "I'm having chest pain and my email is john@example.com"
- **Sent to Claude**: "Someone is having chest pain and [EMAIL]"

## Requirements

- Python 3.11+
- Anthropic API key

## Project Structure

- `flask_backend.py` - Flask server and API endpoints
- `privacy_router.py` - Privacy classification and anonymization logic
- `index.html` - Web interface with privacy indicators
- `.env` - Configuration file
- `requirements.txt` - Python dependencies
