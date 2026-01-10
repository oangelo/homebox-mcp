"""Configuration management for Homebox MCP Server."""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

# Path for storing auto-generated token
TOKEN_FILE = Path("/data/mcp_auth_token.txt")


def _load_or_generate_token(configured_token: str, auth_enabled: bool) -> str:
    """Load token from config, file, or generate a new one.
    
    Priority:
    1. Token from config/environment (if not empty)
    2. Token from file (if exists)
    3. Generate new token (if auth enabled)
    """
    # If token is configured, use it
    if configured_token:
        return configured_token
    
    # If auth is disabled, no token needed
    if not auth_enabled:
        return ""
    
    # Try to load from file
    if TOKEN_FILE.exists():
        try:
            token = TOKEN_FILE.read_text().strip()
            if token:
                return token
        except Exception:
            pass
    
    # Generate new token
    token = secrets.token_urlsafe(32)
    
    # Save to file for persistence
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token)
    except Exception:
        # If we can't save, still return the token (it will be regenerated on restart)
        pass
    
    return token


@dataclass
class Config:
    """Configuration for the Homebox MCP Server."""

    homebox_url: str
    homebox_token: str
    mcp_auth_enabled: bool
    _mcp_auth_token_configured: str = field(repr=False)
    log_level: str = "info"
    server_host: str = "0.0.0.0"
    server_port: int = 8099
    _mcp_auth_token: str = field(default="", init=False, repr=False)
    _token_was_auto_generated: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """Initialize the MCP auth token after dataclass init."""
        self._mcp_auth_token = _load_or_generate_token(
            self._mcp_auth_token_configured, 
            self.mcp_auth_enabled
        )
        # Track if token was auto-generated
        self._token_was_auto_generated = (
            self.mcp_auth_enabled 
            and not self._mcp_auth_token_configured 
            and self._mcp_auth_token
        )

    @property
    def mcp_auth_token(self) -> str:
        """Get the MCP authentication token."""
        return self._mcp_auth_token

    @property
    def token_was_auto_generated(self) -> bool:
        """Check if the token was auto-generated."""
        return self._token_was_auto_generated

    @classmethod
    def from_environment(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            homebox_url=os.environ.get("HOMEBOX_URL", "http://localhost:7745"),
            homebox_token=os.environ.get("HOMEBOX_TOKEN", ""),
            mcp_auth_enabled=os.environ.get("MCP_AUTH_ENABLED", "false").lower() == "true",
            _mcp_auth_token_configured=os.environ.get("MCP_AUTH_TOKEN", ""),
            log_level=os.environ.get("LOG_LEVEL", "info"),
            server_host=os.environ.get("SERVER_HOST", "0.0.0.0"),
            server_port=int(os.environ.get("SERVER_PORT", "8099")),
        )

    @property
    def api_base_url(self) -> str:
        """Get the base URL for the Homebox API."""
        return f"{self.homebox_url.rstrip('/')}/api/v1"


# Global configuration instance
config = Config.from_environment()
