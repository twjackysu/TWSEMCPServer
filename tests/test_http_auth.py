"""Focused tests for MCP HTTP bearer authentication."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock

from fastmcp import FastMCP
import pytest
from starlette.testclient import TestClient

import server
from utils.http_auth import (
    APIKeyAuthConfig,
    APIKeyTokenVerifier,
    HTTPAuthConfigurationError,
)


CURRENT_KEY = "current-test-secret"
PREVIOUS_KEY = "previous-test-secret"
WRONG_KEY = "presented-wrong-secret"


def _create_client(previous_key: str | None = PREVIOUS_KEY) -> TestClient:
    verifier = APIKeyTokenVerifier(
        APIKeyAuthConfig(current_key=CURRENT_KEY, previous_key=previous_key)
    )
    mcp = FastMCP("HTTP auth test", auth=verifier)
    return TestClient(mcp.http_app())


def _initialize(client: TestClient, authorization: str | None):
    headers = {"accept": "application/json, text/event-stream"}
    if authorization is not None:
        headers["authorization"] = authorization

    return client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "auth-test", "version": "1"},
            },
        },
    )


@pytest.mark.parametrize("key", [CURRENT_KEY, PREVIOUS_KEY])
def test_current_and_previous_keys_are_accepted(key: str):
    with _create_client() as client:
        response = _initialize(client, f"Bearer {key}")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic credentials", "Bearer", "Bearer current-test-secret extra"],
)
def test_missing_and_malformed_credentials_share_generic_401(authorization: str | None):
    with _create_client() as client:
        response = _initialize(client, authorization)

    assert response.status_code == 401
    assert response.json() == {
        "error": "invalid_token",
        "error_description": "Authentication required",
    }
    assert response.headers["www-authenticate"].startswith("Bearer ")


def test_wrong_key_receives_same_generic_401():
    with _create_client() as client:
        missing_response = _initialize(client, None)
        wrong_response = _initialize(client, f"Bearer {WRONG_KEY}")

    assert wrong_response.status_code == 401
    assert wrong_response.content == missing_response.content
    assert (
        wrong_response.headers["www-authenticate"]
        == missing_response.headers["www-authenticate"]
    )


@pytest.mark.parametrize("method", ["get", "delete"])
def test_streaming_and_session_methods_also_require_auth(method: str):
    with _create_client() as client:
        response = getattr(client, method)("/mcp")

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


@pytest.mark.parametrize("current_key", [None, "", "   "])
def test_http_startup_fails_closed_without_current_key(monkeypatch, current_key):
    environment = {"MCP_API_KEY_PREVIOUS": PREVIOUS_KEY}
    if current_key is not None:
        environment["MCP_API_KEY_CURRENT"] = current_key
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)

    with pytest.raises(
        HTTPAuthConfigurationError, match="MCP_API_KEY_CURRENT is required"
    ) as exc_info:
        server.run_server(environment)

    run.assert_not_called()
    assert PREVIOUS_KEY not in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_startup_configures_auth_before_run(monkeypatch):
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)
    monkeypatch.setattr(server.mcp, "auth", None)
    monkeypatch.setattr(server.mcp, "_http_api_key_auth_configured", False)

    server.run_server(
        {
            "MCP_API_KEY_CURRENT": CURRENT_KEY,
            "MCP_API_KEY_PREVIOUS": PREVIOUS_KEY,
            "PORT": "8123",
        }
    )

    run.assert_called_once_with(transport="http", host="0.0.0.0", port=8123)
    assert isinstance(server.mcp.auth, APIKeyTokenVerifier)
    assert await server.mcp.auth.verify_token(CURRENT_KEY) is not None
    assert await server.mcp.auth.verify_token(PREVIOUS_KEY) is not None


@pytest.mark.asyncio
async def test_fastmcp_cli_http_startup_cannot_bypass_auth(monkeypatch):
    delegated_run = AsyncMock()
    monkeypatch.setattr(FastMCP, "run_async", delegated_run)
    monkeypatch.setattr(server.mcp, "auth", None)
    monkeypatch.setattr(server.mcp, "_http_api_key_auth_configured", False)
    monkeypatch.setenv("MCP_API_KEY_CURRENT", CURRENT_KEY)
    monkeypatch.delenv("MCP_API_KEY_PREVIOUS", raising=False)

    await server.mcp.run_async(transport="http", show_banner=False)

    assert isinstance(server.mcp.auth, APIKeyTokenVerifier)
    assert await server.mcp.auth.verify_token(CURRENT_KEY) is not None
    delegated_run.assert_awaited_once_with(
        transport="http",
        show_banner=False,
    )


@pytest.mark.asyncio
async def test_fastmcp_cli_http_startup_fails_without_current_key(monkeypatch):
    delegated_run = AsyncMock()
    monkeypatch.setattr(FastMCP, "run_async", delegated_run)
    monkeypatch.setattr(server.mcp, "auth", None)
    monkeypatch.setattr(server.mcp, "_http_api_key_auth_configured", False)
    monkeypatch.delenv("MCP_API_KEY_CURRENT", raising=False)
    monkeypatch.delenv("MCP_API_KEY_PREVIOUS", raising=False)

    with pytest.raises(HTTPAuthConfigurationError):
        await server.mcp.run_async(transport="http")

    delegated_run.assert_not_awaited()


@pytest.mark.parametrize("previous_key", [None, "", "   "])
def test_absent_or_empty_previous_key_is_ignored(previous_key):
    environment = {"MCP_API_KEY_CURRENT": CURRENT_KEY}
    if previous_key is not None:
        environment["MCP_API_KEY_PREVIOUS"] = previous_key

    config = APIKeyAuthConfig.from_environment(environment)

    assert config.previous_key is None


def test_stdio_does_not_require_or_configure_api_keys(monkeypatch):
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)

    server.run_server({"MCP_STDIO": "true"})

    run.assert_called_once_with(transport="stdio")


def test_secrets_do_not_leak_in_auth_response_or_logs(caplog):
    caplog.set_level(logging.DEBUG)

    with _create_client() as client:
        response = _initialize(client, f"Bearer {WRONG_KEY}")

    exposed_text = response.text + "\n" + caplog.text
    assert CURRENT_KEY not in exposed_text
    assert PREVIOUS_KEY not in exposed_text
    assert WRONG_KEY not in exposed_text
