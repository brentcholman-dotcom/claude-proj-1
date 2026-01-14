#!/bin/bash

echo "🔒 Privacy-First LLM Router Setup"
echo "=================================="

# Create project directory
mkdir -p ~/llm-privacy-router
cd ~/llm-privacy-router

echo "📁 Created project directory: ~/llm-privacy-router"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install flask flask-cors openai anthropic requests python-dotenv

# Create environment file template
cat > .env << 'EOF'
# Cloud Service API Keys (optional - leave blank to use only local models)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Ollama Configuration
OLLAMA_URL=http://localhost:11434

# Flask Configuration
FLASK_ENV=development
FLASK_PORT=5000
EOF

echo "⚙️  Created .env file template"

# Create requirements.txt
cat > requirements.txt << 'EOF'
flask>=2.3.0
flask-cors>=4.0.0
openai>=1.0.0
anthropic>=0.7.0
requests>=2.31.0
python-dotenv>=1.0.0
EOF

echo "📋 Created requirements.txt"

# Create simple launcher script
cat > run_router.py << 'EOF'
#!/usr/bin/env python3
"""
Simple launcher for the Privacy-First LLM Router
"""

import os
import sys
import subprocess
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_ollama():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Start Ollama if not running"""
    if not check_ollama():
        print("🔄 Starting Ollama...")
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Wait for Ollama to start
            
            if check_ollama():
                print("✅ Ollama started successfully")
            else:
                print("❌ Failed to start Ollama")
                return False
        except FileNotFoundError:
            print("❌ Ollama not found. Please install Ollama first.")
            print("   Visit: https://ollama.ai/")
            return False
    else:
        print("✅ Ollama is already running")
    
    return True

def check_model():
    """Check if llama3.1:8b model is available"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        
        for model in models:
            if "llama3.1:8b" in model.get("name", ""):
                print("✅ llama3.1:8b model is available")
                return True
        
        print("📥 llama3.1:8b model not found. Downloading...")
        subprocess.run(["ollama", "pull", "llama3.1:8b"])
        print("✅ Model downloaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error checking model: {e}")
        return False

def main():
    print("🔒 Privacy-First LLM Router Launcher")
    print("===================================")
    
    # Check and start Ollama
    if not start_ollama():
        sys.exit(1)
    
    # Check model availability
    if not check_model():
        print("⚠️  Warning: Model check failed, but continuing...")
    
    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    print("\n🔑 API Key Status:")
    print(f"   OpenAI: {'✅ Configured' if openai_key else '❌ Not set'}")
    print(f"   Anthropic: {'✅ Configured' if anthropic_key else '❌ Not set'}")
    
    if not openai_key and not anthropic_key:
        print("\n⚠️  No cloud API keys configured. Only local routing will work.")
        print("   To add cloud services, edit the .env file with your API keys.")
    
    print("\n🚀 Starting Flask backend...")
    print("   Local:  http://localhost:5000")
    print("   Health: http://localhost:5000/api/health")
    print("\n💡 Tip: Keep this terminal open and use another terminal for testing")
    print("   Or open the web interface in your browser!")
    
    # Import and run the Flask app
    try:
        from flask_backend import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError:
        print("❌ Flask backend not found. Make sure flask_backend.py is in the current directory.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x run_router.py

# Create a simple test script
cat > test_router.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for the Privacy-First LLM Router API
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print("🏥 Health Check:")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_query(query):
    """Test a query"""
    try:
        response = requests.post(f"{BASE_URL}/query", json={"query": query})
        result = response.json()
        
        print(f"\n📝 Query: {query}")
        print(f"🎯 Routing: {result['routing_decision']['destination'].upper()}")
        print(f"📊 Confidence: {result['routing_decision']['confidence']:.2f}")
        print(f"💬 Response: {result['response'][:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

def main():
    print("🔒 Privacy-First LLM Router Test Suite")
    print("=====================================")
    
    # Test health
    if not test_health():
        print("❌ Backend not responding. Make sure it's running with: python run_router.py")
        return
    
    # Test queries
    test_queries = [
        "What's the capital of France?",
        "I'm having chest pain, should I see a doctor?",
        "How should I analyze my investment portfolio?",
        "Can you help me debug this Python code?",
    ]
    
    print("\n🧪 Testing Routing Decisions:")
    for query in test_queries:
        test_query(query)
    
    # Get stats
    try:
        response = requests.get(f"{BASE_URL}/stats")
        print(f"\n📊 Final Stats:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Stats failed: {e}")

if __name__ == "__main__":
    main()
EOF

chmod +x test_router.py

echo ""
echo "✅ Setup complete! Here's what to do next:"
echo ""
echo "1. 📝 Edit API keys (optional for cloud services):"
echo "   nano .env"
echo ""
echo "2. 🚀 Start the router:"
echo "   python run_router.py"
echo ""
echo "3. 🧪 Test in another terminal:"
echo "   python test_router.py"
echo ""
echo "4. 🌐 Or open http://localhost:5000 in your browser"
echo ""
echo "📁 All files created in: ~/llm-privacy-router"
echo ""
echo "🔍 Files created:"
echo "   - run_router.py      (Main launcher)"
echo "   - test_router.py     (Test suite)"
echo "   - .env               (Configuration)"
echo "   - requirements.txt   (Dependencies)"
echo ""
echo "⚠️  Next steps:"
echo "   1. Copy privacy_router.py to this directory"
echo "   2. Copy flask_backend.py to this directory"  
echo "   3. Save the HTML UI as index.html"
echo ""
