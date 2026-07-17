# Cyberfox — Cybersecurity Domain

> **Domain owners:** Cybersecurity team members (fork & PR workflow — see `CONTRIBUTING.md`).
> This document covers the **Ares penetration-testing plugin, its safety layer, the engagement state machine, the platform gateway adapters, and the MCP server**. Implementation-specific, with real file paths.

---

## 1. Domain Overview

The cybersecurity domain is delivered as the **Ares plugin** (`plugins/ares/`) — an autonomous red-team / pentest agent that follows a kill-chain methodology. It is hosted *inside* the AI/ML runtime (see `ai_ml.md`) but owns its own tools, agents, safety controls, and persistence.

| Subsystem | Location | Purpose |
|---|---|---|
| Ares plugin | `plugins/ares/` | Pentest tools, agent roles, safety, state. |
| Gateway adapters | `gateway/platforms/`, `plugins/platforms/` | ~30 messaging/platform integrations that can receive/dispatch agent tasks. |
| MCP server | `mcp_serve.py` | Exposes Cyberfox capabilities (incl. Ares tools) over Model Context Protocol. |
| Agent roles | `plugins/ares/agents/` | Specialized operator personas. |
| Safety layer | `plugins/ares/safety/` | 4-layer guardrail system. |
| State | `plugins/ares/state/` | Engagement state machine + knowledge graph. |
| Findings store | `plugins/ares/findings_db.py` | SQLite findings database (WAL). |

---

## 2. Tech Stack

- Python 3.11+, plugin system (`plugin.yaml` declares the Ares plugin).
- ~35 **external security binaries** invoked via subprocess (nmap, nuclei, masscan, amass, feroxbuster, ffuf, gobuster, nikto, wpscan, sqlmap, hydra, netexec/crackmapexec, impacket-*, responder, bloodhound-python, certipy-ad, kerbrute, theHarvester, dnsrecon, subfinder, wafw00f, searchsploit, msfconsole, burp, snmpwalk, smbclient, enum4linux, whatweb).
- Persistence: **two SQLite DBs** — findings (`~/.cyberfox/ares/findings.db`, WAL) and the engagement knowledge graph (entities + relationships).
- Config: `plugins/ares/config.py` (safety knobs, scope, opsec levels).

---

## 3. Architecture — Kill Chain in Code

```
plugins/ares/
├── tools/
│   ├── recon/         # nmap, dnsrecon, subdomain_enum, masscan, amass, whois, theharvester, whatweb
│   ├── scanning/      # nuclei, gobuster, feroxbuster, ffuf, wfuzz, nikto, wpscan, wafw00f, snmpwalk, burp*, subjack
│   ├── exploitation/  # searchsploit, sqlmap, hydra, msf_*, responder, payload_gen, exploit_chain, curl
│   ├── ad/            # bloodhound, certipy, crackmapexec, kerbrute, impacket (secretsdump/psexec/...)
│   ├── browsing/      # browse_autonomously (stealth browser)
│   ├── utility/       # findings_* , journal_* , orchestration helpers
│   ├── findings_tool.py   # save/query/update findings
│   ├── journal_tool.py    # engagement journal
│   ├── base.py            # ToolBase (subprocess wrapper, JSON result contract)
│   └── orchestration/     # engage_init, plan_create/next/update, entity_* , decide
├── agents/            # orchestrator + 6 specialist roles
│   ├── orchestrator.py
│   ├── cloud_specialist.py
│   ├── malware_analyst.py
│   ├── mobile_specialist.py
│   ├── social_engineer.py
│   └── wireless_specialist.py
├── safety/            # 4-layer guardrails
│   ├── scope_validator.py
│   ├── approval_hardening.py
│   ├── doom_loop.py
│   └── audit_trail.py
├── state/             # engagement + knowledge graph
│   ├── engagement_store.py
│   └── models.py
├── findings_db.py     # SQLite findings store
├── journal_store.py   # SQLite journal store
├── config.py          # safety/scope/opsec config
├── references/        # static reference data (CVEs, templates)
├── hooks/             # lifecycle hooks
└── plugin.yaml        # plugin manifest
```

### 3.1 Kill-chain phases (encoded in tool categories)
1. **Recon** (`tools/recon/`) — passive → active mapping.
2. **Scanning** (`tools/scanning/`) — vuln discovery.
3. **Exploitation** (`tools/exploitation/`) — gain access (requires explicit user approval — see §3.3).
4. **Active Directory** (`tools/ad/`) — domain escalation.
5. **Reporting** — `findings_*` tools + `journal_*` produce the deliverable.

Each phase feeds the next; the orchestrator (`agents/orchestrator.py`) enforces sequential progression and never skips phases.

### 3.2 Tool contract
- Every tool subclasses `tools/base.py::ToolBase`.
- Tools return JSON with common fields: `success`, `data`, `error`.
- `tools/base.py` is the subprocess wrapper that invokes the external binary and normalizes output. **To add a tool:** subclass `ToolBase`, declare binary + params, implement `run()`, return the standard JSON envelope.

### 3.3 Safety layer — 4 layers (`plugins/ares/safety/`)
1. **`scope_validator.py`** — rejects any target outside `scope.yaml` / authorized scope. Hard block.
2. **`approval_hardening.py`** — requires explicit user approval before *any* exploit-class tool runs. No silent exploitation.
3. **`doom_loop.py`** — caps repeated tool calls / phase retries to prevent runaway autonomous loops (complements the AI/ML iteration budget).
4. **`audit_trail.py`** — logs every tool invocation (who/what/when/target) to the audit store for the report and OPSEC review.

**OPSEC levels** per phase (from `AGENTS.md`): Recon=low noise, Scanning=medium, Exploit=high, AD=very high. Tools read the opsec level from `config.py` to rate-limit / choose stealth flags.

### 3.4 State & knowledge graph (`plugins/ares/state/`)
- `engagement_store.py` — engagement lifecycle: `planning → recon → scanning → enumeration → validation → exploitation → reporting → completed`.
- `models.py` — entity types (`host, port, service, technology, vulnerability, finding, credential, subdomain, user, group`) and relationships (`has_port, has_service, uses_tech, has_vulnerability, discovered_by, authenticated_with, resolves_to, member_of`).
- Dual persistence: findings in `findings_db.py`; entities/relations in the graph store. Both WAL-mode SQLite.

### 3.5 Agent roles (`plugins/ares/agents/`)
- `orchestrator.py` — drives the kill chain, plans, decides.
- Specialists: `cloud_specialist, malware_analyst, mobile_specialist, social_engineer, wireless_specialist`.
- The AGENTS.md describes 12 conceptual roles (including web, OSINT, etc.); the code currently ships 6 specialist files + orchestrator. New roles = new file in `agents/` exposing a role descriptor.

---

## 4. Gateway & Platform Adapters

- `gateway/platforms/` — built-in adapters: `signal, whatsapp_cloud, bluebubbles, weixin, yuanbao, qqbot, api_server, webhook, + helpers`.
- `plugins/platforms/` — **~20 plugin adapters**: `discord, telegram, slack, matrix, irc, email, sms, teams, mattermost, line, feishu, wecom, dingtalk, google_chat, homeassistant, ntfy, simplex, photon, raft, whatsapp, ...`.
- `gateway/platform_registry.py` — central registry; built-ins use an `if/elif` factory, plugin adapters self-register via `PluginContext.register_platform()`. New adapter = implement `gateway/platforms/base.py::PlatformAdapter` + register.
- These adapters let Ares/operators receive tasks and push results over chat platforms. They are **transport**, not security logic.

---

## 5. MCP Server — `mcp_serve.py`

- Exposes Cyberfox (and Ares) tools over the **Model Context Protocol** so external MCP clients can drive the agent.
- ~35KB; defines MCP tool schemas that wrap the same backend functions the dashboard uses.
- Security note: MCP exposes powerful tools — keep the auth/model scoping consistent with the dashboard auth (`plugins/dashboard_auth/`).

---

## 6. Key Files Reference

| Path | What to touch |
|---|---|
| `plugins/ares/tools/base.py` | Tool base class / subprocess contract |
| `plugins/ares/tools/{recon,scanning,exploitation,ad,browsing,utility}/` | Tool implementations |
| `plugins/ares/agents/` | Agent roles |
| `plugins/ares/safety/{scope_validator,approval_hardening,doom_loop,audit_trail}.py` | Safety layers |
| `plugins/ares/state/{engagement_store,models}.py` | Engagement + graph |
| `plugins/ares/findings_db.py` | Findings SQLite |
| `plugins/ares/config.py` | Safety/scope/opsec knobs |
| `plugins/ares/plugin.yaml` | Plugin manifest |
| `gateway/platforms/`, `plugins/platforms/` | Platform adapters (~30) |
| `gateway/platform_registry.py` | Adapter registry |
| `mcp_serve.py` | MCP server |

---

## 7. How Cybersec Members Should Work

1. **Fork**, branch `sec/<feature>` (see `CONTRIBUTING.md`).
2. **Add a tool:** subclass `ToolBase` in the correct phase dir (`recon/scanning/exploitation/ad/...`); declare the binary + params; return standard JSON. Register if needed.
3. **Add an agent role:** new file in `plugins/ares/agents/` with a role descriptor; wire into orchestrator planning if it's a phase owner.
4. **Add a safety control:** extend `plugins/ares/safety/` and ensure `approval_hardening.py` gating covers exploit tools. Never disable scope validation or approval.
5. **Add a platform adapter:** implement `PlatformAdapter` in `gateway/platforms/` or `plugins/platforms/` and register in `platform_registry.py`.
6. **Never** weaken the 4 safety layers or remove the audit trail — these are mandatory for authorized engagements and legal defensibility.
7. **PR** to `main` (protected, requires review). Do not push directly.

### Conventions to preserve
- Every finding saved immediately via `findings_db` (never batch at end).
- Exploitation tools require explicit approval (`approval_hardening`).
- Targets outside `scope.yaml` are hard-blocked (`scope_validator`).
- Clean up artifacts after exploitation; document every attempt (success or fail).
- Follow the kill chain order — no phase skipping.
