#!/usr/bin/env python3
"""
Security Module for Mistral API
Implements request filtering, validation, and protection for local environment
"""

import re
import time
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import logging

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import ipaddress

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    # API Authentication
    require_api_key: bool = True
    valid_api_keys: List[str] = None

    # Rate limiting
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000

    # Request filtering
    max_prompt_length: int = 8192
    max_tokens: int = 4096
    blocked_patterns: List[str] = None

    # IP filtering
    allowed_ips: List[str] = None
    blocked_ips: List[str] = None

    # Content filtering
    enable_content_filter: bool = True
    max_consecutive_requests: int = 100

    def __post_init__(self):
        if self.valid_api_keys is None:
            self.valid_api_keys = []
        if self.blocked_patterns is None:
            self.blocked_patterns = [
                r'(?i)(exec|eval|import\s+os|subprocess|__import__)',
                r'(?i)(rm\s+-rf|del\s+/|format\s+c:)',
                r'(?i)(password|secret|key|token).*=',
                r'(?i)(system|shell|cmd|powershell)\s*\(',
                r'(?i)<script[^>]*>.*?</script>',
                r'(?i)javascript:',
                r'(?i)(drop\s+table|delete\s+from|truncate)',
            ]
        if self.allowed_ips is None:
            self.allowed_ips = []
        if self.blocked_ips is None:
            self.blocked_ips = []


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque(),
            'day': deque()
        })

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is within rate limits"""
        now = datetime.now()
        client_data = self.requests[client_ip]

        # Clean old requests
        self._clean_old_requests(client_data, now)

        # Check limits
        if len(client_data['minute']) >= self.config.max_requests_per_minute:
            return False
        if len(client_data['hour']) >= self.config.max_requests_per_hour:
            return False
        if len(client_data['day']) >= self.config.max_requests_per_day:
            return False

        # Record this request
        client_data['minute'].append(now)
        client_data['hour'].append(now)
        client_data['day'].append(now)

        return True

    def _clean_old_requests(self, client_data: Dict, now: datetime):
        """Remove old requests outside time windows"""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Clean minute window
        while client_data['minute'] and client_data['minute'][0] < minute_ago:
            client_data['minute'].popleft()

        # Clean hour window
        while client_data['hour'] and client_data['hour'][0] < hour_ago:
            client_data['hour'].popleft()

        # Clean day window
        while client_data['day'] and client_data['day'][0] < day_ago:
            client_data['day'].popleft()


class ContentFilter:
    """Content filtering and sanitization"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.blocked_patterns = [re.compile(pattern) for pattern in config.blocked_patterns]

    def is_safe_content(self, text: str) -> tuple[bool, Optional[str]]:
        """Check if content is safe"""
        if not text or not isinstance(text, str):
            return False, "Invalid or empty content"

        # Length check
        if len(text) > self.config.max_prompt_length:
            return False, f"Content too long (max {self.config.max_prompt_length} chars)"

        # Pattern matching
        for pattern in self.blocked_patterns:
            if pattern.search(text):
                return False, f"Content contains blocked pattern: {pattern.pattern[:50]}..."

        return True, None

    def sanitize_text(self, text: str) -> str:
        """Sanitize input text"""
        if not text:
            return ""

        # Remove potential script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove javascript URLs
        text = re.sub(r'javascript:[^"\s]*', '', text, flags=re.IGNORECASE)

        # Remove potential command injection
        text = re.sub(r'[;&|`$()]', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text


class IPFilter:
    """IP address filtering"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.allowed_networks = []
        self.blocked_networks = []

        # Parse allowed IPs/networks
        for ip_str in config.allowed_ips:
            try:
                self.allowed_networks.append(ipaddress.ip_network(ip_str, strict=False))
            except ValueError:
                logger.warning(f"Invalid allowed IP: {ip_str}")

        # Parse blocked IPs/networks
        for ip_str in config.blocked_ips:
            try:
                self.blocked_networks.append(ipaddress.ip_network(ip_str, strict=False))
            except ValueError:
                logger.warning(f"Invalid blocked IP: {ip_str}")

    def is_allowed_ip(self, client_ip: str) -> tuple[bool, Optional[str]]:
        """Check if IP is allowed"""
        try:
            client_addr = ipaddress.ip_address(client_ip)

            # Check blocked list first
            for network in self.blocked_networks:
                if client_addr in network:
                    return False, f"IP {client_ip} is blocked"

            # If allowed list is empty, allow all (except blocked)
            if not self.allowed_networks:
                return True, None

            # Check allowed list
            for network in self.allowed_networks:
                if client_addr in network:
                    return True, None

            return False, f"IP {client_ip} not in allowed list"

        except ValueError:
            return False, f"Invalid IP address: {client_ip}"


class APIKeyValidator:
    """API key validation"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        # Hash API keys for secure storage
        self.valid_key_hashes = set()
        for key in config.valid_api_keys:
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            self.valid_key_hashes.add(key_hash)

    def is_valid_key(self, api_key: str) -> bool:
        """Validate API key"""
        if not api_key:
            return False

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return key_hash in self.valid_key_hashes

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        return secrets.token_urlsafe(32)


class SecurityManager:
    """Main security manager orchestrating all security components"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.content_filter = ContentFilter(config)
        self.ip_filter = IPFilter(config)
        self.api_key_validator = APIKeyValidator(config)
        self.security_bearer = HTTPBearer(auto_error=False)

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded IP first (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host

    async def validate_request(self, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = None) -> Dict[str, Any]:
        """Main request validation pipeline"""
        client_ip = self.get_client_ip(request)
        validation_result = {
            "client_ip": client_ip,
            "allowed": False,
            "errors": [],
            "warnings": []
        }

        # 1. IP filtering
        if self.config.allowed_ips or self.config.blocked_ips:
            ip_allowed, ip_error = self.ip_filter.is_allowed_ip(client_ip)
            if not ip_allowed:
                validation_result["errors"].append(f"IP_BLOCKED: {ip_error}")
                return validation_result

        # 2. API key validation
        if self.config.require_api_key:
            if not credentials or not credentials.credentials:
                validation_result["errors"].append("API_KEY_MISSING: Authorization header required")
                return validation_result

            if not self.api_key_validator.is_valid_key(credentials.credentials):
                validation_result["errors"].append("API_KEY_INVALID: Invalid API key")
                return validation_result

        # 3. Rate limiting
        if not self.rate_limiter.is_allowed(client_ip):
            validation_result["errors"].append("RATE_LIMITED: Too many requests")
            return validation_result

        validation_result["allowed"] = True
        return validation_result

    def validate_prompt_content(self, prompt: str) -> Dict[str, Any]:
        """Validate prompt content for security"""
        result = {
            "safe": False,
            "sanitized_prompt": "",
            "errors": [],
            "warnings": []
        }

        if not prompt:
            result["errors"].append("CONTENT_EMPTY: Prompt cannot be empty")
            return result

        # Content safety check
        is_safe, safety_error = self.content_filter.is_safe_content(prompt)
        if not is_safe:
            result["errors"].append(f"CONTENT_UNSAFE: {safety_error}")
            return result

        # Sanitize content
        sanitized = self.content_filter.sanitize_text(prompt)
        result["sanitized_prompt"] = sanitized
        result["safe"] = True

        # Check if sanitization changed the content
        if sanitized != prompt:
            result["warnings"].append("CONTENT_SANITIZED: Prompt was modified for security")

        return result

    def validate_parameters(self, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Validate request parameters"""
        result = {
            "valid": True,
            "errors": [],
            "adjusted_params": {}
        }

        # Validate max_tokens
        if max_tokens > self.config.max_tokens:
            result["errors"].append(f"MAX_TOKENS_EXCEEDED: Maximum {self.config.max_tokens} tokens allowed")
            result["adjusted_params"]["max_tokens"] = self.config.max_tokens

        # Validate temperature
        if not 0.0 <= temperature <= 2.0:
            result["errors"].append("TEMPERATURE_INVALID: Temperature must be between 0.0 and 2.0")
            result["adjusted_params"]["temperature"] = max(0.0, min(2.0, temperature))

        return result

import os

# Load security configuration from environment
def load_security_config() -> SecurityConfig:
    """Load security configuration from environment variables"""
    api_keys_str = os.getenv('API_KEYS', '')
    api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()] if api_keys_str else []

    allowed_ips_str = os.getenv('ALLOWED_IPS', '')
    allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()] if allowed_ips_str else []

    blocked_ips_str = os.getenv('BLOCKED_IPS', '')
    blocked_ips = [ip.strip() for ip in blocked_ips_str.split(',') if ip.strip()] if blocked_ips_str else []

    return SecurityConfig(
        require_api_key=os.getenv('REQUIRE_API_KEY', 'true').lower() == 'true',
        valid_api_keys=api_keys,
        max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60')),
        max_requests_per_hour=int(os.getenv('MAX_REQUESTS_PER_HOUR', '1000')),
        max_requests_per_day=int(os.getenv('MAX_REQUESTS_PER_DAY', '10000')),
        max_prompt_length=int(os.getenv('MAX_PROMPT_LENGTH', '8192')),
        max_tokens=int(os.getenv('MAX_TOKENS', '4096')),
        enable_content_filter=os.getenv('ENABLE_CONTENT_FILTER', 'true').lower() == 'true',
        max_consecutive_requests=int(os.getenv('MAX_CONSECUTIVE_REQUESTS', '100')),
        allowed_ips=allowed_ips,
        blocked_ips=blocked_ips
    )

# Global security manager instance
security_config = load_security_config()
security_manager = SecurityManager(security_config)