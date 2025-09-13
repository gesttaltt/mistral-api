#!/usr/bin/env python3
"""
PostgreSQL Database Manager
Handles connections and operations with Render PostgreSQL database
"""

import os
import asyncio
import asyncpg
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class ConversationRecord:
    id: Optional[int] = None
    session_id: str = ""
    user_message: str = ""
    assistant_response: str = ""
    model_name: str = ""
    temperature: float = 0.7
    max_tokens: int = 300
    response_time_ms: int = 0
    tokens_generated: int = 0
    created_at: Optional[datetime] = None

@dataclass
class APIUsageRecord:
    id: Optional[int] = None
    endpoint: str = ""
    client_ip: str = ""
    user_agent: str = ""
    session_id: Optional[str] = None
    request_data: Dict = None
    response_status: int = 200
    response_time_ms: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

class DatabaseManager:
    def __init__(self):
        self.connection_string = os.getenv(
            'DATABASE_URL',
            'postgresql://user:password@host:port/database'
        )
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool and create tables"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=30
            )
            await self.create_tables()
            logger.info("✅ Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False

    async def create_tables(self):
        """Create required tables if they don't exist"""
        create_conversations_table = """
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            user_message TEXT NOT NULL,
            assistant_response TEXT NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 300,
            response_time_ms INTEGER DEFAULT 0,
            tokens_generated INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        create_api_usage_table = """
        CREATE TABLE IF NOT EXISTS api_usage (
            id SERIAL PRIMARY KEY,
            endpoint VARCHAR(255) NOT NULL,
            client_ip VARCHAR(45) NOT NULL,
            user_agent TEXT,
            session_id VARCHAR(255),
            request_data JSONB,
            response_status INTEGER DEFAULT 200,
            response_time_ms INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
        CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
        CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at);
        CREATE INDEX IF NOT EXISTS idx_api_usage_client_ip ON api_usage(client_ip);
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_conversations_table)
            await conn.execute(create_api_usage_table)
            await conn.execute(create_indexes)

    async def save_conversation(self, record: ConversationRecord) -> int:
        """Save conversation record to database"""
        query = """
        INSERT INTO conversations
        (session_id, user_message, assistant_response, model_name,
         temperature, max_tokens, response_time_ms, tokens_generated)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                record.session_id,
                record.user_message,
                record.assistant_response,
                record.model_name,
                record.temperature,
                record.max_tokens,
                record.response_time_ms,
                record.tokens_generated
            )
            return row['id']

    async def save_api_usage(self, record: APIUsageRecord) -> int:
        """Save API usage record to database"""
        query = """
        INSERT INTO api_usage
        (endpoint, client_ip, user_agent, session_id, request_data,
         response_status, response_time_ms, error_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                record.endpoint,
                record.client_ip,
                record.user_agent,
                record.session_id,
                json.dumps(record.request_data) if record.request_data else None,
                record.response_status,
                record.response_time_ms,
                record.error_message
            )
            return row['id']

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[ConversationRecord]:
        """Get conversation history for a session"""
        query = """
        SELECT * FROM conversations
        WHERE session_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, session_id, limit)
            return [
                ConversationRecord(
                    id=row['id'],
                    session_id=row['session_id'],
                    user_message=row['user_message'],
                    assistant_response=row['assistant_response'],
                    model_name=row['model_name'],
                    temperature=row['temperature'],
                    max_tokens=row['max_tokens'],
                    response_time_ms=row['response_time_ms'],
                    tokens_generated=row['tokens_generated'],
                    created_at=row['created_at']
                )
                for row in reversed(rows)
            ]

    async def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get API usage statistics"""
        query = """
        SELECT
            endpoint,
            COUNT(*) as request_count,
            AVG(response_time_ms) as avg_response_time,
            COUNT(DISTINCT client_ip) as unique_clients,
            COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count
        FROM api_usage
        WHERE created_at >= NOW() - INTERVAL '%s hours'
        GROUP BY endpoint
        ORDER BY request_count DESC
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query % hours)
            return {
                'stats': [dict(row) for row in rows],
                'period_hours': hours,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔒 Database connection pool closed")

# Global database instance
db_manager = DatabaseManager()