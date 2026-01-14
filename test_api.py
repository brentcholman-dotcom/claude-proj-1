#!/usr/bin/env python3
"""
Test Script for Multi-LLM Privacy Chat API
Tests all endpoints and privacy protection features
"""

import requests
import json
import time
from typing import Dict, Optional

class MultiLLMAPITester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def print_header(self, text: str):
        """Print a formatted header"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70)

    def print_test(self, test_name: str):
        """Print test name"""
        print(f"\n🧪 TEST: {test_name}")
        print("-" * 70)

    def print_result(self, success: bool, message: str):
        """Print test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")

    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        self.print_test("Health Check")
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = (response.status_code == 200 and
                      data.get('status') == 'healthy' and
                      len(data.get('available_providers', [])) == 4)

            self.print_result(success, f"Server is {'healthy' if success else 'unhealthy'}")
            return success
        except Exception as e:
            self.print_result(False, f"Health check failed: {str(e)}")
            return False

    def test_get_providers(self) -> bool:
        """Test getting list of providers"""
        self.print_test("Get Available Providers")
        try:
            response = self.session.get(f"{self.base_url}/api/providers")
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Current Provider: {data.get('current')}")
            print(f"Available Providers:")
            for provider_id, info in data.get('providers', {}).items():
                print(f"  • {provider_id}: {info['name']}")

            success = (response.status_code == 200 and
                      data.get('current') is None and
                      len(data.get('providers', {})) == 4)

            self.print_result(success, "Providers list retrieved successfully")
            return success
        except Exception as e:
            self.print_result(False, f"Get providers failed: {str(e)}")
            return False

    def test_current_provider_empty(self) -> bool:
        """Test that no provider is configured initially"""
        self.print_test("Check Initial Provider Status (Should be None)")
        try:
            response = self.session.get(f"{self.base_url}/api/current-provider")
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = (response.status_code == 200 and
                      data.get('configured') == False and
                      data.get('provider') is None)

            self.print_result(success, "No provider configured (as expected)")
            return success
        except Exception as e:
            self.print_result(False, f"Check current provider failed: {str(e)}")
            return False

    def test_query_without_provider(self) -> bool:
        """Test that queries fail without provider configuration"""
        self.print_test("Query Without Provider (Should Fail)")
        try:
            response = self.session.post(
                f"{self.base_url}/api/query",
                json={'query': 'Hello, world!'}
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = response.status_code == 403 and 'error' in data

            self.print_result(success, "Query correctly blocked without provider")
            return success
        except Exception as e:
            self.print_result(False, f"Query test failed: {str(e)}")
            return False

    def test_set_provider_invalid_key(self, provider: str = 'claude') -> bool:
        """Test setting provider with invalid API key"""
        self.print_test(f"Set Provider with Invalid Key ({provider})")
        try:
            response = self.session.post(
                f"{self.base_url}/api/set-provider",
                json={
                    'provider': provider,
                    'api_key': 'sk-invalid-test-key-12345'
                }
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = response.status_code == 401 and 'error' in data

            self.print_result(success, "Invalid API key correctly rejected")
            return success
        except Exception as e:
            self.print_result(False, f"Invalid key test failed: {str(e)}")
            return False

    def test_set_provider_valid_key(self, provider: str, api_key: str) -> bool:
        """Test setting provider with valid API key"""
        self.print_test(f"Set Provider with Valid Key ({provider})")
        try:
            print(f"Provider: {provider}")
            print(f"API Key: {api_key[:15]}...")
            print("Validating... (this may take a few seconds)")

            response = self.session.post(
                f"{self.base_url}/api/set-provider",
                json={
                    'provider': provider,
                    'api_key': api_key
                }
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = (response.status_code == 200 and
                      data.get('success') == True and
                      data.get('provider') == provider)

            self.print_result(success, f"Provider '{provider}' configured successfully")
            return success
        except Exception as e:
            self.print_result(False, f"Set provider failed: {str(e)}")
            return False

    def test_current_provider_configured(self, expected_provider: str) -> bool:
        """Test that provider is now configured"""
        self.print_test(f"Check Provider Status (Should be {expected_provider})")
        try:
            response = self.session.get(f"{self.base_url}/api/current-provider")
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")

            success = (response.status_code == 200 and
                      data.get('configured') == True and
                      data.get('provider') == expected_provider)

            self.print_result(success, f"Provider '{expected_provider}' is active")
            return success
        except Exception as e:
            self.print_result(False, f"Check configured provider failed: {str(e)}")
            return False

    def test_simple_query(self, query: str = "What is 2+2?") -> Optional[Dict]:
        """Test a simple query"""
        self.print_test(f"Simple Query: '{query}'")
        try:
            response = self.session.post(
                f"{self.base_url}/api/query",
                json={'query': query}
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            print(f"Query: {data.get('query')}")
            print(f"Response: {data.get('response', 'N/A')[:200]}...")
            print(f"Model: {data.get('model_used')}")

            decision = data.get('routing_decision', {})
            print(f"\nPrivacy Analysis:")
            print(f"  Sensitivity Score: {decision.get('sensitivity_score', 0):.2f}")
            print(f"  Anonymization: {decision.get('anonymization_needed', False)}")
            print(f"  Patterns: {decision.get('detected_patterns', [])}")

            success = response.status_code == 200 and 'response' in data

            self.print_result(success, "Query processed successfully")
            return data if success else None
        except Exception as e:
            self.print_result(False, f"Simple query failed: {str(e)}")
            return None

    def test_privacy_query_low_sensitivity(self) -> Optional[Dict]:
        """Test query with low sensitivity (should not be anonymized)"""
        query = "What's the weather like in Paris today?"
        self.print_test(f"Low Sensitivity Query: '{query}'")
        try:
            response = self.session.post(
                f"{self.base_url}/api/query",
                json={'query': query}
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            decision = data.get('routing_decision', {})

            print(f"Sensitivity Score: {decision.get('sensitivity_score', 0):.2f}")
            print(f"Anonymization Applied: {decision.get('anonymization_needed', False)}")
            print(f"Detected Patterns: {decision.get('detected_patterns', [])}")

            success = (response.status_code == 200 and
                      decision.get('sensitivity_score', 1.0) < 0.3 and
                      decision.get('anonymization_needed') == False)

            self.print_result(success, "Low sensitivity query correctly NOT anonymized")
            return data if success else None
        except Exception as e:
            self.print_result(False, f"Low sensitivity test failed: {str(e)}")
            return None

    def test_privacy_query_high_sensitivity(self) -> Optional[Dict]:
        """Test query with high sensitivity (should be anonymized)"""
        query = "My email is john.doe@example.com and I need help with my taxes"
        self.print_test(f"High Sensitivity Query (PII): '{query}'")
        try:
            response = self.session.post(
                f"{self.base_url}/api/query",
                json={'query': query}
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            decision = data.get('routing_decision', {})

            print(f"Original Query: {query}")
            print(f"Processed Query: {data.get('processed_query', 'N/A')}")
            print(f"Sensitivity Score: {decision.get('sensitivity_score', 0):.2f}")
            print(f"Anonymization Applied: {decision.get('anonymization_needed', False)}")
            print(f"Detected Patterns: {decision.get('detected_patterns', [])}")

            success = (response.status_code == 200 and
                      decision.get('sensitivity_score', 0) > 0.3 and
                      decision.get('anonymization_needed') == True)

            self.print_result(success, "High sensitivity query correctly anonymized")
            return data if success else None
        except Exception as e:
            self.print_result(False, f"High sensitivity test failed: {str(e)}")
            return None

    def test_privacy_query_personal_context(self) -> Optional[Dict]:
        """Test query with personal context"""
        query = "I'm having trouble with my mortgage payment and need advice"
        self.print_test(f"Personal Context Query: '{query}'")
        try:
            response = self.session.post(
                f"{self.base_url}/api/query",
                json={'query': query}
            )
            data = response.json()

            print(f"Status Code: {response.status_code}")
            decision = data.get('routing_decision', {})

            print(f"Original Query: {query}")
            print(f"Processed Query: {data.get('processed_query', 'N/A')}")
            print(f"Sensitivity Score: {decision.get('sensitivity_score', 0):.2f}")
            print(f"Anonymization Applied: {decision.get('anonymization_needed', False)}")
            print(f"Detected Patterns: {decision.get('detected_patterns', [])}")

            success = (response.status_code == 200 and
                      decision.get('sensitivity_score', 0) > 0.3 and
                      decision.get('anonymization_needed') == True)

            self.print_result(success, "Personal context query correctly anonymized")
            return data if success else None
        except Exception as e:
            self.print_result(False, f"Personal context test failed: {str(e)}")
            return None

    def run_all_tests(self, provider: str = None, api_key: str = None):
        """Run all tests"""
        self.print_header("MULTI-LLM PRIVACY CHAT API TEST SUITE")

        results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }

        def record_result(passed: bool):
            results['total'] += 1
            if passed:
                results['passed'] += 1
            else:
                results['failed'] += 1

        # Phase 1: Basic API Tests (No Auth Required)
        self.print_header("PHASE 1: Basic API Tests")
        record_result(self.test_health_check())
        record_result(self.test_get_providers())
        record_result(self.test_current_provider_empty())
        record_result(self.test_query_without_provider())
        record_result(self.test_set_provider_invalid_key())

        # Phase 2: Authentication Tests (Requires Valid API Key)
        if provider and api_key:
            self.print_header(f"PHASE 2: Authentication & Configuration Tests ({provider})")
            if self.test_set_provider_valid_key(provider, api_key):
                record_result(True)
                record_result(self.test_current_provider_configured(provider))

                # Phase 3: Query Tests
                self.print_header("PHASE 3: Query & Privacy Protection Tests")
                record_result(self.test_simple_query() is not None)
                record_result(self.test_privacy_query_low_sensitivity() is not None)
                record_result(self.test_privacy_query_high_sensitivity() is not None)
                record_result(self.test_privacy_query_personal_context() is not None)
            else:
                record_result(False)
                print("\n⚠️  Skipping query tests - provider configuration failed")
        else:
            print("\n⚠️  Skipping authentication and query tests")
            print("    To run full test suite, provide provider and API key:")
            print("    python test_api.py --provider claude --api-key YOUR_KEY")

        # Summary
        self.print_header("TEST SUMMARY")
        print(f"Total Tests: {results['total']}")
        print(f"✅ Passed: {results['passed']}")
        print(f"❌ Failed: {results['failed']}")

        success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")

        if results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {results['failed']} test(s) failed")

        return results['failed'] == 0

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Test Multi-LLM Privacy Chat API')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL of the API')
    parser.add_argument('--provider', help='Provider to test (claude, chatgpt, gemini, grok)')
    parser.add_argument('--api-key', help='API key for the provider')

    args = parser.parse_args()

    print("🚀 Multi-LLM Privacy Chat API Tester")
    print(f"Target: {args.url}")

    if not args.provider or not args.api_key:
        print("\n⚠️  No API credentials provided - running basic tests only")
        print("    Use --provider and --api-key to run full test suite")
        print("\nExample:")
        print("  python test_api.py --provider claude --api-key sk-ant-...")

    tester = MultiLLMAPITester(args.url)
    success = tester.run_all_tests(args.provider, args.api_key)

    return 0 if success else 1

if __name__ == '__main__':
    exit(main())
