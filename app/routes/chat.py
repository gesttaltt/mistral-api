"""
Chat completion endpoints
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from ..models import ChatCompletionRequest, ChatCompletionResponse
from ..utils import log_api_usage, TimingContext
from ..database import db_manager, ConversationRecord

router = APIRouter(prefix="/v1/chat", tags=["chat"])

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


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
):
    """OpenAI-compatible chat completions endpoint"""
    session_id = request.session_id or str(uuid.uuid4())
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

    with TimingContext() as timer:
        try:
            if not server_state.model_server or not server_state.model_server.is_running:
                raise HTTPException(status_code=503, detail="Model server not available")

            # Extract user message (last message should be from user)
            if not request.messages or request.messages[-1].role != "user":
                raise HTTPException(status_code=400, detail="Last message must be from user")

            user_message = request.messages[-1].content

            # Build context from conversation history
            conversation_context = ""
            for msg in request.messages[:-1]:
                if msg.role == "user":
                    conversation_context += f"User: {msg.content}\n"
                elif msg.role == "assistant":
                    conversation_context += f"Assistant: {msg.content}\n"

            # Prepare prompt
            if conversation_context:
                full_prompt = f"{conversation_context}User: {user_message}\nAssistant:"
            else:
                full_prompt = user_message

            # Generate response
            result = server_state.model_server.send_completion_request(
                prompt=full_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            if "content" not in result:
                error_msg = result.get("error", "Unknown error")
                raise HTTPException(status_code=500, detail=f"Model error: {error_msg}")

            assistant_response = result["content"].strip()

            # Clean up response
            if "Assistant:" in assistant_response:
                assistant_response = assistant_response.split("Assistant:")[-1].strip()

            # Calculate metrics
            tokens_generated = len(assistant_response.split())

            # Prepare response
            response = ChatCompletionResponse(
                id=completion_id,
                created=int(time.time()),
                model=request.model,
                session_id=session_id,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": assistant_response
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": len(full_prompt.split()),
                    "completion_tokens": tokens_generated,
                    "total_tokens": len(full_prompt.split()) + tokens_generated
                }
            )

            # Log to database
            background_tasks.add_task(
                log_conversation,
                session_id, user_message, assistant_response, request.model,
                request.temperature, request.max_tokens, timer.elapsed_ms, tokens_generated
            )

            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/chat/completions", session_id,
                request.dict(), 200, timer.elapsed_ms
            )

            return response

        except HTTPException:
            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/chat/completions", session_id,
                request.dict(), 500, timer.elapsed_ms, str(HTTPException)
            )
            raise
        except Exception as e:
            error_msg = str(e)
            background_tasks.add_task(
                log_api_usage,
                http_request, "/v1/chat/completions", session_id,
                request.dict(), 500, timer.elapsed_ms, error_msg
            )
            raise HTTPException(status_code=500, detail=f"Internal error: {error_msg}")