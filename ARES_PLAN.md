# Ares — Cybersecurity AI Agent on Cyberfox

A modular plugin-based personal AI agent for **VAPT, SOC, and red teaming** built on top of [Cyberfox Agent](https://github.com/Sarthak5-t/Cyberfox) using the **big-pickle** LLM.

## Architecture

```
Cyberfox Core (untouched)
    ↕ plugin hooks
Ares Plugin (plugins/ares/)
    ├── Safety Layer (scope, approval, audit, doom loop)
    ├── Tool Layer (18+ security tools)
    ├── Agent Definitions (named subagents)
    └── Context Management (truncation, phase injection)
    ↕ delegate_task
Subagents (isolated per-phase)
    ├── recon    → nmap, dns, subfinder
    ├── scanner  → nuclei, gobuster, ffuf, nikto
    ├── exploit  → searchsploit, sqlmap, hydra, msf
    ├── ad       → bloodhound, certipy, crackmapexec
    └── reporter → report generation
```

## Model

**Provider:** big-pickle via OpenCode Zen API
**Endpoint:** `https://opencode.ai/zen/v1/chat/completions`
**Config:**
```yaml
model:
  provider: custom
  base_url: https://opencode.ai/zen/v1
  default: big-pickle
```
**Capabilities:** tool calling ✅, reasoning ✅, structured output ✅, 200K context
**Cost:** $0 (free public tier)

## Modules

| # | Module | Files | Depends On | Status |
|---|--------|-------|------------|--------|
| 1 | **Plugin Core** | `plugin.yaml`, `__init__.py`, `config.py`, `tools/base.py` | None | ✅ |
| 2 | **Safety** | `safety/scope_validator.py`, `doom_loop.py`, `audit_trail.py`, `approval_hardening.py` | M1 | ✅ |
| 3 | **Recon Tools** | `tools/recon/nmap_tool.py`, `dnsrecon_tool.py`, `subfinder_tool.py` | M1, M2 | ✅ |
| 4 | **Scanning Tools** | `tools/scanning/nuclei_tool.py`, `gobuster_tool.py`, `ffuf_tool.py`, `nikto_tool.py`, `enum4linux_tool.py` | M1, M2 | ✅ |
| 5 | **Exploitation Tools** | `tools/exploitation/searchsploit_tool.py`, `sqlmap_tool.py`, `hydra_tool.py`, `metasploit_tool.py`, `responder_tool.py`, `impacket_tool.py` | M1, M2 | ✅ |
| 6 | **AD Tools** | `tools/ad/bloodhound_tool.py`, `certipy_tool.py`, `crackmapexec_tool.py`, `kerbrute_tool.py` | M1, M2 | ✅ |
| 7 | **Report Tool** | `tools/utility/report_tool.py` | M1 | ✅ |
| 8 | **Agent Definitions** | `agents/__init__.py`, `agents/orchestrator.py` | M3-M7 | ✅ |
| 9 | **Skills** | `skills/ares/ares_lead.md` (lead skill) + user skill dirs | M3-M7 | ✅ |
| 10 | **Configuration** | `~/.cyberfox/profiles/ares/config.yaml`, `~/.cyberfox/profiles/ares/scope.yaml` | M1 | ✅ |

## Model Verification

| Date | Test | Result |
|------|------|--------|
| 2026-07-08 | Chat completion (text output) | ✅ `content` field populated |
| 2026-07-08 | Reasoning | ✅ `reasoning_content` returned |
| 2026-07-08 | Tool calling | ✅ `tool_calls` with valid JSON |
| 2026-07-08 | Cost | ✅ `$0` per call |
| 2026-07-08 | Auth | ✅ Public endpoint, no key needed |

## Progress

- [x] Model API verified (big-pickle working)
- [x] Sprint 1: M1 + M10 + M2 — Core scaffold + config + safety
- [x] Sprint 2: M3 + M4 — Recon + scanning tools (8 tools)
- [x] Sprint 3: M5 + M6 + M7 — Exploitation + AD + report (9 tools)
- [x] Sprint 4: M8 — Agent definitions + subagent orchestrator
- [x] Sprint 5: M9 — Ares lead skill
- [ ] Sprint 6: E2E verification — `cyberfox -p ares` test run

## Subagent Roles

| Agent | Toolsets | Approval Required | Can Delegate |
|-------|----------|-------------------|--------------|
| `recon` | `ares_recon`, `ares_dns`, `web` | No | No (leaf) |
| `scanner` | `ares_scanning`, `ares_recon` | No | No (leaf) |
| `exploit` | `ares_exploit`, `ares_ad` | **Yes** | No (leaf) |
| `ad` | `ares_ad`, `ares_scanning` | **Yes** | No (leaf) |
| `reporter` | `ares_report` | No | No (leaf) |

## File Map

```
plugins/ares/
├── plugin.yaml
├── __init__.py
├── config.py
├── safety/
│   ├── __init__.py
│   ├── scope_validator.py
│   ├── doom_loop.py
│   ├── audit_trail.py
│   └── approval_hardening.py
├── tools/
│   ├── __init__.py
│   ├── base.py
│   ├── recon/
│   │   ├── __init__.py
│   │   ├── nmap_tool.py
│   │   ├── dnsrecon_tool.py
│   │   └── subfinder_tool.py
│   ├── scanning/
│   │   ├── __init__.py
│   │   ├── nuclei_tool.py
│   │   ├── gobuster_tool.py
│   │   ├── ffuf_tool.py
│   │   ├── nikto_tool.py
│   │   └── enum4linux_tool.py
│   ├── exploitation/
│   │   ├── __init__.py
│   │   ├── searchsploit_tool.py
│   │   ├── sqlmap_tool.py
│   │   ├── hydra_tool.py
│   │   ├── metasploit_tool.py
│   │   ├── responder_tool.py
│   │   └── impacket_tool.py
│   ├── ad/
│   │   ├── __init__.py
│   │   ├── bloodhound_tool.py
│   │   ├── certipy_tool.py
│   │   ├── crackmapexec_tool.py
│   │   └── kerbrute_tool.py
│   └── utility/
│       ├── __init__.py
│       └── report_tool.py
├── agents/
│   ├── __init__.py
│   ├── definitions.yaml
│   └── orchestrator.py
└── references/
    ├── port_services.json
    └── cwe_top25.json

~/.cyberfox/
├── profiles/ares/config.yaml
├── ares/scope.yaml
├── ares/audit/
├── ares/reports/
└── skills/cybersec/
    ├── recon/SKILL.md
    ├── scanning/SKILL.md
    ├── exploitation/SKILL.md
    ├── ad-pentesting/SKILL.md
    ├── webapp-testing/SKILL.md
    ├── post-exploitation/SKILL.md
    ├── reporting/SKILL.md
    └── evasion/SKILL.md
```

## Notes

- **Zero Cyberfox core files modified** — everything is a plugin, skill, or config
- **Model:** big-pickle via `provider: custom` — no API key, no GPU needed
- **Kali Linux assumed** — all binaries should be on PATH
- **Tool output truncated** at 2000 lines / 50KB to protect context window
- **Doom loop prevention** stops 3+ identical tool calls
- **Scope validation** blocks out-of-range targets before any tool runs
