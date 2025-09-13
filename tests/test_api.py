#!/usr/bin/env python3
"""
API Testing Script
Test the Mistral API endpoints to verify functionality
"""

import requests
import json
import time
import uuid
import sys
from pathlib import Path

# Add API directory to Python path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

def test_health_endpoint(base_url: str):
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   Model loaded: {data.get('model_loaded')}")
            print(f"   Database connected: {data.get('database_connected')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_chat_completion(base_url: str, session_id: str):
    """Test the chat completion endpoint"""
    print("\n💬 Testing chat completion endpoint...")

    payload = {
        "messages": [
            {"role": "user", "content": "Hello! Can you tell me a fun fact about space?"}
        ],
        "model": "mistral-7b-instruct",
        "temperature": 0.7,
        "max_tokens": 150,
        "session_id": session_id
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Chat completion successful")
            print(f"   Response: {data['choices'][0]['message']['content'][:100]}...")
            print(f"   Tokens used: {data['usage']['total_tokens']}")
            print(f"   Session ID: {data.get('session_id')}")
            return True
        else:
            print(f"❌ Chat completion failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat completion error: {e}")
        return False

def test_simple_completion(base_url: str, session_id: str):
    """Test the simple completion endpoint"""
    print("\n📝 Testing simple completion endpoint...")

    payload = {
        "prompt": "Explain what machine learning is in simple terms:",
        "model": "mistral-7b-instruct",
        "temperature": 0.5,
        "max_tokens": 100,
        "session_id": session_id
    }

    try:
        response = requests.post(
            f"{base_url}/v1/completions",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Simple completion successful")
            print(f"   Response: {data['choices'][0]['text'][:100]}...")
            print(f"   Tokens used: {data['usage']['total_tokens']}")
            return True
        else:
            print(f"❌ Simple completion failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Simple completion error: {e}")
        return False

def test_conversation_history(base_url: str, session_id: str):
    """Test the conversation history endpoint"""
    print("\n📚 Testing conversation history endpoint...")

    try:
        response = requests.get(
            f"{base_url}/v1/conversations/{session_id}",
            params={"limit": 5},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Conversation history retrieved")
            print(f"   Session: {data['session_id']}")
            print(f"   Conversations: {len(data['conversations'])}")
            return True
        else:
            print(f"❌ Conversation history failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Conversation history error: {e}")
        return False

def test_usage_stats(base_url: str):
    """Test the usage stats endpoint"""
    print("\n📊 Testing usage stats endpoint...")

    try:
        response = requests.get(
            f"{base_url}/v1/stats",
            params={"hours": 24},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Usage stats retrieved")
            print(f"   Period: {data['period_hours']} hours")
            print(f"   Endpoints tracked: {len(data['stats'])}")
            return True
        else:
            print(f"❌ Usage stats failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Usage stats error: {e}")
        return False

def main():
    """Main test function"""
    base_url = "http://localhost:9000"
    session_id = str(uuid.uuid4())

    print("🧪 Mistral API Test Suite")
    print("="*50)
    print(f"Testing API at: {base_url}")
    print(f"Test session ID: {session_id}")
    print("="*50)

    tests = [
        ("Health Check", lambda: test_health_endpoint(base_url)),
        ("Chat Completion", lambda: test_chat_completion(base_url, session_id)),
        ("Simple Completion", lambda: test_simple_completion(base_url, session_id)),
        ("Conversation History", lambda: test_conversation_history(base_url, session_id)),
        ("Usage Stats", lambda: test_usage_stats(base_url))
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
        if not success:
            print(f"⚠️  {test_name} failed - API may not be fully functional")

    # Summary
    print("\n" + "="*50)
    print("🏁 Test Results Summary")
    print("="*50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the API server logs for details.")

if __name__ == "__main__":
    main()