from __future__ import annotations

import logging as _logging
import sys as _sys

logger = _logging.getLogger(__name__)  # noqa: F821 — used in register() below as `logger`

# ── Auth-stripping transport for big-pickle (opencode.ai) ──────────────────
# The opencode.ai public endpoint accepts requests with NO Authorization
# header. Cyberfox sets api_key="no-key-required" for custom endpoints without
# a configured key, which becomes `Authorization: Bearer no-key-required` →
# HTTP 401. We replace `openai.OpenAI` at the module level with a subclass
# that wraps the httpx transport to strip the auth header for opencode.ai
# base URLs. Any `from openai import OpenAI` after this patch gets the
# subclass automatically (verified: function-level imports re-resolve from
# the live module attribute).
_STRIPPED = False


def _ensure_auth_stripped() -> None:
    global _STRIPPED
    import sys as _sys2
    old_stdout = _sys2.stdout
    try:
        with open("/tmp/ares_debug2.log", "a") as _f:
            _f.write(f"_ensure_auth_stripped called. _STRIPPED={_STRIPPED}, stdout={old_stdout}\n")
            _f.write(f"  CYBERFOX_HOME={__import__('os').environ.get('CYBERFOX_HOME', 'NOT SET')}\n")
            _f.write(f"  CYBERFOX_HOME={__import__('os').environ.get('CYBERFOX_HOME', 'NOT SET')}\n")
    except Exception:
        pass
    if _STRIPPED:
        return
    try:
        import httpx as _httpx
        import openai as _openai

        class _NoAuthTransport(_httpx.BaseTransport):
            def __init__(self, verify: bool = True) -> None:
                self._transport = _httpx.HTTPTransport(verify=verify)

            def handle_request(self, request: _httpx.Request) -> _httpx.Response:
                request.headers.pop("authorization", None)
                return self._transport.handle_request(request)

        _OriginalOpenAI = _openai.OpenAI

        class _NoAuthOpenAI(_OriginalOpenAI):  # type: ignore[valid-type]
            def __init__(self, **kw: object) -> None:
                _api_key = str(kw.get("api_key", "") or "")
                _base_url = str(kw.get("base_url", "") or "")
                super().__init__(**kw)
                if _api_key != "no-key-required" or "opencode.ai" not in _base_url.lower():
                    return
                _c = getattr(self, "_client", None)
                if _c is None:
                    return
                _verify = getattr(
                    getattr(_c, "_transport", None), "_verify", True
                )
                _nat = _NoAuthTransport(verify=_verify)
                # httpx.Client may use _transport (no mounts) or mounts dict
                # with URLPattern keys — replace whichever is active.
                _c._transport = _nat
                if hasattr(_c, "_mounts"):
                    try:
                        from httpx._utils import URLPattern as _URLPattern
                    except ImportError:
                        _URLPattern = None  # type: ignore[assignment]
                    for _mk, _mt in list(_c._mounts.items()):
                        _mpat = getattr(_mk, "pattern", str(_mk))
                        if _mpat.startswith("https://"):
                            _c._mounts[_mk] = _NoAuthTransport(
                                verify=getattr(_mt, "_verify", _verify)
                            )

        _openai.OpenAI = _NoAuthOpenAI  # type: ignore[assignment]

        # Clear cached class refs on already-loaded proxy modules so the next
        # `from openai import OpenAI` inside _load_openai_cls picks up our
        # subclass. Modules not yet loaded get it automatically.
        for _mod_name in ("agent.process_bootstrap", "agent.auxiliary_client"):
            _mod = _sys.modules.get(_mod_name)
            if _mod is not None:
                _mod._OPENAI_CLS_CACHE = None  # type: ignore[attr-defined]

        _STRIPPED = True
        logger.debug("Auth-stripping transport installed for opencode.ai")
    except Exception as _exc:
        logger.debug("Auth-stripping transport not installed: %s", _exc)


_ensure_auth_stripped()


# ── Config ────────────────────────────────────────────────────────────────
from plugins.ares.config import get_config, reload_config


def register(ctx) -> None:
    cfg = get_config()
    if not cfg.ares_enabled:
        logger.info("Ares plugin is disabled via config")
        return

    logger.info("Registering Ares cybersecurity plugin")

    _register_tools(ctx)
    _register_hooks(ctx)


def _register_tools(ctx) -> None:
    from plugins.ares.safety.scope_validator import pre_tool_call as _scope_check
    from plugins.ares.safety.doom_loop import pre_tool_call as _doom_check
    from plugins.ares.safety.approval_hardening import pre_tool_call as _approval_check
    # Recon tools
    from plugins.ares.tools.recon import nmap_tool
    from plugins.ares.tools.recon import dnsrecon_tool
    from plugins.ares.tools.recon import subfinder_tool
    from plugins.ares.tools.recon import masscan_tool
    from plugins.ares.tools.recon import amass_tool
    from plugins.ares.tools.recon import whois_tool
    from plugins.ares.tools.recon import theharvester_tool
    from plugins.ares.tools.recon import whatweb_tool
    # Scanning tools
    from plugins.ares.tools.scanning import nuclei_tool
    from plugins.ares.tools.scanning import gobuster_tool
    from plugins.ares.tools.scanning import ffuf_tool
    from plugins.ares.tools.scanning import nikto_tool
    from plugins.ares.tools.scanning import enum4linux_tool
    from plugins.ares.tools.scanning import wafw00f_tool
    from plugins.ares.tools.scanning import wpscan_tool
    from plugins.ares.tools.scanning import wfuzz_tool
    from plugins.ares.tools.scanning import feroxbuster_tool
    from plugins.ares.tools.scanning import smbclient_tool
    from plugins.ares.tools.scanning import snmpwalk_tool
    from plugins.ares.tools.scanning import curl_tool
    from plugins.ares.tools.scanning.burp import burp_scan
    from plugins.ares.tools.scanning.burp import burp_spider
    from plugins.ares.tools.scanning.burp import burp_repeater
    from plugins.ares.tools.scanning import nuclei_templates
    from plugins.ares.tools.scanning import subjack
    # Exploitation tools
    from plugins.ares.tools.exploitation import searchsploit_tool
    from plugins.ares.tools.exploitation import sqlmap_tool
    from plugins.ares.tools.exploitation import hydra_tool
    from plugins.ares.tools.exploitation import metasploit_tool
    from plugins.ares.tools.exploitation import responder_tool
    from plugins.ares.tools.exploitation import impacket_tool
    from plugins.ares.tools.exploitation.metasploit import msf_console
    from plugins.ares.tools.exploitation.metasploit import msf_search
    from plugins.ares.tools.exploitation.metasploit import msf_payload
    from plugins.ares.tools.exploitation.metasploit import msf_post
    from plugins.ares.tools.exploitation.custom import exploit_chain
    from plugins.ares.tools.exploitation.custom import payload_gen
    from plugins.ares.tools.exploitation.custom import exploit_dev
    # AD tools
    from plugins.ares.tools.ad import bloodhound_tool
    from plugins.ares.tools.ad import certipy_tool
    from plugins.ares.tools.ad import crackmapexec_tool
    from plugins.ares.tools.ad import kerbrute_tool
    # Utility tools
    from plugins.ares.tools.utility import report_tool
    from plugins.ares.tools import findings_tool
    from plugins.ares.agents import orchestrator

    _TOOL_MODULES = [
        # Recon
        nmap_tool,
        dnsrecon_tool,
        subfinder_tool,
        masscan_tool,
        amass_tool,
        whois_tool,
        theharvester_tool,
        whatweb_tool,
        # Scanning
        nuclei_tool,
        gobuster_tool,
        ffuf_tool,
        nikto_tool,
        enum4linux_tool,
        wafw00f_tool,
        wpscan_tool,
        wfuzz_tool,
        feroxbuster_tool,
        smbclient_tool,
        snmpwalk_tool,
        curl_tool,
        burp_scan,
        burp_spider,
        burp_repeater,
        nuclei_templates,
        subjack,
        # Exploitation
        searchsploit_tool,
        sqlmap_tool,
        hydra_tool,
        metasploit_tool,
        responder_tool,
        impacket_tool,
        msf_console,
        msf_search,
        msf_payload,
        msf_post,
        exploit_chain,
        payload_gen,
        exploit_dev,
        # AD
        bloodhound_tool,
        certipy_tool,
        crackmapexec_tool,
        kerbrute_tool,
        # Utility
        report_tool,
        findings_tool,
        orchestrator,
    ]

    for mod in _TOOL_MODULES:
        if hasattr(mod, "TOOLSET") and hasattr(mod, "register_tools"):
            try:
                mod.register_tools(ctx)
            except Exception as e:
                logger.error("Failed to register tools from %s: %s", mod.__name__, e)


def _register_hooks(ctx) -> None:
    try:
        from plugins.ares.safety.scope_validator import pre_tool_call as scope_check
        ctx.register_hook("pre_tool_call", scope_check)
    except Exception as e:
        logger.debug("scope_validator hook not registered: %s", e)

    try:
        from plugins.ares.safety.doom_loop import pre_tool_call as doom_check
        ctx.register_hook("pre_tool_call", doom_check)
    except Exception as e:
        logger.debug("doom_loop hook not registered: %s", e)

    try:
        from plugins.ares.safety.approval_hardening import pre_tool_call as approval_check
        ctx.register_hook("pre_tool_call", approval_check)
    except Exception as e:
        logger.debug("approval_hardening hook not registered: %s", e)

    try:
        from plugins.ares.safety.audit_trail import post_tool_call as audit_log
        ctx.register_hook("post_tool_call", audit_log)
    except Exception as e:
        logger.debug("audit_trail hook not registered: %s", e)

    try:
        from plugins.ares.safety.audit_trail import on_session_end as audit_finalize
        ctx.register_hook("on_session_end", audit_finalize)
    except Exception as e:
        logger.debug("audit_trail session hook not registered: %s", e)

