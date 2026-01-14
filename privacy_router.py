#!/usr/bin/env python3
"""
Claude LLM Router
Processes all queries through Claude (Anthropic)
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Represents a routing decision with reasoning"""
    destination: str  # "local" or "cloud" 
    confidence: float  # 0.0 to 1.0
    sensitivity_score: float  # 0.0 to 1.0
    complexity_score: float  # 0.0 to 1.0
    reasoning: List[str]  # Human-readable reasons
    detected_patterns: List[str]  # What patterns were detected
    anonymization_needed: bool = False

class PrivacyClassifier:
    """Multi-layer privacy and sensitivity classifier"""
    
    def __init__(self):
        # Layer 1: Explicit PII patterns (highest priority)
        self.pii_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'address': r'\b\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b'
        }
        
        # Layer 2: Sensitive keyword categories
        self.sensitive_keywords = {
            'health_symptoms': [
                'pain', 'symptoms', 'doctor', 'medication', 'diagnosis', 'illness',
                'therapy', 'treatment', 'hospital', 'medical', 'health insurance',
                'prescription', 'side effects', 'disease', 'condition', 'surgery'
            ],
            'financial_personal': [
                'my salary', 'my income', 'my debt', 'my mortgage', 'my loan',
                'my credit score', 'my bank', 'my account', 'refinance my',
                'my budget', 'my expenses', 'my savings', 'bankruptcy',
                'foreclosure', 'personal loan'
            ],
            'mental_health': [
                'depression', 'anxiety', 'therapist', 'counseling', 'suicide',
                'self-harm', 'panic attack', 'ptsd', 'bipolar', 'medication',
                'mental health', 'therapy session', 'psychiatrist'
            ],
            'relationships_personal': [
                'my partner', 'my spouse', 'my marriage', 'my relationship',
                'breakup', 'divorce', 'dating', 'my boyfriend', 'my girlfriend',
                'my family', 'my children', 'my parents', 'domestic violence',
                'custody', 'affair'
            ],
            'legal_personal': [
                'my lawyer', 'my case', 'lawsuit', 'legal trouble', 'arrest',
                'court date', 'criminal record', 'restraining order', 'will',
                'inheritance', 'custody battle'
            ]
        }
        
        # Layer 3: Personal identifiers and context
        self.personal_indicators = [
            'my', 'i am', 'i have', 'i need', 'i want', 'i think', 'i feel',
            'personally', 'in my case', 'for me', 'my situation'
        ]
        
        # Complexity indicators
        self.complexity_keywords = [
            'analyze', 'comprehensive', 'detailed analysis', 'research',
            'compare multiple', 'evaluate', 'deep dive', 'strategy',
            'forecast', 'predict', 'model', 'simulate', 'optimize'
        ]
        
        # Non-sensitive general topics
        self.general_topics = [
            'weather', 'news', 'sports', 'entertainment', 'technology',
            'science', 'history', 'geography', 'math', 'programming',
            'recipes', 'travel destinations', 'movie recommendations'
        ]

    def detect_pii(self, text: str) -> List[str]:
        """Detect personally identifiable information"""
        detected = []
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(pii_type)
        return detected

    def calculate_sensitivity_score(self, text: str) -> Tuple[float, List[str]]:
        """Calculate sensitivity score based on detected patterns"""
        text_lower = text.lower()
        detected_patterns = []
        score = 0.0
        
        # Check for PII (immediate high sensitivity)
        pii_detected = self.detect_pii(text)
        if pii_detected:
            score = 1.0
            detected_patterns.extend([f"PII: {pii}" for pii in pii_detected])
            return score, detected_patterns
        
        # Check sensitive keyword categories
        category_scores = {}
        for category, keywords in self.sensitive_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                category_scores[category] = min(matches * 0.3, 1.0)
                detected_patterns.append(f"{category}: {matches} matches")
        
        # Check for personal indicators
        personal_matches = sum(1 for indicator in self.personal_indicators 
                             if indicator in text_lower)
        if personal_matches > 0:
            personal_score = min(personal_matches * 0.2, 0.6)
            detected_patterns.append(f"personal_context: {personal_matches} indicators")
        else:
            personal_score = 0
        
        # Calculate final sensitivity score
        if category_scores:
            # Take the highest category score and add personal context
            max_category_score = max(category_scores.values())
            score = min(max_category_score + personal_score, 1.0)
        else:
            score = personal_score
        
        return score, detected_patterns

    def calculate_complexity_score(self, text: str) -> Tuple[float, List[str]]:
        """Calculate complexity score based on query characteristics"""
        text_lower = text.lower()
        detected_patterns = []
        score = 0.0
        
        # Check for complexity keywords
        complexity_matches = sum(1 for keyword in self.complexity_keywords 
                               if keyword in text_lower)
        if complexity_matches > 0:
            score += min(complexity_matches * 0.3, 0.6)
            detected_patterns.append(f"complexity_keywords: {complexity_matches}")
        
        # Check query length (longer queries often more complex)
        word_count = len(text.split())
        if word_count > 50:
            score += 0.3
            detected_patterns.append(f"long_query: {word_count} words")
        elif word_count > 20:
            score += 0.1
            detected_patterns.append(f"medium_query: {word_count} words")
        
        # Check for multiple questions
        question_count = text.count('?')
        if question_count > 1:
            score += 0.2
            detected_patterns.append(f"multiple_questions: {question_count}")
        
        # Check for technical/domain-specific complexity
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'\$[\d,]+',       # Dollar amounts
            r'\d+%',           # Percentages
            r'\b\d{4}\b'       # Years
        ]
        
        technical_matches = sum(1 for pattern in technical_patterns 
                              if re.search(pattern, text))
        if technical_matches > 2:
            score += 0.2
            detected_patterns.append(f"technical_content: {technical_matches}")
        
        return min(score, 1.0), detected_patterns

class LLMRouter:
    """Main router for Claude - maintains conversation history"""

    def __init__(self):
        self.classifier = PrivacyClassifier()
        self.conversation_history = []
        
    def analyze_query(self, query: str, context: Optional[List[str]] = None) -> RoutingDecision:
        """Analyze a query and determine routing decision"""
        
        # Combine query with recent context for analysis
        full_text = query
        if context:
            full_text = " ".join(context[-3:]) + " " + query  # Last 3 context items
        
        # Calculate scores
        sensitivity_score, sensitivity_patterns = self.classifier.calculate_sensitivity_score(full_text)
        complexity_score, complexity_patterns = self.classifier.calculate_complexity_score(query)
        
        # Make routing decision
        reasoning = []
        detected_patterns = sensitivity_patterns + complexity_patterns
        
        # Decision logic
        if sensitivity_score >= self.sensitivity_threshold_high:
            destination = "local"
            confidence = 0.9 + (sensitivity_score - self.sensitivity_threshold_high) * 0.5
            reasoning.append(f"High sensitivity score: {sensitivity_score:.2f}")
            reasoning.append("Privacy protection required")
            
        elif sensitivity_score <= self.sensitivity_threshold_medium:
            if complexity_score >= self.complexity_threshold_cloud:
                destination = "cloud"
                confidence = 0.7 + (complexity_score - self.complexity_threshold_cloud) * 0.3
                reasoning.append(f"Low sensitivity: {sensitivity_score:.2f}")
                reasoning.append(f"High complexity: {complexity_score:.2f}")
                reasoning.append("Cloud model better suited for complex reasoning")
            else:
                destination = "local"
                confidence = 0.6
                reasoning.append("Low sensitivity and complexity - keeping local for speed")
                
        else:  # Medium sensitivity
            if complexity_score >= self.complexity_threshold_cloud:
                destination = "cloud"
                confidence = 0.5
                reasoning.append(f"Medium sensitivity: {sensitivity_score:.2f}")
                reasoning.append(f"High complexity: {complexity_score:.2f}")
                reasoning.append("Anonymization recommended for cloud processing")
                anonymization_needed = True
            else:
                destination = "local"
                confidence = 0.7
                reasoning.append("Medium sensitivity - defaulting to local for privacy")
        
        # Ensure confidence is in valid range
        confidence = max(0.1, min(1.0, confidence))
        
        decision = RoutingDecision(
            destination=destination,
            confidence=confidence,
            sensitivity_score=sensitivity_score,
            complexity_score=complexity_score,
            reasoning=reasoning,
            detected_patterns=detected_patterns,
            anonymization_needed=locals().get('anonymization_needed', False)
        )
        
        # Store decision for learning
        self.routing_history.append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'decision': decision,
            'context_used': bool(context)
        })
        
        return decision
    
    
    def anonymize_query(self, query: str) -> str:
        """Basic anonymization for medium-sensitivity queries going to cloud"""
        anonymized = query
        
        # Replace personal pronouns
        anonymized = re.sub(r'\bmy\b', 'a person\'s', anonymized, flags=re.IGNORECASE)
        anonymized = re.sub(r'\bi am\b', 'someone is', anonymized, flags=re.IGNORECASE)
        anonymized = re.sub(r'\bi have\b', 'someone has', anonymized, flags=re.IGNORECASE)
        anonymized = re.sub(r'\bi need\b', 'someone needs', anonymized, flags=re.IGNORECASE)
        
        # Remove specific identifiers (basic approach)
        anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', anonymized)
        anonymized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', anonymized)
        
        return anonymized
    
    def process_query(self, query: str, force_destination: Optional[str] = None) -> Dict:
        """Main entry point - process query (actual sending to Claude handled by flask_backend)"""

        # Store conversation history
        self.conversation_history.append(query)

        return {
            'query': query,
            'response': '[Processed by Claude]',
            'routing_decision': {
                'destination': 'claude',
                'confidence': 1.0
            },
            'model_used': 'Claude (Anthropic)'
        }

# Example usage and testing
if __name__ == "__main__":
    router = LLMRouter()

    # Test queries
    test_queries = [
        "What's the capital of France?",
        "How should I analyze the ROI of different investment strategies?",
        "Can you help me debug this Python code?",
    ]

    print("🤖 Claude LLM Router Demo\n")
    print("All queries are sent to Claude (Anthropic)\n")

    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        result = router.process_query(query)
        print(f"📍 Destination: {result['routing_decision']['destination'].upper()}")
        print(f"🤖 Model: {result['model_used']}")
        print("-" * 80)

    print(f"\n📈 Total queries processed: {len(router.conversation_history)}")
