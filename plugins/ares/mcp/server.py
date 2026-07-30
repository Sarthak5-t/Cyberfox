from __future__ import annotations

import json
import logging
import importlib
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("Ares Security Tools", instructions="Exposes all registered Ares penetration testing tools as MCP tools.")


def _discover_tool_modules():
    _TOOLS_REGISTRY.clear()
    base_dirs = [
        Path(__file__).resolve().parent.parent / "tools",
        Path(__file__).resolve().parent.parent / "agents",
    ]
    modules = []

    for base in base_dirs:
        if not base.exists():
            continue
        project_root = base.parent.parent.parent
        for pyfile in sorted(base.rglob("*.py")):
            if pyfile.name == "__init__.py":
                continue
            if "__pycache__" in pyfile.parts:
                continue

            rel = pyfile.relative_to(project_root)
            mod_name = ".".join(rel.with_suffix("").parts)

            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue

            if hasattr(mod, "SCHEMA") and hasattr(mod, "_handle") and hasattr(mod, "register_tools"):
                name = mod.SCHEMA["name"]
                if not any(existing[0] == name for existing in _TOOLS_REGISTRY):
                    modules.append(mod)
                    _TOOLS_REGISTRY.append((name, mod._handle, mod.SCHEMA))

    return modules


_TOOLS_REGISTRY: list[tuple[str, object, dict]] = []


def _register_all_tools():
    _discover_tool_modules()

    for name, handler, schema in _TOOLS_REGISTRY:
        desc = schema.get("description", "")

        def make_tool_fn(h=handler):
            def tool_fn(**kwargs) -> str:
                result = h(kwargs)
                if isinstance(result, str):
                    return result
                return json.dumps(result)
            return tool_fn

        fn = make_tool_fn()
        fn.__name__ = name.replace("-", "_")
        fn.__doc__ = desc

        try:
            mcp.add_tool(fn, name=name, description=desc)
        except Exception:
            pass


def main():
    logging.basicConfig(level=logging.INFO)
    _register_all_tools()
    logger.info("Ares MCP server started with %d tools", len(_TOOLS_REGISTRY))
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
