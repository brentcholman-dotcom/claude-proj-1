#!/usr/bin/env python3
"""
Test script for privacy filtering functionality
"""

from privacy_router import LLMRouter, PrivacyClassifier

def test_pii_detection():
    """Test PII detection"""
    print("🧪 Testing PII Detection\n")

    classifier = PrivacyClassifier()

    test_cases = [
        ("My email is john@example.com", "Should detect email"),
        ("Call me at 555-123-4567", "Should detect phone"),
        ("My SSN is 123-45-6789", "Should detect SSN"),
        ("What's the weather today?", "Should not detect PII"),
    ]

    for query, description in test_cases:
        pii = classifier.detect_pii(query)
        print(f"Query: {query}")
        print(f"Expected: {description}")
        print(f"Detected PII: {pii if pii else 'None'}")
        print("-" * 60)

def test_sensitivity_analysis():
    """Test sensitivity scoring"""
    print("\n🧪 Testing Sensitivity Analysis\n")

    classifier = PrivacyClassifier()

    test_cases = [
        ("What's the capital of France?", "Low sensitivity"),
        ("I'm having chest pain and difficulty breathing", "High sensitivity - health"),
        ("My therapist said I should try meditation for my anxiety", "High sensitivity - mental health"),
        ("What's the best way to invest in stocks?", "Low sensitivity - general finance"),
        ("My salary is $50,000 and I need help with my debt", "High sensitivity - personal finance"),
    ]

    for query, description in test_cases:
        score, patterns = classifier.calculate_sensitivity_score(query)
        print(f"Query: {query}")
        print(f"Expected: {description}")
        print(f"Sensitivity Score: {score:.2f}")
        print(f"Detected Patterns: {patterns if patterns else 'None'}")
        print("-" * 60)

def test_anonymization():
    """Test query anonymization"""
    print("\n🧪 Testing Anonymization\n")

    router = LLMRouter()

    test_cases = [
        "I'm having chest pain and my email is john@example.com",
        "My therapist suggested I try meditation for my anxiety",
        "I need help with my mortgage refinancing, I owe $280k",
        "What's the best way to debug Python code?",
    ]

    for query in test_cases:
        anonymized = router.anonymize_query(query)
        decision = router.analyze_query(query)

        print(f"Original: {query}")
        print(f"Anonymized: {anonymized}")
        print(f"Sensitivity: {decision.sensitivity_score:.2f}")
        print(f"Would Anonymize: {'YES' if decision.sensitivity_score > 0.3 else 'NO'}")
        print("-" * 60)

def test_full_workflow():
    """Test the complete privacy workflow"""
    print("\n🧪 Testing Full Privacy Workflow\n")

    router = LLMRouter()

    # Simulate what enhanced_process_query does
    test_queries = [
        "What's the capital of France?",
        "I'm having chest pain, should I see a doctor?",
        "My email is test@example.com and I need help",
    ]

    for query in test_queries:
        print(f"\nProcessing: {query}")

        # Analyze
        decision = router.analyze_query(query)
        print(f"  Sensitivity Score: {decision.sensitivity_score:.2f}")
        print(f"  Detected Patterns: {decision.detected_patterns}")

        # Check if anonymization needed
        if decision.sensitivity_score > 0.3:
            anonymized = router.anonymize_query(query)
            print(f"  🔒 ANONYMIZED: {anonymized}")
            print(f"  ✓ Privacy protected before sending to Claude")
        else:
            print(f"  ✓ No anonymization needed (low sensitivity)")

        print("-" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("Privacy Filtering Test Suite")
    print("=" * 60)

    test_pii_detection()
    test_sensitivity_analysis()
    test_anonymization()
    test_full_workflow()

    print("\n✅ All tests completed!")
