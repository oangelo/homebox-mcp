"""Configuration management for Homebox MCP Server."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for the Homebox MCP Server."""

    homebox_url: str
    homebox_username: str
    homebox_password: str
    log_level: str = "info"
    server_host: str = "0.0.0.0"
    server_port: int = 8099

    @classmethod
    def from_environment(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            homebox_url=os.environ.get("HOMEBOX_URL", "http://localhost:7745"),
            homebox_username=os.environ.get("HOMEBOX_USERNAME", ""),
            homebox_password=os.environ.get("HOMEBOX_PASSWORD", ""),
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
