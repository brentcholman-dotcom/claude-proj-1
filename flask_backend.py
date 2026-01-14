#!/usr/bin/env python3
"""
Flask Backend for Multi-LLM Privacy Router
Supports Claude, ChatGPT, Gemini, and Grok with privacy protection
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import requests
from anthropic import Anthropic
import openai
import google.generativeai as genai

# Import our privacy router
from privacy_router import LLMRouter, RoutingDecision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)
CORS(app, supports_credentials=True)

class MultiLLMManager:
    """Manages connections to multiple LLM providers with privacy protection"""

    # Supported providers
    PROVIDERS = {
        'claude': {'name': 'Claude (Anthropic)', 'default_model': 'claude-sonnet-4-20250514'},
        'chatgpt': {'name': 'ChatGPT (OpenAI)', 'default_model': 'gpt-4'},
        'gemini': {'name': 'Gemini (Google)', 'default_model': 'gemini-pro'},
        'grok': {'name': 'Grok (xAI)', 'default_model': 'grok-beta'}
    }

    def __init__(self):
        """Initialize manager - clients created per-session"""
        pass

    def validate_api_key(self, provider: str, api_key: str) -> tuple[bool, str]:
        """Validate an API key by making a test request"""
        try:
            if provider == 'claude':
                client = Anthropic(api_key=api_key)
                # Test with minimal request
                client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True, "Claude API key validated successfully"

            elif provider == 'chatgpt':
                client = openai.OpenAI(api_key=api_key)
                # Test with minimal request
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True, "OpenAI API key validated successfully"

            elif provider == 'gemini':
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                # Test with minimal request
                model.generate_content("test", generation_config={'max_output_tokens': 10})
                return True, "Gemini API key validated successfully"

            elif provider == 'grok':
                # Grok uses OpenAI-compatible API
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1"
                )
                # Test with minimal request
                client.chat.completions.create(
                    model="grok-beta",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True, "Grok API key validated successfully"
            else:
                return False, f"Unknown provider: {provider}"

        except Exception as e:
            logger.error(f"API key validation failed for {provider}: {e}")
            return False, f"Validation failed: {str(e)}"

    def query_llm(self, provider: str, api_key: str, prompt: str) -> str:
        """Query the selected LLM provider"""
        try:
            if provider == 'claude':
                return self._query_claude(api_key, prompt)
            elif provider == 'chatgpt':
                return self._query_chatgpt(api_key, prompt)
            elif provider == 'gemini':
                return self._query_gemini(api_key, prompt)
            elif provider == 'grok':
                return self._query_grok(api_key, prompt)
            else:
                return f"Error: Unsupported provider '{provider}'"
        except Exception as e:
            logger.error(f"Error querying {provider}: {e}")
            return f"Error querying {provider}: {str(e)}"

    def _query_claude(self, api_key: str, prompt: str) -> str:
        """Query Claude (Anthropic)"""
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _query_chatgpt(self, api_key: str, prompt: str) -> str:
        """Query ChatGPT (OpenAI)"""
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _query_gemini(self, api_key: str, prompt: str) -> str:
        """Query Gemini (Google)"""
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

    def _query_grok(self, api_key: str, prompt: str) -> str:
        """Query Grok (xAI)"""
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        response = client.chat.completions.create(
            model="grok-beta",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

class EnhancedLLMRouter(LLMRouter):
    """Router that sends requests to selected LLM with privacy protection"""

    def __init__(self):
        super().__init__()
        self.llm_manager = MultiLLMManager()
        self.user_preferences = self.load_user_preferences()

    def load_user_preferences(self) -> Dict:
        """Load user preferences from file"""
        try:
            with open('user_preferences.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default preferences
            return {
                "auto_apply_learned_rules": False,
                "learned_rules": {}
            }
    
    def save_user_preferences(self):
        """Save user preferences to file"""
        with open('user_preferences.json', 'w') as f:
            json.dump(self.user_preferences, f, indent=2)
    
    def query_llm(self, provider: str, api_key: str, prompt: str) -> str:
        """Query the selected LLM provider"""
        return self.llm_manager.query_llm(provider, api_key, prompt)
    
    def apply_learned_rules(self, query: str) -> Optional[RoutingDecision]:
        """Apply previously learned routing rules"""
        if not self.user_preferences.get("auto_apply_learned_rules", True):
            return None
        
        learned_rules = self.user_preferences.get("learned_rules", {})
        
        # Simple keyword-based rule matching for demo
        # In production, this would be more sophisticated
        query_lower = query.lower()
        
        for rule_pattern, rule_data in learned_rules.items():
            if rule_pattern in query_lower and rule_data.get("confidence", 0) > 0.8:
                logger.info(f"Applied learned rule: {rule_pattern} -> {rule_data['destination']}")
                
                # Create a routing decision based on learned rule
                decision = RoutingDecision(
                    destination=rule_data["destination"],
                    confidence=rule_data["confidence"],
                    sensitivity_score=rule_data.get("sensitivity_score", 0.5),
                    complexity_score=rule_data.get("complexity_score", 0.5),
                    reasoning=[f"Learned rule applied: {rule_pattern}"],
                    detected_patterns=[f"learned_pattern: {rule_pattern}"]
                )
                return decision
        
        return None
    
    def learn_from_correction(self, query: str, original_decision: RoutingDecision, 
                            corrected_destination: str, reason: str = ""):
        """Learn from user corrections to improve future routing"""
        
        # Extract key patterns from the query for learning
        key_patterns = []
        query_lower = query.lower()
        
        # Extract domain-specific keywords
        health_keywords = ['health', 'doctor', 'medical', 'pain', 'symptoms']
        finance_keywords = ['financial', 'money', 'investment', 'budget', 'loan']
        work_keywords = ['work', 'job', 'career', 'office', 'meeting']
        
        for keyword in health_keywords:
            if keyword in query_lower:
                key_patterns.append(f"health_{keyword}")
        
        for keyword in finance_keywords:
            if keyword in query_lower:
                key_patterns.append(f"finance_{keyword}")
                
        for keyword in work_keywords:
            if keyword in query_lower:
                key_patterns.append(f"work_{keyword}")
        
        # Store learned rules
        learned_rules = self.user_preferences.get("learned_rules", {})
        
        for pattern in key_patterns:
            if pattern not in learned_rules:
                learned_rules[pattern] = {
                    "destination": corrected_destination,
                    "confidence": 0.6,
                    "examples": 1,
                    "sensitivity_score": original_decision.sensitivity_score,
                    "complexity_score": original_decision.complexity_score,
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # Update existing rule
                rule = learned_rules[pattern]
                if rule["destination"] == corrected_destination:
                    # Strengthen confidence
                    rule["confidence"] = min(0.95, rule["confidence"] + 0.1)
                    rule["examples"] += 1
                else:
                    # Conflicting correction, reduce confidence
                    rule["confidence"] = max(0.3, rule["confidence"] - 0.1)
                
                rule["last_updated"] = datetime.now().isoformat()
        
        self.user_preferences["learned_rules"] = learned_rules
        self.save_user_preferences()
        
        logger.info(f"Learned from correction: {query[:50]}... -> {corrected_destination}")
    
    def enhanced_process_query(self, query: str, provider: str, api_key: str) -> Dict:
        """Process query with privacy protection and send to selected LLM"""

        # Analyze query for PII and sensitivity
        decision = self.analyze_query(query, self.conversation_history[-5:])

        # Determine if anonymization is needed based on sensitivity
        processed_query = query
        anonymization_applied = False

        # Apply anonymization for high-sensitivity queries or if PII detected
        if decision.sensitivity_score > 0.3:  # Medium to high sensitivity
            processed_query = self.anonymize_query(query)
            anonymization_applied = True
            decision.anonymization_needed = True
            logger.info(f"Query anonymized - Sensitivity: {decision.sensitivity_score:.2f}")

        # Send to selected LLM (with anonymization if needed)
        response = self.query_llm(provider, api_key, processed_query)
        provider_name = self.llm_manager.PROVIDERS.get(provider, {}).get('name', provider)

        # Store conversation history (original query)
        self.conversation_history.append(query)

        return {
            'query': query,
            'response': response,
            'routing_decision': {
                'destination': provider,
                'confidence': 1.0,
                'sensitivity_score': decision.sensitivity_score,
                'complexity_score': decision.complexity_score,
                'reasoning': decision.reasoning + ([f'Privacy protection: Query anonymized before sending to {provider_name}'] if anonymization_applied else []),
                'detected_patterns': decision.detected_patterns,
                'anonymization_needed': anonymization_applied
            },
            'model_used': provider_name,
            'processed_query': processed_query if anonymization_applied else None,
            'timestamp': datetime.now().isoformat()
        }

# Initialize the enhanced router
router = EnhancedLLMRouter()

@app.route('/')
def index():
    """Serve the main UI"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>Privacy-First LLM Router API</h1>
        <p>HTML interface not found. Please save the interface as 'index.html' in the current directory.</p>
        <p>Current directory: """ + os.getcwd() + """</p>
        <p>Looking for: index.html</p>
        <p>Files in directory: """ + str(os.listdir('.')) + """</p>
        """

@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get list of available LLM providers"""
    return jsonify({
        'providers': router.llm_manager.PROVIDERS,
        'current': session.get('provider', None)
    })

@app.route('/api/set-provider', methods=['POST'])
def set_provider():
    """Set the active LLM provider"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        api_key = data.get('api_key')

        if not provider or provider not in router.llm_manager.PROVIDERS:
            return jsonify({'error': 'Invalid provider'}), 400

        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Validate API key
        valid, message = router.llm_manager.validate_api_key(provider, api_key)

        if not valid:
            return jsonify({'error': message}), 401

        # Store in session (server-side, secure)
        session['provider'] = provider
        session['api_key'] = api_key
        session.modified = True

        logger.info(f"Provider set to {provider}")

        return jsonify({
            'success': True,
            'status': 'success',
            'message': message,
            'provider': provider,
            'provider_name': router.llm_manager.PROVIDERS[provider]['name']
        })

    except Exception as e:
        logger.error(f"Error setting provider: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-provider', methods=['GET'])
def get_current_provider():
    """Get current provider status"""
    provider = session.get('provider')
    has_api_key = 'api_key' in session

    if provider and has_api_key:
        return jsonify({
            'configured': True,
            'provider': provider,
            'provider_name': router.llm_manager.PROVIDERS[provider]['name']
        })
    else:
        return jsonify({
            'configured': False,
            'provider': None
        })

@app.route('/api/query', methods=['POST'])
def process_query():
    """Main endpoint for processing queries"""
    try:
        # Check if provider is configured
        provider = session.get('provider')
        api_key = session.get('api_key')

        if not provider or not api_key:
            return jsonify({
                'error': 'Please select an LLM provider and configure your API key first'
            }), 403

        data = request.get_json()
        query = data.get('query', '')

        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400

        result = router.enhanced_process_query(query, provider, api_key)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/correct', methods=['POST'])
def submit_correction():
    """Endpoint for submitting routing corrections"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        original_destination = data.get('original_destination', '')
        corrected_destination = data.get('corrected_destination', '')
        reason = data.get('reason', '')
        
        # Find the original decision in routing history
        original_decision = None
        for history_item in reversed(router.routing_history):
            if history_item['query'] == query:
                original_decision = history_item['decision']
                break
        
        if original_decision:
            router.learn_from_correction(
                query, 
                original_decision, 
                corrected_destination, 
                reason
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Correction recorded and learned from'
            })
        else:
            return jsonify({'error': 'Original query not found in history'}), 404
            
    except Exception as e:
        logger.error(f"Error processing correction: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get query statistics"""
    try:
        history = router.conversation_history

        return jsonify({
            'total_queries': len(history),
            'claude_count': len(history),
            'service': 'Claude (Anthropic)'
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """Get user preferences"""
    return jsonify(router.user_preferences)

@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    """Update user preferences"""
    try:
        data = request.get_json()
        
        # Update preferences
        for key, value in data.items():
            if key in router.user_preferences:
                router.user_preferences[key] = value
        
        router.save_user_preferences()
        
        return jsonify({
            'status': 'success',
            'message': 'Preferences updated',
            'preferences': router.user_preferences
        })
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        provider = session.get('provider')
        has_api_key = 'api_key' in session

        return jsonify({
            'status': 'healthy',
            'configured': has_api_key,
            'provider': provider if has_api_key else None,
            'total_queries_processed': len(router.conversation_history),
            'available_providers': list(router.llm_manager.PROVIDERS.keys())
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("🤖 Multi-LLM Privacy Router Backend Starting...")
    print("=" * 60)
    print("📋 Supported LLM Providers:")
    for key, info in router.llm_manager.PROVIDERS.items():
        print(f"   • {info['name']}")
    print("\n🔒 Privacy Protection: All queries are analyzed and anonymized")
    print("   when sensitive information is detected")
    print("\n🚀 Starting server on http://localhost:5000")
    print("   Select your LLM provider in the web interface")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
