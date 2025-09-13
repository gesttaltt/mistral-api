"""
Utility functions for the API server
"""

import time
import logging
from typing import Optional, Dict
from fastapi import Request

from .database import db_manager, APIUsageRecord

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


async def log_api_usage(
    request: Request,
    endpoint: str,
    session_id: Optional[str],
    request_data: Dict,
    response_status: int,
    response_time_ms: int,
    error_message: Optional[str] = None
):
    """Log API usage to database"""
    try:
        usage_record = APIUsageRecord(
            endpoint=endpoint,
            client_ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
            session_id=session_id,
            request_data=request_data,
            response_status=response_status,
            response_time_ms=response_time_ms,
            error_message=error_message
        )
        await db_manager.save_api_usage(usage_record)
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")


class TimingContext:
    """Context manager for timing operations"""
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()

    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds"""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0