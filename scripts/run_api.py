#!/usr/bin/env python3
"""
API Server Runner
Simplified script to start the Mistral API server with proper environment setup
"""

import os
import sys
from pathlib import Path

# Add API directory to Python path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))
sys.path.insert(0, str(api_dir.parent))  # Add orchestrator directory

def load_env_file():
    """Load environment variables from .env file if it exists"""
    env_file = api_dir / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print(f"✅ Loaded environment from {env_file}")
    else:
        print("⚠️  No .env file found. Using environment variables or defaults.")
        print(f"📝 Copy .env.example to .env and configure your database URL")

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import asyncpg
        import pydantic
        print("✅ All required packages are available")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def main():
    """Main entry point"""
    print("🚀 Starting Mistral API Server...")
    print("="*50)

    # Load environment
    load_env_file()

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url or 'localhost' in database_url or 'password@host' in database_url:
        print("❌ DATABASE_URL not properly configured")
        print("Please set your Render PostgreSQL URL in .env file")
        sys.exit(1)

    # Import and run server
    try:
        from config.settings import settings

        print(f"🌐 Starting server on {settings.API_HOST}:{settings.API_PORT}")
        print(f"📊 Database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
        print(f"🤖 Model server: {settings.MODEL_SERVER_HOST}:{settings.MODEL_SERVER_PORT}")
        print("="*50)

        # Import uvicorn and run
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=False,
            log_level="info",
            access_log=True
        )

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()