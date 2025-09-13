"""
Configuration settings for the API server
"""

import os
from typing import Optional


class Settings:
    """Application settings"""

    # Database settings
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@host:port/database'
    )

    # API server settings
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '9000'))

    # Model settings
    MODEL_NAME: str = os.getenv('MODEL_NAME', 'mistral-7b-instruct')
    MAX_TOKENS: int = int(os.getenv('MAX_TOKENS', '4096'))
    DEFAULT_TEMPERATURE: float = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))

    # Model server settings
    MODEL_SERVER_HOST: str = os.getenv('MODEL_SERVER_HOST', '127.0.0.1')
    MODEL_SERVER_PORT: int = int(os.getenv('MODEL_SERVER_PORT', '8081'))

    # GPU settings
    GPU_LAYERS: int = int(os.getenv('GPU_LAYERS', '20'))
    CONTEXT_SIZE: int = int(os.getenv('CONTEXT_SIZE', '32768'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '2048'))
    THREADS: int = int(os.getenv('THREADS', '8'))

    # Security settings (optional)
    API_KEY: Optional[str] = os.getenv('API_KEY')

    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # CORS settings
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', '*').split(',')

    # Database pool settings
    DB_MIN_CONNECTIONS: int = int(os.getenv('DB_MIN_CONNECTIONS', '1'))
    DB_MAX_CONNECTIONS: int = int(os.getenv('DB_MAX_CONNECTIONS', '10'))
    DB_COMMAND_TIMEOUT: int = int(os.getenv('DB_COMMAND_TIMEOUT', '30'))


# Global settings instance
settings = Settings()