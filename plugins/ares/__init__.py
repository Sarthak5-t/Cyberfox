from __future__ import annotations

import logging as _logging

logger = _logging.getLogger(__name__)

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
    from plugins.ares.tools.recon import nmap_tool
    from plugins.ares.tools.recon import dnsrecon_tool
    from plugins.ares.tools.recon import subfinder_tool
    from plugins.ares.tools.recon import masscan_tool
    from plugins.ares.tools.recon import amass_tool
    from plugins.ares.tools.recon import whois_tool
    from plugins.ares.tools.recon import theharvester_tool
    from plugins.ares.tools.recon import whatweb_tool
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
    from plugins.ares.tools.ad import bloodhound_tool
    from plugins.ares.tools.ad import certipy_tool
    from plugins.ares.tools.ad import crackmapexec_tool
    from plugins.ares.tools.ad import kerbrute_tool
    from plugins.ares.tools.utility import report_tool
    from plugins.ares.tools import findings_tool
    from plugins.ares.tools import journal_tool
    from plugins.ares.tools.browsing import browse_autonomously
    from plugins.ares.agents import orchestrator
    from plugins.ares.tools.orchestration import engage_tool
    from plugins.ares.tools.orchestration import plan_tool
    from plugins.ares.tools.orchestration import entity_tool
    from plugins.ares.tools.orchestration import decide_tool

    _TOOL_MODULES = [
        nmap_tool, dnsrecon_tool, subfinder_tool, masscan_tool, amass_tool,
        whois_tool, theharvester_tool, whatweb_tool,
        nuclei_tool, gobuster_tool, ffuf_tool, nikto_tool, enum4linux_tool,
        wafw00f_tool, wpscan_tool, wfuzz_tool, feroxbuster_tool, smbclient_tool,
        snmpwalk_tool, curl_tool, burp_scan, burp_spider, burp_repeater,
        nuclei_templates, subjack,
        searchsploit_tool, sqlmap_tool, hydra_tool, metasploit_tool,
        responder_tool, impacket_tool, msf_console, msf_search, msf_payload,
        msf_post, exploit_chain, payload_gen, exploit_dev,
        bloodhound_tool, certipy_tool, crackmapexec_tool, kerbrute_tool,
        report_tool, findings_tool, journal_tool, browse_autonomously, orchestrator,
        engage_tool, plan_tool, entity_tool, decide_tool,
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

    try:
        from plugins.ares.hooks.reflection import post_tool_call as reflection_hook
        ctx.register_hook("post_tool_call", reflection_hook)
    except Exception as e:
        logger.debug("reflection hook not registered: %s", e)

    try:
        from plugins.ares.hooks.context_injection import pre_llm_call as ctx_inject
        ctx.register_hook("pre_llm_call", ctx_inject)
    except Exception as e:
        logger.debug("context_injection hook not registered: %s", e)
