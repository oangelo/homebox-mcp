"""Configuration management for Homebox MCP Server."""

import os
import secrets
import sys
from dataclasses import dataclass, field


def _log(message: str) -> None:
    """Simple logging before logging module is configured."""
    print(f"[CONFIG] {message}", file=sys.stderr, flush=True)


def _generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def _print_token_banner(token: str, source: str) -> None:
    """Print the token prominently in logs."""
    print("", file=sys.stderr, flush=True)
    print("=" * 70, file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)
    print("  🔑 MCP AUTHENTICATION TOKEN", file=sys.stderr, flush=True)
    print(f"     ({source})", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)
    print(f"  {token}", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)
    print("  📋 Copy this token to Claude.ai:", file=sys.stderr, flush=True)
    print("     Field: 'Segredo do Cliente OAuth'", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)
    print("=" * 70, file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)


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

    def __post_init__(self):
        """Initialize the MCP auth token after dataclass init."""
        if not self.mcp_auth_enabled:
            _log("MCP authentication: DISABLED")
            self._mcp_auth_token = ""
            return
        
        _log("MCP authentication: ENABLED")
        
        # Use configured token or generate one
        if self._mcp_auth_token_configured:
            self._mcp_auth_token = self._mcp_auth_token_configured
            _print_token_banner(self._mcp_auth_token, "configured in addon options")
        else:
            self._mcp_auth_token = _generate_token()
            _print_token_banner(self._mcp_auth_token, "auto-generated")

    @property
    def mcp_auth_token(self) -> str:
        """Get the MCP authentication token."""
        return self._mcp_auth_token

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
