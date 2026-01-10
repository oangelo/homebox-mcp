"""Configuration management for Homebox MCP Server."""

import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Path for storing auto-generated token
TOKEN_FILE = Path("/data/mcp_auth_token.txt")


def _log(message: str) -> None:
    """Simple logging before logging module is configured."""
    print(f"[CONFIG] {message}", file=sys.stderr, flush=True)


def _load_or_generate_token(configured_token: str, auth_enabled: bool) -> str:
    """Load token from config, file, or generate a new one.
    
    Priority:
    1. Token from config/environment (if not empty)
    2. Token from file (if exists)
    3. Generate new token (if auth enabled)
    """
    # If token is configured, use it
    if configured_token:
        _log(f"Using configured MCP auth token (length: {len(configured_token)})")
        return configured_token
    
    # If auth is disabled, no token needed
    if not auth_enabled:
        _log("MCP auth disabled, no token needed")
        return ""
    
    _log(f"MCP auth enabled, looking for token...")
    _log(f"Token file path: {TOKEN_FILE}")
    
    # Try to load from file
    if TOKEN_FILE.exists():
        _log(f"Token file exists, loading...")
        try:
            token = TOKEN_FILE.read_text().strip()
            if token:
                _log(f"Loaded existing token from file (length: {len(token)})")
                return token
            else:
                _log("Token file was empty")
        except Exception as e:
            _log(f"Error reading token file: {e}")
    else:
        _log("Token file does not exist")
    
    # Generate new token
    _log("Generating new token...")
    token = secrets.token_urlsafe(32)
    _log(f"Generated new token (length: {len(token)})")
    
    # Save to file for persistence
    try:
        _log(f"Saving token to {TOKEN_FILE}...")
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token)
        _log("Token saved successfully")
    except Exception as e:
        _log(f"Error saving token to file: {e}")
        _log("Token will be regenerated on next restart")
    
    # Print token to logs so user can see it
    _log("=" * 60)
    _log("AUTO-GENERATED MCP AUTH TOKEN:")
    _log(f"  {token}")
    _log("Copy this token to Claude.ai 'Segredo do Cliente OAuth'")
    _log("=" * 60)
    
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
        _log(f"Initializing config, mcp_auth_enabled={self.mcp_auth_enabled}")
        self._mcp_auth_token = _load_or_generate_token(
            self._mcp_auth_token_configured, 
            self.mcp_auth_enabled
        )
        # Track if token was auto-generated
        self._token_was_auto_generated = (
            self.mcp_auth_enabled 
            and not self._mcp_auth_token_configured 
            and bool(self._mcp_auth_token)
        )
        _log(f"Token loaded: {bool(self._mcp_auth_token)}, auto-generated: {self._token_was_auto_generated}")

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
        mcp_auth_enabled = os.environ.get("MCP_AUTH_ENABLED", "false").lower() == "true"
        _log(f"MCP_AUTH_ENABLED env var: '{os.environ.get('MCP_AUTH_ENABLED', '')}' -> {mcp_auth_enabled}")
        
        return cls(
            homebox_url=os.environ.get("HOMEBOX_URL", "http://localhost:7745"),
            homebox_token=os.environ.get("HOMEBOX_TOKEN", ""),
            mcp_auth_enabled=mcp_auth_enabled,
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
_log("Loading configuration from environment...")
config = Config.from_environment()
_log(f"Configuration loaded. MCP Auth: enabled={config.mcp_auth_enabled}, has_token={bool(config.mcp_auth_token)}")
