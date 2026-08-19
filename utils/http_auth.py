"""Bearer authentication for the MCP HTTP transport."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import secrets

from fastmcp.server.auth import AccessToken, TokenVerifier


class HTTPAuthConfigurationError(RuntimeError):
    """Raised when HTTP authentication is not safely configured."""


@dataclass(frozen=True)
class APIKeyAuthConfig:
    """API keys accepted by the MCP HTTP transport."""

    current_key: str
    previous_key: str | None = None

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> APIKeyAuthConfig:
        """Load API-key configuration, failing closed without a current key."""
        environment = os.environ if environ is None else environ
        current_key = environment.get("MCP_API_KEY_CURRENT", "")
        if not current_key.strip():
            raise HTTPAuthConfigurationError(
                "MCP_API_KEY_CURRENT is required for HTTP transport and must not be empty"
            )

        previous_key = environment.get("MCP_API_KEY_PREVIOUS")
        if previous_key is not None and not previous_key.strip():
            previous_key = None

        return cls(current_key=current_key, previous_key=previous_key)


class APIKeyTokenVerifier(TokenVerifier):
    """Validate current and rotation-window API keys in constant time."""

    def __init__(self, config: APIKeyAuthConfig):
        super().__init__()
        self._current_key = config.current_key.encode("utf-8")
        self._previous_key = (
            config.previous_key.encode("utf-8")
            if config.previous_key is not None
            else None
        )

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> APIKeyTokenVerifier:
        """Create a verifier from the MCP API-key environment variables."""
        return cls(APIKeyAuthConfig.from_environment(environ))

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return access metadata when the token matches an accepted key."""
        presented_key = token.encode("utf-8")
        matches_current = secrets.compare_digest(presented_key, self._current_key)
        matches_previous = (
            secrets.compare_digest(presented_key, self._previous_key)
            if self._previous_key is not None
            else False
        )

        if not (matches_current or matches_previous):
            return None

        return AccessToken(
            token=token,
            client_id="mcp-api-key",
            scopes=[],
        )


__all__ = [
    "APIKeyAuthConfig",
    "APIKeyTokenVerifier",
    "HTTPAuthConfigurationError",
]
