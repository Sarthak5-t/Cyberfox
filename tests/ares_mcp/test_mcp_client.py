"""Tests for the Ares MCP client module (plugins/ares/tools/mcp/).

Starts a local FastMCP test server via stdio transport and verifies the
connect → discover → call → disconnect lifecycle.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import pytest

# Path to the test server script
TEST_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "_test_mcp_server.py")


@pytest.fixture(scope="module")
def _ensure_test_server_script():
    """Write the test MCP server if not present."""
    server_code = r'''#!/usr/bin/env python3
"""Minimal FastMCP test server — exposes echo and math tools on stdio."""
import sys
sys.path.insert(0, ".")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Ares-Test-Server", instructions="Test server for Ares MCP client")

@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message."""
    return f"Echo: {message}"

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@mcp.tool()
def status() -> str:
    """Return server status."""
    return "ok"

mcp.run(transport="stdio")
'''
    with open(TEST_SERVER_SCRIPT, "w") as f:
        f.write(server_code)
    os.chmod(TEST_SERVER_SCRIPT, 0o755)
    yield
    if os.path.exists(TEST_SERVER_SCRIPT):
        os.unlink(TEST_SERVER_SCRIPT)


def test_mcp_module_imports():
    """Verify the core module imports and MCP SDK detection."""
    from plugins.ares.tools.mcp import (
        _MCP_AVAILABLE, connect, call_tool, disconnect, list_connections,
        _check_mcp, _ensure_loop,
    )
    assert _MCP_AVAILABLE is True, "MCP SDK should be available"
    _check_mcp()  # should not raise
    loop = _ensure_loop()
    assert loop is not None
    assert loop.is_running()


def test_schema_validation():
    """Verify all three tool modules have valid SCHEMAs."""
    from plugins.ares.tools.mcp import mcp_connect_tool as ct
    from plugins.ares.tools.mcp import mcp_call_tool as cl
    from plugins.ares.tools.mcp import mcp_disconnect_tool as dt

    for module, expected_name in [
        (ct, "mcp_server_connect"),
        (cl, "mcp_server_call"),
        (dt, "mcp_server_disconnect"),
    ]:
        assert hasattr(module, "SCHEMA")
        assert hasattr(module, "TOOLSET")
        assert hasattr(module, "register_tools")
        assert hasattr(module, "_handle")
        assert module.SCHEMA["name"] == expected_name
        assert module.TOOLSET == "ares_utility"
        assert "description" in module.SCHEMA
        assert "parameters" in module.SCHEMA


def test_connect_disconnect_stdio(_ensure_test_server_script):
    """Connect to the test server via stdio, verify tools, then disconnect."""
    from plugins.ares.tools.mcp import connect, disconnect, list_connections

    result = connect(
        name="ares-test",
        transport="stdio",
        command=sys.executable,
        args=[TEST_SERVER_SCRIPT],
        timeout=15,
    )

    assert result["server"] == "ares-test"
    assert result["transport"] == "stdio"
    assert result["tool_count"] >= 3
    tool_names = [t["name"] for t in result["tools"]]
    assert "echo" in tool_names
    assert "add" in tool_names
    assert "status" in tool_names

    # Verify it shows in list_connections
    conns = list_connections()
    assert any(c["server"] == "ares-test" for c in conns)

    # Disconnect
    result = disconnect("ares-test")
    assert result["server"] == "ares-test"
    assert result["disconnected"] is True

    # Verify it's gone
    conns = list_connections()
    assert not any(c["server"] == "ares-test" for c in conns)


def test_call_tools(_ensure_test_server_script):
    """Connect and call each tool on the test server."""
    from plugins.ares.tools.mcp import connect, call_tool, disconnect

    connect(
        name="ares-test-call",
        transport="stdio",
        command=sys.executable,
        args=[TEST_SERVER_SCRIPT],
        timeout=15,
    )

    try:
        # Test echo
        result = call_tool("ares-test-call", "echo", {"message": "hello world"})
        assert result["server"] == "ares-test-call"
        assert result["tool"] == "echo"
        assert result["isError"] is False
        assert "Echo: hello world" in result["content"]
        assert result["content_blocks"] >= 1

        # Test add
        result = call_tool("ares-test-call", "add", {"a": 3, "b": 4})
        assert result["isError"] is False
        assert "7" in result["content"] or "7.0" in result["content"]

        # Test status
        result = call_tool("ares-test-call", "status", {})
        assert result["isError"] is False
        assert "ok" in result["content"]

    finally:
        disconnect("ares-test-call")


def test_reconnect_after_disconnect(_ensure_test_server_script):
    """Connect, disconnect, reconnect — should work."""
    from plugins.ares.tools.mcp import connect, call_tool, disconnect

    # First connection
    connect(
        name="ares-test-re", transport="stdio",
        command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
    )
    result = call_tool("ares-test-re", "status", {})
    assert "ok" in result["content"]
    disconnect("ares-test-re")

    # Reconnect
    connect(
        name="ares-test-re", transport="stdio",
        command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
    )
    result = call_tool("ares-test-re", "status", {})
    assert "ok" in result["content"]
    disconnect("ares-test-re")


def test_tool_handlers_output_json(_ensure_test_server_script):
    """Verify the _handle functions return valid JSON strings."""
    from plugins.ares.tools.mcp.mcp_connect_tool import _handle as connect_handle
    from plugins.ares.tools.mcp.mcp_disconnect_tool import _handle as disconnect_handle

    # Connect via the handler
    result_str = connect_handle({
        "name": "ares-test-h",
        "command": sys.executable,
        "args": TEST_SERVER_SCRIPT,
        "transport": "stdio",
        "timeout": 15,
    })
    result = json.loads(result_str)
    assert result["success"] is True, f"Connect failed: {result}"
    data = result["data"]
    assert data["server"] == "ares-test-h"
    assert data["tool_count"] >= 3

    # Disconnect via the handler
    result_str = disconnect_handle({"server": "ares-test-h"})
    result = json.loads(result_str)
    assert result["success"] is True
    assert result["data"]["disconnected"] is True


def test_disconnect_all(_ensure_test_server_script):
    """Disconnect all via the 'all' flag."""
    from plugins.ares.tools.mcp import connect, list_connections
    from plugins.ares.tools.mcp.mcp_disconnect_tool import _handle

    connect(
        name="ares-test-1", transport="stdio",
        command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
    )
    connect(
        name="ares-test-2", transport="stdio",
        command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
    )

    assert len(list_connections()) >= 2

    result_str = _handle({"all": True})
    result = json.loads(result_str)
    assert result["success"] is True
    assert len(result["data"]["disconnected"]) >= 2

    assert len(list_connections()) == 0


def test_connect_twice_fails(_ensure_test_server_script):
    """Connecting the same name twice should fail."""
    from plugins.ares.tools.mcp import connect, disconnect

    connect(
        name="ares-test-dupe", transport="stdio",
        command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
    )
    try:
        with pytest.raises(RuntimeError, match="already connected"):
            connect(
                name="ares-test-dupe", transport="stdio",
                command=sys.executable, args=[TEST_SERVER_SCRIPT], timeout=15,
            )
    finally:
        disconnect("ares-test-dupe")


def test_call_before_connect_fails():
    """Calling a tool without connecting should fail."""
    from plugins.ares.tools.mcp import call_tool

    with pytest.raises(RuntimeError, match="not connected"):
        call_tool("nonexistent-server", "echo", {"message": "hi"})


def test_disconnect_nonexistent_fails():
    """Disconnecting a non-existent server should fail."""
    from plugins.ares.tools.mcp import disconnect

    with pytest.raises(RuntimeError, match="not connected"):
        disconnect("nonexistent-server")
