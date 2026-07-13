import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


def _load_tool_module(module_name: str, filename: str):
    spec = spec_from_file_location(module_name, TOOLS_DIR / filename)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _restore_tool_and_agent_modules():
    _prefixes = ("tools", "agent", "plugins")
    _extra = {"fal_client", "openai"}
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name in _extra
        or name == "tools" or name.startswith("tools.")
        or name == "agent" or name.startswith("agent.")
        or name == "plugins" or name.startswith("plugins.")
    }
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name in _extra \
               or name == "tools" or name.startswith("tools.") \
               or name == "agent" or name.startswith("agent.") \
               or name == "plugins" or name.startswith("plugins."):
                if name not in original_modules:
                    sys.modules.pop(name, None)
        sys.modules.update(original_modules)


def _install_fake_tools_package():
    tools_package = types.ModuleType("tools")
    tools_package.__path__ = [str(TOOLS_DIR)]  # type: ignore[attr-defined]
    sys.modules["tools"] = tools_package
    sys.modules["tools.debug_helpers"] = types.SimpleNamespace(
        DebugSession=lambda *args, **kwargs: types.SimpleNamespace(
            active=False,
            session_id="debug-session",
            log_call=lambda *a, **k: None,
            save=lambda: None,
            get_session_info=lambda: {},
        )
    )
    sys.modules["tools.managed_tool_gateway"] = _load_tool_module(
        "tools.managed_tool_gateway",
        "managed_tool_gateway.py",
    )


def _load_video_gen_plugin():
    """Load the FAL video gen plugin in isolation."""
    _install_fake_tools_package()

    agent_dir = Path(__file__).resolve().parents[2] / "agent"
    spec = spec_from_file_location(
        "agent.video_gen_provider",
        agent_dir / "video_gen_provider.py",
    )
    assert spec and spec.loader
    mod = module_from_spec(spec)
    sys.modules["agent.video_gen_provider"] = mod
    spec.loader.exec_module(mod)

    plugin_init = PLUGINS_DIR / "video_gen" / "fal" / "__init__.py"
    spec = spec_from_file_location("plugins.video_gen.fal", plugin_init)
    assert spec and spec.loader
    plugin_mod = module_from_spec(spec)
    sys.modules["plugins.video_gen.fal"] = plugin_mod
    spec.loader.exec_module(plugin_mod)
    return plugin_mod


def test_video_gen_happy_horse_uses_alibaba_namespace():
    """Verify the happy-horse family uses alibaba/ not fal-ai/ endpoints."""
    plugin_mod = _load_video_gen_plugin()

    hh = plugin_mod.FAL_FAMILIES["happy-horse"]
    assert hh["text_endpoint"] == "alibaba/happy-horse/text-to-video"
    assert hh["image_endpoint"] == "alibaba/happy-horse/image-to-video"
