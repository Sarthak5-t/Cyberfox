# Cyberfox

<p align="center">
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
   <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Version-4.3.0-blue?style=for-the-badge" alt="Version"></a>
    <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Tools-103-red?style=for-the-badge" alt="Tools"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Platform-Kali%20Linux-purple?style=for-the-badge" alt="Platform"></a>
</p>

<p align="center">
  <b>Elite cybersecurity operations agent</b> with 103 tools, bug bounty pipeline, agentic AI, knowledge graph, dynamic MCP servers, and stealth browsing.
</p>

---

## What's New (v4.3.0)

### Free AI Model Providers (NEW)
- **DeepInfra, Groq, Cloudflare Workers AI, GitHub Models** — 4 new no-cost providers added to the model picker
- **OpenCode Zen** — `big-pickle` model, 200K context, $0, anonymous, no API key needed
- All new providers show in TUI `/model` without env vars via aggregator discovery bypass

### Context Compaction (IMPROVED)
- Default compaction threshold raised from **50% → 85%** — 200K models now fire at ~170K instead of ~100K
- Matches OpenCode's approach: maximize usable context before summarization triggers

### Medium Article Reader (NEW)
- `medium_read` tool with **freedium cache bypass** — no paywall, no Cloudflare, no browser needed
- 3-tier fallback: freedium → RSS → Playwright browser
- Extracts title, author, date, and full article body from member-only content in ~1s

### CVE Knowledge Base (NEW)
- Local SQLite CVE database with PoC storage, search, and lookup
- Integrated with `searchsploit_tool` — results merged from both searchsploit and CVE KB
- CVE enrichment pipeline pulls PoCs from KB; reflection hook captures them as entity metadata

### ACP Mesh Agent Networking (NEW)
- `mesh_join`, `mesh_status`, `mesh_leave` — agent mesh for distributed operations
- `ares_delegate(remote=True)` — delegate tasks to remote mesh agents
- Enables multi-host penetration testing coordination

### Dynamic MCP Servers (NEW)
- `mcp_server_connect`, `mcp_server_call`, `mcp_server_disconnect` — attach any external MCP server (Burp Suite, custom harnesses, tool mocks) mid-engagement, call its tools by name, then disconnect
- Transports: stdio, Server-Sent Events (SSE), WebSocket — with per-server persistent async sessions on a shared event loop

### 34 New Security Tools
| Category | Tools |
|----------|-------|
| **Recon** | sherlock, recon-ng, dnsenum, fierce, dnsmap, dmitry, holehe |
| **Scanning** | commix, xsstrike, zap, cmsmap, wapiti, uniscan |
| **Exploitation** | hashcat, john, cewl, crunch, medusa, patator, beef, bettercap, rsmangler, chisel, kali_exec |
| **Wireless** | aircrack-ng |
| **Forensics** | volatility |
| **Infrastructure** | Mesh join/status/leave, CVE KB (4 tools), medium_read |

## What's New (v4.2.0)

### Bug Bounty Integration Layer (NEW)
- **9 Bug Bounty Modules** — Rate limiter, scope enforcer, OPSEC, WAF advisor, proxy manager, auth handler, vuln validator, orchestrator, HackerOne API
- **Full Kill-Chain Pipeline** — 9-stage automated pipeline: recon → probe → port → WAF detect → vuln scan → crawl → inject → validate → report
- **Rate Limiting** — Token bucket with per-target tracking, ban detection, exponential backoff
- **Scope Enforcement** — Hard boundary with wildcard, CIDR, URL, and exclusion support
- **WAF Detection** — 13 WAF signatures with automatic scan strategy adjustment
- **Proxy Rotation** — Round-robin with health tracking, Tor support, and automatic failover
- **Auth Management** — Form/basic/bearer/API key login with CSRF capture and session persistence
- **Vuln Validation** — Replay + false positive filtering + retest with alternate payloads
- **HackerOne API** — Authenticated report submission, scope lookup, attachments

### Agentic AI System (NEW)
- **Agent Lifecycle** — Creation, execution, monitoring, and termination
- **Inter-Agent Communication** — Message bus with publish/subscribe
- **Task Routing** — Automatic classification and specialist assignment
- **Checkpoint System** — Save/restore agent state for long-running operations
- **Working Memory** — Short-term LRU cache for active context
- **Episodic Memory** — Event recording and retrieval
- **Semantic Memory** — Knowledge store with vector similarity search
- **Procedural Memory** — Procedure storage and replay
- **Long-Term Memory** — Persistent learning across sessions
- **Skill Hub** — Dynamic skill registration, scoring, and versioning
- **Adaptive Thinking** — Strategy selection based on complexity estimation
- **Reasoning Chains** — Multi-step logical reasoning
- **Context-Aware Planning** — Dynamic plan generation and adaptation
- **Decision Framework** — Evidence-based decision making with confidence tracking
- **Process Management** — Process spawning, monitoring, and cleanup
- **Enhanced Shell** — Command execution with history and aliasing
- **Security Sandbox** — Filesystem/network confinement for tool execution
- **System Monitor** — CPU, memory, disk, and network monitoring

### Previous Features
- **Tool Governance** — 5-tier permission system (NONE → READ_ONLY → WRITE → EXECUTE → DANGEROUS) for all 100 tools
- **TokenJuice Compressor** — Content-aware output compression (JSON 80%, HTML 96%, Logs 81% smaller)
- **Sandbox** — Landlock/Docker/chroot jail confinement for tool subprocesses
- **Model Router** — Auto-selects best AI model per task type (scan, exploit, report, code, chat)
- **Encrypted Secrets** — Fernet (AES-CBC) encrypted API keys with PBKDF2 key derivation
- **Model Council** — Multi-model deliberation with weighted voting for critical decisions
- **Memory Tree** — Hierarchical summary tree for large tool outputs
- **Agent Intelligence Layer** — Structured plan, act, reflect, adapt loop
- **Knowledge Graph** — SQLite-backed entities + relationships
- **100 Security Tools** — Nmap, Nuclei, Metasploit, Burp Suite, BloodHound, Certipy, and more

---

## Features

### Agent Intelligence

Cyberfox doesn't just run commands — it plans, executes, reflects, and adapts.

```
User: Find vulnerabilities on app.example.com
    |
    v
engage_init -> plan_create -> plan_next
    |
    v
[Execute tool] -> [Extract entities] -> [Reflect] -> [Replan]
    |
    v
Continue autonomously until goal achieved
```

| Component | What It Does |
|-----------|-------------|
| **Plan** | Kill-chain template with dynamic task expansion |
| **Knowledge Graph** | Tracks hosts, ports, services, techs, vulns, creds as connected entities |
| **Reflection** | Post-tool hook auto-extracts entities from output |
| **Decision Log** | Records why you changed approach |
| **Event Bus** | Publishes events (PORT_FOUND, HTTP_DETECTED, etc.) for specialist agents |

### Orchestration Tools

| Tool | Purpose |
|------|---------|
| `engage_init` | Start new engagement with scope and goals |
| `engage_resume` | Resume a previous engagement |
| `engage_status` | Current state, entity counts, plan progress |
| `plan_create` | Generate plan from kill-chain template |
| `plan_next` | Get next pending task (respects dependencies) |
| `plan_update` | Mark task completed/failed/skipped |
| `plan_add` | Dynamically add tasks from discoveries |
| `entity_save` | Save entity to knowledge graph |
| `entity_query` | Query entities by type/name |
| `entity_graph` | Get full graph or subgraph around an entity |
| `entity_link` | Create relationship between entities |
| `entity_count` | Count entities by type |
| `decide` | Log decision with reasoning |

### Knowledge Graph

Entities are stored in SQLite and connected by typed relationships:

```
Host (10.10.10.10)
  |-- has_port --> Port (80/tcp)
                     |-- has_service --> Service (Apache/2.4.57)
                                          |-- uses_tech --> Technology (WordPress)
                                          |-- has_vulnerability --> Vulnerability (CVE-2024-xxxx)
Credential (admin:pass) -- authenticated_with --> Service (Apache)
```

**Entity types:** host, domain, subdomain, port, service, technology, vulnerability, finding, credential, user, group

**Relationship types:** has_port, has_service, uses_tech, has_vulnerability, discovered_by, authenticated_with, resolves_to, member_of, and more

### Security Capabilities

| Category | Tools | Description |
|----------|-------|-------------|
| **Reconnaissance** | 15 tools | Nmap, DNSRecon, Subfinder, Masscan, Amass, Whois, TheHarvester, WhatWeb, Sherlock, Recon-ng, DNSEnum, Fierce, DNSMap, Dmitry, Holehe |
| **Scanning** | 20 tools | Nuclei, Gobuster, Feroxbuster, FFUF, Nikto, WPScan, Burp Suite, Commix, XSStrike, ZAP, CMSMap, Wapiti, UniScan, and more |
| **Exploitation** | 24 tools | SQLMap, Hydra, Metasploit, Responder, Impacket, Hashcat, John, Cewl, Crunch, Medusa, Patator, BeEF, Bettercap, Chisel, custom exploit chains |
| **Active Directory** | 6 tools | BloodHound, Certipy, CrackMapExec, Kerbrute, Impacket |
| **Wireless** | 1 tool | Aircrack-ng |
| **Forensics** | 1 tool | Volatility |
| **Browsing** | 1 tool | Stealth web browsing with anti-bot-detection |
| **Mesh Networking** | 3 tools | Mesh join/status/leave for distributed agent coordination |
| **CVE Knowledge Base** | 4 tools | CVE search, lookup, stats, PoC database |
| **MCP Integration** | 3 tools | Dynamic MCP server connect/call/disconnect (stdio, SSE, WS) |
| **Orchestration** | 13 tools | Engagement, planning, knowledge graph, decisions |
| **Bug Bounty** | 9 modules | Rate limiter, scope enforcer, OPSEC, WAF advisor, proxy, auth, validator, orchestrator, HackerOne |
| **Agentic AI** | 16 modules | Agents, memory, skills, reasoning, OS interaction |
| **Utility** | 14 tools | Findings, journal, reporting, delegation, medium_read, mesh, MCP tools |

### Tool Governance

Every tool has a formal permission level and metadata:

```python
from plugins.ares.tools import PermissionLevel, get_tool_permission, ToolCategory

# 5-tier permission system
# NONE → READ_ONLY → WRITE → EXECUTE → DANGEROUS

perm, ext, cat, timeout = get_tool_permission("nmap_scan")
# PermissionLevel.EXECUTE, False, ToolCategory.RECON, 600

perm, ext, cat, timeout = get_tool_permission("sqlmap_scan")
# PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 900
```

| Permission | Tools | What It Means |
|-----------|-------|---------------|
| `READ_ONLY` | whois, wafw00f, msf_search, findings_query | No side effects |
| `WRITE` | findings_save, findings_update, journal_* | Writes to local DB/files |
| `EXECUTE` | nmap, nuclei, gobuster, feroxbuster | Runs system commands |
| `DANGEROUS` | sqlmap, hydra, msf_exec, bloodhound, crackmapexec | Exploitation, credential attacks |

### Token Compression (TokenJuice)

Content-aware compression before output hits the AI context window:

| Content Type | Rule | Savings |
|-------------|------|---------|
| JSON | Strip nulls/empties, compact whitespace, collapse arrays | ~80% |
| HTML | Strip tags/scripts, keep text content | ~96% |
| Logs | Collapse repeated lines into count summary | ~81% |
| Code | Remove common indentation, leading blanks | ~20% |
| XML | Remove comments, collapse empty elements | ~30% |

### Sandbox Confinement

Tool subprocesses run in a jail with filesystem restrictions:

| Method | When Used | Security |
|--------|-----------|----------|
| Landlock LSM | Linux 5.13+ kernels | Kernel-enforced, least privilege |
| Docker | Docker daemon running | Container isolation, no network |
| chroot | Fallback | Basic filesystem isolation |
| none | Last resort | Logs warning, runs unconfined |

### Model Routing

Auto-selects the best AI model based on task type:

| Task | Preferred Capabilities | Example Models |
|------|----------------------|----------------|
| Scan | TOOL_USE + FAST | qwen-local, gpt-4o-mini |
| Exploit | TOOL_USE + REASONING | claude-sonnet, gpt-4o |
| Report | CHAT + CHEAP | gpt-4o-mini, local |
| Code | CODE + TOOL_USE | claude-sonnet, gpt-4o |
| Chat | CHAT + FAST + CHEAP | qwen-local, gpt-4o-mini |

### Stealth Browsing

The `browse_autonomously` tool opens a real Chromium browser with:
- **playwright-stealth** — anti-detection patches
- **WebDriver flag disabled** — avoids headless detection
- **Chrome runtime spoofing** — appears as real browser
- **Cloudflare bypass** — detects and waits through challenges
- **Turnstile checkbox clicking** — auto-solves Turnstile CAPTCHAs
- **JS rendering wait** — waits for data tables and dynamic content

### Specialist Roles

| Role | Focus |
|------|-------|
| **Pentester** | Reconnaissance and exploitation |
| **SOC Analyst** | Defensive security analysis |
| **Cloud Security** | AWS, Azure, GCP testing |
| **Mobile Security** | Android/iOS app security |
| **Wireless Security** | WiFi and Bluetooth |
| **Social Engineering** | Phishing and pretexting |
| **Malware Analyst** | Reverse engineering |
| **AD Specialist** | Active Directory attacks |
| **Web Attacker** | Web app exploitation |
| **OSINT Analyst** | Passive reconnaissance |
| **Privilege Escalation** | Local and domain privesc |
| **Lead Orchestrator** | Engagement coordination |

### Kill-Chain Methodology

```
1. RECON -> 2. SCANNING -> 3. EXPLOITATION -> 4. AD ATTACKS -> 5. REPORTING
```

| Phase | Objective | Key Tools |
|-------|-----------|-----------|
| **Recon** | Map the attack surface | Nmap, Masscan, Subfinder, Amass |
| **Scanning** | Find exploitable weaknesses | Nuclei, Burp Suite, Nikto, Gobuster |
| **Exploitation** | Gain access, prove impact | SQLMap, Metasploit, Hydra, Responder |
| **AD Attacks** | Escalate to Domain Admin | BloodHound, Kerberoast, Certipy |
| **Reporting** | Deliver actionable findings | Findings DB, CVSS scoring, Reports |

### Bug Bounty Pipeline

```
PASSIVE_RECON -> LIVE_PROBE -> PORT_SCAN -> WAF_DETECT -> VULN_SCAN -> CRAWL -> INJECT -> VALIDATE -> REPORT
```

| Stage | What Runs | Safety Layer |
|-------|-----------|--------------|
| **Passive Recon** | subfinder, dig, curl probe | Scope check, rate limit |
| **Live Probe** | nmap service scan | Rate limit, jitter |
| **Port Scan** | nmap full port scan | Rate limit, jitter |
| **WAF Detect** | wafw00f / heuristic | Adjusts all downstream params |
| **Vuln Scan** | nuclei templates | Rate limit, proxy, tamper |
| **Crawl** | feroxbuster dirs | Rate limit, proxy |
| **Inject** | sqlmap, XSS/CMDi probes | Scope check, rate limit, auth |
| **Validate** | Replay + FP filter | False positive removal |
| **Report** | Markdown + JSON | Findings database |

---

## Installation

### Prerequisites

- Kali Linux (required)
- Python 3.11+
- Node.js

### From Source

```bash
git clone https://github.com/Sarthak5-t/Cyberfox.git
cd Cyberfox
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Quick Start

```bash
cyberfox              # Start interactive CLI
cyberfox model        # Choose your LLM provider
cyberfox setup        # Run setup wizard
```

### OpenRouter Setup

```bash
echo 'OPENROUTER_API_KEY=your_key_here' >> ~/.cyberfox/.env
cyberfox model
# Select: openrouter -> tencent/hy3:free
```

---

## Usage

### Basic Commands

```bash
cyberfox                    # Start interactive session
cyberfox model              # Switch LLM provider/model
cyberfox tools              # Configure enabled tools
cyberfox config set         # Set configuration values
cyberfox update             # Update to latest version
cyberfox doctor             # Diagnose issues
```

### Bug Bounty Pipeline

```python
from plugins.ares.bugbounty import get_orchestrator, get_scope_enforcer

# Configure scope
scope = get_scope_enforcer()
scope.set_scope(["*.example.com", "10.0.0.0/8"], ["staging.example.com"])

# Run full pipeline
orch = get_orchestrator()
result = orch.run(
    target="app.example.com",
    max_rps=10.0,  # Respect program rules
)

# Results
print(f"Findings: {result['findings_count']}")
print(f"Stages: {result['stages_completed']}")
for finding in result["findings"]:
    print(f"  [{finding['severity']}] {finding['title']}")
```

### Individual Modules

```python
# Rate limiting
from plugins.ares.bugbounty import get_rate_limiter
rl = get_rate_limiter()
rl.configure_for_program(max_rps=5.0)  # HackerOne program limit
rl.wait_if_needed("target.com")
rl.report_response("target.com", 429)  # Auto-backoff

# WAF detection + strategy
from plugins.ares.bugbounty import get_waf_advisor
waf = get_waf_advisor()
result = waf.detect("https://target.com")
strategy = waf.get_strategy(result)
# strategy.rate_limit = 3.0, strategy.use_proxy = True, etc.

# Auth management
from plugins.ares.bugbounty import get_auth_handler
auth = get_auth_handler()
auth.login_form("target.com", "https://target.com/login",
                "admin", "password123")
headers = auth.get_auth_headers("target.com")

# Vuln validation
from plugins.ares.bugbounty import get_vuln_validator, Finding
validator = get_vuln_validator()
finding = Finding(title="SQL Injection", severity="critical",
                  target="target.com", url="http://target.com?id=1' OR 1=1--")
result = validator.validate(finding)
# result.confirmed = True, result.confidence = 0.85

# HackerOne submission
from plugins.ares.bugbounty import get_hackerone
h1 = get_hackerone()
h1.authenticate()
h1.create_report("program-handle", report)
```

### Autonomous Engagement

```bash
cyberfox
> Scan 10.10.10.10 for vulnerabilities and get root
```

The agent will automatically:
1. Initialize an engagement and create a plan
2. Execute reconnaissance (nmap, whatweb, etc.)
3. Save discoveries to the knowledge graph
4. Expand the plan based on findings
5. Continue through exploitation phases
6. Report results with full evidence

### Manual Orchestration

```bash
cyberfox
> engage_init targeting 10.10.10.10
> plan_create
> plan_next
> [run nmap scan]
> entity_save type=host name=10.10.10.10
> plan_update task_id=1 status=completed
> decide reasoning="HTTP found" action="queue web scanning"
```

---

## Architecture

```
cyberfox/
├── agent/                  # Core agent logic
├── cyberfox_cli/           # CLI interface
├── plugins/
│   └── ares/               # Cybersecurity plugin (v4.2.0)
│       ├── state/          # Engagement state + knowledge graph
│       │   ├── models.py       # Entity, Relationship, PlanTask dataclasses
│       │   └── engagement_store.py  # SQLite CRUD
│       ├── hooks/          # Auto-reflection + event bus
│       │   └── reflection.py   # Post-tool entity extraction
│       ├── agentic.py      # Unified API for all agentic + bug bounty capabilities
│       ├── agents/         # Agent lifecycle, communication, routing, checkpointing
│       ├── memory/         # Working, episodic, semantic, procedural, longterm memory
│       ├── skills/         # Skill hub, scoring, learning, versioning
│       ├── reasoning/      # Adaptive thinking, chains, planning, decisions
│       ├── os_interaction/ # Process management, shell, sandbox, monitoring
│       ├── bugbounty/      # Bug bounty integration layer
│       │   ├── rate_limiter.py     # Token bucket + ban detection
│       │   ├── scope_enforcer.py   # Hard boundary enforcement
│       │   ├── opsec.py            # UA rotation, headers, jitter
│       │   ├── waf_advisor.py      # WAF detection + strategy
│       │   ├── proxy_manager.py    # Tor + proxy rotation
│       │   ├── auth_handler.py     # Session management
│       │   ├── vuln_validator.py   # Finding confirmation
│       │   ├── orchestrator.py     # 9-stage pipeline engine
│       │   └── platform_api.py     # HackerOne integration
│       ├── cve_kb/          # CVE knowledge base + PoC storage
│       ├── mesh/            # ACP agent mesh networking
│       ├── mcp/             # Model Context Protocol servers
│       ├── mcp/             # MCP server connection manager
│       ├── tools/
│       │   ├── permission.py   # 5-tier permission system + tool governance
│       │   ├── tokenjuice.py   # Content-aware token compressor
│       │   ├── sandbox.py      # Landlock/Docker/chroot jail
│       │   ├── router.py       # Task-based model routing
│       │   ├── secrets.py      # Fernet-encrypted secrets store
│       │   ├── council.py      # Multi-model deliberation
│       │   ├── memory_tree.py  # Hierarchical output summaries
│       │   ├── orchestration/  # 13 orchestration tools
│       │   ├── recon/          # 15 recon tools
│       │   ├── scanning/       # 20 scanning tools
│       │   ├── exploitation/   # 24 exploit tools
│       │   ├── ad/             # 6 AD tools
│       │   ├── wireless/       # Aircrack-ng
│       │   ├── forensics/      # Volatility
│       │   ├── kali/           # Kali integration
│       │   ├── mesh/           # Mesh tools (join/status/leave)
│       │   ├── browsing/       # Stealth browsing
│       │   └── utility/        # Findings, journal, reports
│       ├── agents/         # 12 specialist roles
│       ├── references/     # 14 security reference files
│       └── safety/         # Permission gating, scope validation, audit trail
├── skills/
│   └── ares/               # 11 expert skills
└── project_info/           # Domain documentation
```

---

## Skills

| Skill | Description |
|-------|-------------|
| `ares/lead` | Main pentest orchestration |
| `ares/recon` | Reconnaissance methodology |
| `ares/scanning` | Vulnerability scanning |
| `ares/exploit` | Exploitation techniques |
| `ares/ad` | Active Directory attacks |
| `ares/cloud_pentest` | Cloud security testing |
| `ares/mobile_pentest` | Mobile app security |
| `ares/wireless_pentest` | Wireless security testing |
| `ares/social_engineering` | Social engineering assessments |
| `ares/physical_pentest` | Physical security testing |
| `ares/report` | Report generation |

---

## References

| Reference | Content |
|-----------|---------|
| `owasp_top10.md` | OWASP Top 10 vulnerabilities |
| `owasp_api_security.md` | API security top 10 |
| `cloud_security.md` | AWS, Azure, GCP security |
| `container_security.md` | Docker, Kubernetes security |
| `mobile_security.md` | Android/iOS security |
| `wireless_security.md` | WiFi, Bluetooth security |
| `social_engineering.md` | Social engineering techniques |
| `physical_security.md` | Physical security testing |
| `ad_attack_tree.md` | AD attack methodology |
| `mitre_attack_mapping.md` | MITRE ATT&CK mapping |

---

## Safety Features

- **Permission Levels** — 5-tier tool governance (NONE → READ_ONLY → WRITE → EXECUTE → DANGEROUS)
- **Scope Validation** — Only targets within authorized scope (wildcard/CIDR/URL/exclusions)
- **Approval Gates** — Dangerous tools require explicit user confirmation
- **Sandbox Confinement** — Landlock/Docker/chroot jail for tool subprocesses
- **Encrypted Secrets** — Fernet-encrypted API keys with PBKDF2 derivation
- **Audit Trail** — Complete logging of all actions with sanitized arguments
- **Doom Loop Detection** — Prevents infinite retry loops
- **Token Compression** — Reduces API costs while preserving signal
- **OPSEC Guidelines** — Phase-appropriate noise levels
- **Rate Limiting** — Token bucket with per-target tracking and ban detection
- **WAF Awareness** — Auto-adjusts scan speed and evasion when WAF detected
- **Proxy Rotation** — IP rotation with health tracking and Tor support
- **Vulnerability Validation** — False positive filtering before report submission

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/Sarthak5-t/Cyberfox.git
cd Cyberfox
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
```

---

<p align="center">
  <b>Created by <a href="https://linkedin.com/in/khatalsarthak">Sarthak Khatal</a></b>
</p>
