#!/usr/bin/env python3
"""
Flask Backend for Privacy-First LLM Router
Handles routing between local Ollama and cloud services with full privacy protection
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import requests
import openai
from anthropic import Anthropic

# Import our privacy router
from privacy_router import LLMRouter, RoutingDecision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class CloudServiceManager:
    """Manages connections to various cloud LLM services"""
    
    def __init__(self):
        # Initialize cloud service clients
        self.openai_client = None
        self.anthropic_client = None
        
        # Load API keys from environment variables
        self.setup_openai()
        self.setup_anthropic()
    
    def setup_openai(self):
        """Initialize OpenAI client if API key is available"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            openai.api_key = api_key
            self.openai_client = openai
            logger.info("OpenAI client initialized")
        else:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    
    def setup_anthropic(self):
        """Initialize Anthropic client if API key is available"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic_client = Anthropic(api_key=api_key)
            logger.info("Anthropic client initialized")
        else:
            logger.warning("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
    
    def query_openai(self, prompt: str, model: str = "gpt-4") -> str:
        """Query OpenAI API"""
        if not self.openai_client:
            return "Error: OpenAI not configured. Please set OPENAI_API_KEY."
        
        try:
            response = self.openai_client.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error querying OpenAI: {e}"
    
    def query_anthropic(self, prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
        """Query Anthropic API"""
        if not self.anthropic_client:
            return "Error: Anthropic not configured. Please set ANTHROPIC_API_KEY."
        
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"Error querying Anthropic: {e}"

class EnhancedLLMRouter(LLMRouter):
    """Enhanced router with cloud service integration"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        super().__init__(ollama_url)
        self.cloud_manager = CloudServiceManager()
        self.user_preferences = self.load_user_preferences()
        
    def load_user_preferences(self) -> Dict:
        """Load user preferences from file"""
        try:
            with open('user_preferences.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default preferences
            return {
                "preferred_cloud_service": "anthropic",  # "openai" or "anthropic"
                "sensitivity_threshold_high": 0.8,
                "sensitivity_threshold_medium": 0.3,
                "complexity_threshold_cloud": 0.7,
                "auto_apply_learned_rules": True,
                "learned_rules": {}
            }
    
    def save_user_preferences(self):
        """Save user preferences to file"""
        with open('user_preferences.json', 'w') as f:
            json.dump(self.user_preferences, f, indent=2)
    
    def query_cloud_model(self, prompt: str, service: Optional[str] = None) -> str:
        """Query cloud model based on user preference"""
        service = service or self.user_preferences.get("preferred_cloud_service", "anthropic")
        
        if service == "openai":
            return self.cloud_manager.query_openai(prompt)
        elif service == "anthropic":
            return self.cloud_manager.query_anthropic(prompt)
        else:
            return f"Error: Unknown cloud service '{service}'"
    
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
    
    def enhanced_process_query(self, query: str, force_destination: Optional[str] = None,
                             cloud_service: Optional[str] = None) -> Dict:
        """Enhanced query processing with learning and cloud integration"""
        
        # First check for learned rules
        learned_decision = self.apply_learned_rules(query)
        if learned_decision and not force_destination:
            decision = learned_decision
        else:
            # Use standard analysis
            decision = self.analyze_query(query, self.conversation_history[-5:])
        
        # Allow manual override
        if force_destination:
            decision.destination = force_destination
            decision.reasoning.append(f"Manual override to {force_destination}")
        
        # Prepare query for processing
        processed_query = query
        if decision.destination == "cloud" and decision.anonymization_needed:
            processed_query = self.anonymize_query(query)
        
        # Get response based on routing decision
        if decision.destination == "local":
            response = self.query_local_model(processed_query)
            model_used = "Local Ollama (llama3.1:8b)"
        else:
            response = self.query_cloud_model(processed_query, cloud_service)
            service_name = cloud_service or self.user_preferences.get("preferred_cloud_service", "anthropic")
            model_used = f"Cloud Model ({service_name.title()})"
        
        # Store conversation history
        self.conversation_history.append(query)
        
        return {
            'query': query,
            'response': response,
            'routing_decision': {
                'destination': decision.destination,
                'confidence': decision.confidence,
                'sensitivity_score': decision.sensitivity_score,
                'complexity_score': decision.complexity_score,
                'reasoning': decision.reasoning,
                'detected_patterns': decision.detected_patterns,
                'anonymization_needed': decision.anonymization_needed
            },
            'model_used': model_used,
            'processed_query': processed_query if processed_query != query else None,
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

@app.route('/api/query', methods=['POST'])
def process_query():
    """Main endpoint for processing queries"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        force_destination = data.get('force_destination')
        cloud_service = data.get('cloud_service')
        
        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        result = router.enhanced_process_query(
            query, 
            force_destination=force_destination,
            cloud_service=cloud_service
        )
        
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
    """Get routing statistics"""
    try:
        history = router.routing_history
        
        if not history:
            return jsonify({
                'total_queries': 0,
                'local_count': 0,
                'cloud_count': 0,
                'accuracy_estimate': 0,
                'category_breakdown': {}
            })
        
        local_count = sum(1 for h in history if h['decision'].destination == 'local')
        cloud_count = len(history) - local_count
        
        # Calculate category breakdown
        categories = {}
        for item in history:
            for pattern in item['decision'].detected_patterns:
                category = pattern.split(':')[0]
                categories[category] = categories.get(category, 0) + 1
        
        return jsonify({
            'total_queries': len(history),
            'local_count': local_count,
            'cloud_count': cloud_count,
            'accuracy_estimate': 89,  # Placeholder - would calculate from corrections
            'category_breakdown': categories,
            'learned_rules_count': len(router.user_preferences.get('learned_rules', {}))
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
        # Check Ollama connection
        ollama_status = "unknown"
        try:
            response = requests.get(f"{router.ollama_url}/api/tags", timeout=5)
            ollama_status = "connected" if response.status_code == 200 else "error"
        except:
            ollama_status = "disconnected"
        
        # Check cloud services
        cloud_services = {
            "openai": "configured" if router.cloud_manager.openai_client else "not_configured",
            "anthropic": "configured" if router.cloud_manager.anthropic_client else "not_configured"
        }
        
        return jsonify({
            'status': 'healthy',
            'ollama_status': ollama_status,
            'cloud_services': cloud_services,
            'total_queries_processed': len(router.routing_history)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("🔒 Privacy-First LLM Router Backend Starting...")
    print("📋 Setup Instructions:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Set environment variables for cloud services:")
    print("   export OPENAI_API_KEY='your-key-here'")
    print("   export ANTHROPIC_API_KEY='your-key-here'")
    print("3. Install dependencies: pip install flask flask-cors openai anthropic")
    print("\n🚀 Starting server on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
