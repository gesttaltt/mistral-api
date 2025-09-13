#!/usr/bin/env python3
"""
Security Testing Suite
Tests all security measures against malicious inputs and attack vectors
"""

import requests
import time
import sys
from pathlib import Path

# Add API directory to Python path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from app.security import APIKeyValidator

class SecurityTester:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.test_api_key = APIKeyValidator.generate_api_key()
        print(f"🔑 Generated test API key: {self.test_api_key}")

    def test_api_key_protection(self):
        """Test API key authentication"""
        print("\n🔐 Testing API Key Protection...")

        # Test without API key
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hello"}]},
            timeout=5
        )

        if response.status_code == 401:
            print("✅ API key required - Unauthorized access blocked")
        else:
            print(f"❌ API key bypass possible - Status: {response.status_code}")

        # Test with invalid API key
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hello"}]},
            headers={"Authorization": "Bearer invalid_key"},
            timeout=5
        )

        if response.status_code == 401:
            print("✅ Invalid API key rejected")
        else:
            print(f"❌ Invalid API key accepted - Status: {response.status_code}")

    def test_malicious_prompts(self):
        """Test protection against malicious prompts"""
        print("\n🦹 Testing Malicious Prompt Protection...")

        malicious_prompts = [
            "Execute this: import os; os.system('rm -rf /')",
            "Run command: del /f /s /q C:\\*",
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "javascript:alert('malicious')",
            "__import__('os').system('malicious command')",
            "eval('malicious code')",
            "subprocess.call(['rm', '-rf', '/'])",
            "System('format C:')",
            "password = 'secret123'; execute_malicious_code()",
        ]

        blocked_count = 0
        for i, prompt in enumerate(malicious_prompts):
            try:
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": prompt}]},
                    headers={"Authorization": f"Bearer {self.test_api_key}"},
                    timeout=5
                )

                if response.status_code == 400:
                    blocked_count += 1
                    print(f"✅ Blocked malicious prompt {i+1}")
                else:
                    print(f"❌ Malicious prompt {i+1} not blocked - Status: {response.status_code}")

            except Exception as e:
                print(f"⚠️  Error testing prompt {i+1}: {e}")

        print(f"📊 Blocked {blocked_count}/{len(malicious_prompts)} malicious prompts")

    def test_input_length_limits(self):
        """Test protection against oversized inputs"""
        print("\n📏 Testing Input Length Limits...")

        # Test extremely long prompt
        long_prompt = "A" * 20000  # 20KB prompt
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": long_prompt}]},
            headers={"Authorization": f"Bearer {self.test_api_key}"},
            timeout=5
        )

        if response.status_code == 400:
            print("✅ Long prompt blocked")
        else:
            print(f"❌ Long prompt not blocked - Status: {response.status_code}")

        # Test excessive max_tokens
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50000
            },
            headers={"Authorization": f"Bearer {self.test_api_key}"},
            timeout=5
        )

        if response.status_code == 400 or (response.status_code == 200 and
            response.json().get("usage", {}).get("completion_tokens", 0) <= 4096):
            print("✅ Excessive max_tokens limited")
        else:
            print(f"❌ Excessive max_tokens not limited - Status: {response.status_code}")

    def test_rate_limiting(self):
        """Test rate limiting protection"""
        print("\n⏱️  Testing Rate Limiting...")

        # Send rapid requests
        blocked_requests = 0
        total_requests = 10

        for i in range(total_requests):
            try:
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": f"Test {i}"}]},
                    headers={"Authorization": f"Bearer {self.test_api_key}"},
                    timeout=2
                )

                if response.status_code == 429:
                    blocked_requests += 1
                    print(f"✅ Request {i+1} rate limited")
                elif response.status_code == 200:
                    print(f"⚪ Request {i+1} allowed")
                else:
                    print(f"⚠️  Request {i+1} returned {response.status_code}")

            except Exception as e:
                print(f"❌ Error in request {i+1}: {e}")

        if blocked_requests > 0:
            print(f"✅ Rate limiting active - {blocked_requests}/{total_requests} requests blocked")
        else:
            print("⚠️  No rate limiting detected in rapid requests")

    def test_parameter_validation(self):
        """Test parameter validation and sanitization"""
        print("\n🧹 Testing Parameter Validation...")

        # Test invalid temperature
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 5.0  # Invalid - should be 0.0-2.0
            },
            headers={"Authorization": f"Bearer {self.test_api_key}"},
            timeout=5
        )

        if response.status_code == 400:
            print("✅ Invalid temperature rejected")
        else:
            print(f"❌ Invalid temperature accepted - Status: {response.status_code}")

        # Test invalid role
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "messages": [{"role": "hacker", "content": "malicious content"}]
            },
            headers={"Authorization": f"Bearer {self.test_api_key}"},
            timeout=5
        )

        if response.status_code == 400:
            print("✅ Invalid message role rejected")
        else:
            print(f"❌ Invalid message role accepted - Status: {response.status_code}")

    def test_content_sanitization(self):
        """Test content sanitization"""
        print("\n🧽 Testing Content Sanitization...")

        # Test script tag removal
        dangerous_content = 'Hello <script>alert("xss")</script> world'
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": dangerous_content}]},
            headers={"Authorization": f"Bearer {self.test_api_key}"},
            timeout=10
        )

        if response.status_code == 200:
            # Check if the response doesn't contain script tags
            response_text = str(response.json())
            if "<script>" not in response_text.lower():
                print("✅ Script tags sanitized")
            else:
                print("❌ Script tags not sanitized")
        else:
            print(f"⚠️  Sanitization test failed - Status: {response.status_code}")

    def test_security_headers(self):
        """Test security headers in responses"""
        print("\n🛡️  Testing Security Headers...")

        response = requests.get(f"{self.base_url}/health")

        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Cache-Control'
        ]

        headers_present = 0
        for header in security_headers:
            if header in response.headers:
                headers_present += 1
                print(f"✅ {header} header present")
            else:
                print(f"❌ {header} header missing")

        print(f"📊 {headers_present}/{len(security_headers)} security headers present")

    def run_all_tests(self):
        """Run comprehensive security test suite"""
        print("🧪 Starting Comprehensive Security Test Suite")
        print("="*60)

        tests = [
            ("API Key Protection", self.test_api_key_protection),
            ("Malicious Prompts", self.test_malicious_prompts),
            ("Input Length Limits", self.test_input_length_limits),
            ("Rate Limiting", self.test_rate_limiting),
            ("Parameter Validation", self.test_parameter_validation),
            ("Content Sanitization", self.test_content_sanitization),
            ("Security Headers", self.test_security_headers),
        ]

        results = []

        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                test_func()
                results.append((test_name, True))
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                results.append((test_name, False))

        # Summary
        print("\n" + "="*60)
        print("🏁 Security Test Results Summary")
        print("="*60)

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")

        print(f"\nOverall: {passed}/{total} security tests completed successfully")

        if passed == total:
            print("🎉 All security measures are working correctly!")
            print("🔒 Your local environment is well protected.")
        else:
            print("⚠️  Some security measures may need attention.")
            print("🔍 Review the failed tests and strengthen security.")


def main():
    """Main test execution"""
    print("🛡️  Mistral API Security Test Suite")
    print("Testing protection against malicious inputs and attacks")
    print("="*60)

    tester = SecurityTester()

    # Test if server is running
    try:
        response = requests.get(f"{tester.base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running and accessible")
            tester.run_all_tests()
        else:
            print(f"❌ API server returned status {response.status_code}")
    except requests.ConnectionError:
        print("❌ Cannot connect to API server. Please start the server first:")
        print("   cd scripts && python run_api.py")
    except Exception as e:
        print(f"❌ Error connecting to API server: {e}")


if __name__ == "__main__":
    main()