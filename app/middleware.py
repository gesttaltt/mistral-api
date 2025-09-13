#!/usr/bin/env python3
"""
Security Middleware for Mistral API
Implements request interception and security validation
"""

import time
import json
import logging
from typing import Callable, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from .security import security_manager

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce security policies on all requests"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ['/health', '/docs', '/redoc', '/openapi.json']

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security pipeline"""
        start_time = time.time()

        # Skip security checks for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        try:
            # Extract authorization credentials
            credentials = None
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                credentials = HTTPAuthorizationCredentials(
                    scheme='Bearer',
                    credentials=auth_header.split(' ', 1)[1]
                )

            # Validate request
            validation_result = await security_manager.validate_request(request, credentials)

            if not validation_result["allowed"]:
                # Log security violation
                logger.warning(
                    f"Security violation from {validation_result['client_ip']}: "
                    f"{', '.join(validation_result['errors'])}"
                )

                # Determine appropriate error response
                error_code = validation_result["errors"][0].split(':')[0] if validation_result["errors"] else "SECURITY_VIOLATION"

                if "API_KEY" in error_code:
                    status_code = status.HTTP_401_UNAUTHORIZED
                    message = "Invalid or missing API key"
                elif "RATE_LIMITED" in error_code:
                    status_code = status.HTTP_429_TOO_MANY_REQUESTS
                    message = "Rate limit exceeded"
                elif "IP_BLOCKED" in error_code:
                    status_code = status.HTTP_403_FORBIDDEN
                    message = "Access denied"
                else:
                    status_code = status.HTTP_400_BAD_REQUEST
                    message = "Request validation failed"

                return JSONResponse(
                    status_code=status_code,
                    content={
                        "error": {
                            "code": error_code,
                            "message": message,
                            "type": "security_error"
                        }
                    }
                )

            # Add security info to request state for downstream use
            request.state.security_validation = validation_result
            request.state.client_ip = validation_result["client_ip"]

            # Continue processing
            response = await call_next(request)

            # Add security headers to response
            self._add_security_headers(response)

            # Log successful request
            processing_time = time.time() - start_time
            logger.info(
                f"Request processed: {request.method} {request.url.path} "
                f"from {validation_result['client_ip']} "
                f"({processing_time:.3f}s)"
            )

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "SECURITY_MIDDLEWARE_ERROR",
                        "message": "Internal security validation error",
                        "type": "internal_error"
                    }
                }
            )

    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"


async def validate_chat_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize chat completion request"""
    validation_result = {
        "valid": False,
        "sanitized_data": {},
        "errors": [],
        "warnings": []
    }

    try:
        # Extract and validate messages
        messages = request_data.get("messages", [])
        if not messages:
            validation_result["errors"].append("MESSAGES_MISSING: No messages provided")
            return validation_result

        # Validate each message
        sanitized_messages = []
        total_content_length = 0

        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                validation_result["errors"].append(f"MESSAGE_INVALID: Message {i} is not a valid object")
                return validation_result

            role = message.get("role", "").lower()
            content = message.get("content", "")

            # Validate role
            if role not in ["user", "assistant", "system"]:
                validation_result["errors"].append(f"ROLE_INVALID: Invalid role '{role}' in message {i}")
                return validation_result

            # Validate content
            if not content or not isinstance(content, str):
                validation_result["errors"].append(f"CONTENT_INVALID: Invalid content in message {i}")
                return validation_result

            # Security check for content
            content_validation = security_manager.validate_prompt_content(content)
            if not content_validation["safe"]:
                validation_result["errors"].extend([
                    f"MESSAGE_{i}_" + error for error in content_validation["errors"]
                ])
                return validation_result

            total_content_length += len(content_validation["sanitized_prompt"])

            sanitized_messages.append({
                "role": role,
                "content": content_validation["sanitized_prompt"]
            })

            # Add warnings if content was sanitized
            if content_validation["warnings"]:
                validation_result["warnings"].extend([
                    f"MESSAGE_{i}_" + warning for warning in content_validation["warnings"]
                ])

        # Check total content length
        if total_content_length > security_manager.config.max_prompt_length:
            validation_result["errors"].append(
                f"TOTAL_CONTENT_TOO_LONG: Combined message content exceeds "
                f"{security_manager.config.max_prompt_length} characters"
            )
            return validation_result

        # Validate parameters
        max_tokens = request_data.get("max_tokens", 300)
        temperature = request_data.get("temperature", 0.7)

        param_validation = security_manager.validate_parameters(max_tokens, temperature)
        if param_validation["errors"]:
            validation_result["errors"].extend(param_validation["errors"])
            # Don't return here, just adjust parameters

        # Build sanitized request data
        validation_result["sanitized_data"] = {
            "messages": sanitized_messages,
            "model": request_data.get("model", "mistral-7b-instruct"),
            "temperature": param_validation["adjusted_params"].get("temperature", temperature),
            "max_tokens": param_validation["adjusted_params"].get("max_tokens", max_tokens),
            "session_id": request_data.get("session_id")
        }

        # Add parameter adjustment warnings
        if param_validation["adjusted_params"]:
            validation_result["warnings"].append(
                f"PARAMETERS_ADJUSTED: {list(param_validation['adjusted_params'].keys())}"
            )

        validation_result["valid"] = True
        return validation_result

    except Exception as e:
        logger.error(f"Chat request validation error: {e}")
        validation_result["errors"].append(f"VALIDATION_ERROR: {str(e)}")
        return validation_result


async def validate_completion_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize simple completion request"""
    validation_result = {
        "valid": False,
        "sanitized_data": {},
        "errors": [],
        "warnings": []
    }

    try:
        # Extract prompt
        prompt = request_data.get("prompt", "")
        if not prompt:
            validation_result["errors"].append("PROMPT_MISSING: No prompt provided")
            return validation_result

        # Security check for prompt
        content_validation = security_manager.validate_prompt_content(prompt)
        if not content_validation["safe"]:
            validation_result["errors"].extend(content_validation["errors"])
            return validation_result

        # Validate parameters
        max_tokens = request_data.get("max_tokens", 300)
        temperature = request_data.get("temperature", 0.7)

        param_validation = security_manager.validate_parameters(max_tokens, temperature)
        if param_validation["errors"]:
            validation_result["errors"].extend(param_validation["errors"])

        # Build sanitized request data
        validation_result["sanitized_data"] = {
            "prompt": content_validation["sanitized_prompt"],
            "model": request_data.get("model", "mistral-7b-instruct"),
            "temperature": param_validation["adjusted_params"].get("temperature", temperature),
            "max_tokens": param_validation["adjusted_params"].get("max_tokens", max_tokens),
            "session_id": request_data.get("session_id")
        }

        # Add warnings
        if content_validation["warnings"]:
            validation_result["warnings"].extend(content_validation["warnings"])

        if param_validation["adjusted_params"]:
            validation_result["warnings"].append(
                f"PARAMETERS_ADJUSTED: {list(param_validation['adjusted_params'].keys())}"
            )

        validation_result["valid"] = True
        return validation_result

    except Exception as e:
        logger.error(f"Completion request validation error: {e}")
        validation_result["errors"].append(f"VALIDATION_ERROR: {str(e)}")
        return validation_result