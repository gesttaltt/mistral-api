"""
Simple completion endpoints
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from ..models import CompletionRequest, CompletionResponse
from ..utils import log_api_usage, TimingContext
from ..database import db_manager, ConversationRecord

router = APIRouter(prefix="/v1", tags=["completions"])

# Import server state from main module
from ..main import server_state


async def log_conversation(
    session_id: str,
    user_message: str,
    assistant_response: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    response_time_ms: int,
    tokens_generated: int
):
    """Background task to log conversation"""
    try:
        record = ConversationRecord(
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            response_time_ms=response_time_ms,
            tokens_generated=tokens_generated
        )
        await db_manager.save_conversation(record)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log conversation: {e}")


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
):
    """Simple completion endpoint"""
    session_id = request.session_id or str(uuid.uuid4())

    with TimingContext() as timer:
        try:
            if not server_state.model_server or not server_state.model_server.is_running:
                raise HTTPException(status_code=503, detail="Model server not available")

            # Generate response
            result = server_state.model_server.send_completion_request(
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            if "content" not in result:
                error_msg = result.get("error", "Unknown error")
                raise HTTPException(status_code=500, detail=f"Model error: {error_msg}")

            response_text = result["content"].strip()
            tokens_generated = len(response_text.split())

            # Prepare response
            response_data = {
                "id": f"cmpl-{uuid.uuid4().hex[:8]}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "text": response_text,
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(request.prompt.split()),
                    "completion_tokens": tokens_generated,
                    "total_tokens": len(request.prompt.split()) + tokens_generated
                }
            }

            # Log to database
            background_tasks.add_task(
                log_conversation,
                session_id, request.prompt, response_text, request.model,
                request.temperature, request.max_tokens, timer.elapsed_ms, tokens_generated
            )

            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/completions", session_id,
                request.dict(), 200, timer.elapsed_ms
            )

            return response_data

        except HTTPException:
            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/completions", session_id,
                request.dict(), 500, timer.elapsed_ms, str(HTTPException)
            )
            raise
        except Exception as e:
            error_msg = str(e)
            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/completions", session_id,
                request.dict(), 500, timer.elapsed_ms, error_msg
            )
            raise HTTPException(status_code=500, detail=f"Internal error: {error_msg}")