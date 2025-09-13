"""
Health check endpoints
"""

import time
from fastapi import APIRouter, Request, BackgroundTasks

from ..models import HealthResponse
from ..utils import log_api_usage, TimingContext
from ..database import db_manager

router = APIRouter(prefix="/health", tags=["health"])

# Import server state from main module
from ..main import server_state


@router.get("/", response_model=HealthResponse)
async def health_check(request: Request, background_tasks: BackgroundTasks):
    """Health check endpoint"""
    with TimingContext() as timer:
        # Check model server
        model_healthy = server_state.model_server and server_state.model_server.test_server_health()

        # Check database
        db_healthy = db_manager.pool is not None

        response = HealthResponse(
            status="healthy" if model_healthy and db_healthy else "unhealthy",
            model_loaded=model_healthy,
            uptime_seconds=time.time(),
            database_connected=db_healthy
        )

    background_tasks.add_task(
        log_api_usage,
        request, "/health", None, {}, 200, timer.elapsed_ms
    )

    return response