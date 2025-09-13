"""
Conversation history endpoints
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from ..models import ConversationHistoryResponse
from ..utils import log_api_usage, TimingContext
from ..database import db_manager

router = APIRouter(prefix="/v1", tags=["conversations"])


@router.get("/conversations/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    http_request: Request,
    background_tasks: BackgroundTasks,
    limit: int = 10
):
    """Get conversation history for a session"""
    with TimingContext() as timer:
        try:
            history = await db_manager.get_conversation_history(session_id, limit)

            response = ConversationHistoryResponse(
                session_id=session_id,
                conversations=[
                    {
                        "id": conv.id,
                        "user_message": conv.user_message,
                        "assistant_response": conv.assistant_response,
                        "model_name": conv.model_name,
                        "temperature": conv.temperature,
                        "max_tokens": conv.max_tokens,
                        "response_time_ms": conv.response_time_ms,
                        "tokens_generated": conv.tokens_generated,
                        "created_at": conv.created_at.isoformat() if conv.created_at else None
                    }
                    for conv in history
                ]
            )

            background_tasks.add_task(
                log_api_usage,
                http_request, f"/v1/conversations/{session_id}", session_id,
                {"limit": limit}, 200, timer.elapsed_ms
            )

            return response

        except Exception as e:
            error_msg = str(e)
            background_tasks.add_task(
                log_api_usage,
                http_request, f"/v1/conversations/{session_id}", session_id,
                {"limit": limit}, 500, timer.elapsed_ms, error_msg
            )
            raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")