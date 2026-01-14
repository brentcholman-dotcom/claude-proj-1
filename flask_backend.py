#!/usr/bin/env python3
"""
Flask Backend for Claude LLM Router
Sends all requests to Claude (Anthropic) for processing
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import requests
from anthropic import Anthropic

# Import our privacy router
from privacy_router import LLMRouter, RoutingDecision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class CloudServiceManager:
    """Manages connection to Claude (Anthropic)"""

    def __init__(self):
        # Initialize Anthropic client
        self.anthropic_client = None
        self.setup_anthropic()

    def setup_anthropic(self):
        """Initialize Anthropic client if API key is available"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic_client = Anthropic(api_key=api_key)
            logger.info("Claude (Anthropic) client initialized")
        else:
            logger.error("Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")

    def query_claude(self, prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
        """Query Claude API"""
        if not self.anthropic_client:
            return "Error: Claude not configured. Please set ANTHROPIC_API_KEY in your .env file."

        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"Error querying Claude: {e}"

class EnhancedLLMRouter(LLMRouter):
    """Router that sends all requests to Claude"""

    def __init__(self):
        super().__init__()
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
                "auto_apply_learned_rules": False,
                "learned_rules": {}
            }
    
    def save_user_preferences(self):
        """Save user preferences to file"""
        with open('user_preferences.json', 'w') as f:
            json.dump(self.user_preferences, f, indent=2)
    
    def query_cloud_model(self, prompt: str, service: Optional[str] = None) -> str:
        """Query Claude (all requests go to Claude)"""
        return self.cloud_manager.query_claude(prompt)
    
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
        """Process query with privacy protection and send to Claude"""

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

        # All requests go to Claude (with anonymization if needed)
        response = self.query_cloud_model(processed_query)
        model_used = "Claude (Anthropic)"

        # Store conversation history (original query)
        self.conversation_history.append(query)

        return {
            'query': query,
            'response': response,
            'routing_decision': {
                'destination': 'claude',
                'confidence': 1.0,
                'sensitivity_score': decision.sensitivity_score,
                'complexity_score': decision.complexity_score,
                'reasoning': decision.reasoning + (['Privacy protection: Query anonymized before sending to Claude'] if anonymization_applied else []),
                'detected_patterns': decision.detected_patterns,
                'anonymization_needed': anonymization_applied
            },
            'model_used': model_used,
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
        # Check Claude/Anthropic connection
        claude_status = "configured" if router.cloud_manager.anthropic_client else "not_configured"

        return jsonify({
            'status': 'healthy',
            'claude_status': claude_status,
            'total_queries_processed': len(router.conversation_history)
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("🤖 Claude LLM Router Backend Starting...")
    print("📋 Setup Instructions:")
    print("1. Set your Anthropic API key in .env file:")
    print("   ANTHROPIC_API_KEY='your-key-here'")
    print("2. All requests will be sent to Claude")
    print("\n🚀 Starting server on http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)
