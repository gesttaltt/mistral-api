"""
Pydantic models for API requests and responses
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    model: str = Field(default="mistral-7b-instruct", description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=300, ge=1, le=4096, description="Maximum tokens to generate")
    session_id: Optional[str] = Field(default=None, description="Session identifier for conversation tracking")
    stream: bool = Field(default=False, description="Stream response tokens")


class ChatCompletionResponse(BaseModel):
    id: str = Field(..., description="Completion ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Completion choices")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    session_id: Optional[str] = Field(None, description="Session ID if provided")


class CompletionRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt")
    model: str = Field(default="mistral-7b-instruct", description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=300, ge=1, le=4096, description="Maximum tokens to generate")
    session_id: Optional[str] = Field(default=None, description="Session identifier")


class CompletionResponse(BaseModel):
    id: str = Field(..., description="Completion ID")
    object: str = Field(default="text_completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Completion choices")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    database_connected: bool


class ConversationHistoryResponse(BaseModel):
    session_id: str
    conversations: List[Dict[str, Any]]


class UsageStatsResponse(BaseModel):
    stats: List[Dict[str, Any]]
    period_hours: int
    generated_at: str