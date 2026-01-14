# Claude AI Chat

A web-based chat interface powered by Claude from Anthropic.

## Features

- Clean, modern chat interface
- All queries processed by Claude (Anthropic)
- Flask backend with Python
- Real-time conversation history

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

## Requirements

- Python 3.11+
- Anthropic API key

## Project Structure

- `flask_backend.py` - Flask server and API endpoints
- `privacy_router.py` - Router logic (simplified for Claude-only)
- `index.html` - Web interface
- `.env` - Configuration file
- `requirements.txt` - Python dependencies
