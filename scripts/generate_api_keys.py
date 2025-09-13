#!/usr/bin/env python3
"""
API Key Generator
Generate secure API keys for the Mistral API
"""

import sys
from pathlib import Path

# Add API directory to Python path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from app.security import APIKeyValidator

def main():
    """Generate API keys"""
    print("🔑 Mistral API Key Generator")
    print("="*40)

    try:
        num_keys = int(input("How many API keys do you want to generate? [3]: ") or "3")
    except ValueError:
        num_keys = 3

    print(f"\n🎯 Generating {num_keys} secure API keys...")
    print("="*40)

    api_keys = []
    for i in range(num_keys):
        key = APIKeyValidator.generate_api_key()
        api_keys.append(key)
        print(f"Key {i+1}: {key}")

    print("\n📋 Copy these keys to your .env file:")
    print("="*40)
    keys_string = ",".join(api_keys)
    print(f"API_KEYS={keys_string}")

    print("\n⚠️  Security Notes:")
    print("- Keep these keys secret and secure")
    print("- Don't commit them to version control")
    print("- Each key provides full API access")
    print("- Regenerate keys if compromised")
    print("- Use different keys for different applications")

    print("\n✅ API keys generated successfully!")

if __name__ == "__main__":
    main()