#!/usr/bin/env python3
"""
Mistral API Server - Main Application
FastAPI server that exposes local Mistral model via REST API
Integrates with PostgreSQL database for logging and conversation storage
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from .database import db_manager, ConversationRecord, APIUsageRecord
from .model_server import MistralServerManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServerState:
    """Global server state"""
    model_server: Optional[MistralServerManager] = None

server_state = ServerState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Mistral API Server...")

    # Initialize database
    if not await db_manager.initialize():
        raise RuntimeError("Failed to initialize database")

    # Start model server
    server_state.model_server = MistralServerManager()
    if not server_state.model_server.start_server():
        raise RuntimeError("Failed to start Mistral model server")

    logger.info("✅ Mistral API Server ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Mistral API Server...")
    if server_state.model_server:
        server_state.model_server.stop_server()
    await db_manager.close()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Mistral Local API",
    description="REST API for local Mistral 7B model with PostgreSQL logging",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import route modules
from .routes import health, chat, completions, conversations, stats

# Register routes
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(completions.router)
app.include_router(conversations.router)
app.include_router(stats.router)

def create_app() -> FastAPI:
    """Factory function to create FastAPI app"""
    return app

def run_server(host: str = "0.0.0.0", port: int = 9000, reload: bool = False):
    """Run the API server"""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mistral API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()
    run_server(args.host, args.port, args.reload)