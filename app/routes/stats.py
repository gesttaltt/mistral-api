"""
Usage statistics endpoints
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from ..models import UsageStatsResponse
from ..utils import log_api_usage, TimingContext
from ..database import db_manager

router = APIRouter(prefix="/v1", tags=["stats"])


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    http_request: Request,
    background_tasks: BackgroundTasks,
    hours: int = 24
):
    """Get API usage statistics"""
    with TimingContext() as timer:
        try:
            stats_data = await db_manager.get_usage_stats(hours)

            response = UsageStatsResponse(
                stats=stats_data["stats"],
                period_hours=stats_data["period_hours"],
                generated_at=stats_data["generated_at"]
            )

            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/stats", None,
                {"hours": hours}, 200, timer.elapsed_ms
            )

            return response

        except Exception as e:
            error_msg = str(e)
            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/stats", None,
                {"hours": hours}, 500, timer.elapsed_ms, error_msg
            )
            raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")