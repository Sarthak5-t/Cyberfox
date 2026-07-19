# Cyberfox

<p align="center">
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Version-4.0.0-blue?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Tools-65-red?style=for-the-badge" alt="Tools"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Platform-Kali%20Linux-purple?style=for-the-badge" alt="Platform"></a>
</p>

<p align="center">
  <b>Elite cybersecurity operations agent</b> with 65 tools, knowledge graph, autonomous orchestration, and stealth browsing.
</p>

---

## What's New (v4.1.0)

- **Tool Governance** — 5-tier permission system (NONE → READ_ONLY → WRITE → EXECUTE → DANGEROUS) for all 51 tools
- **TokenJuice Compressor** — Content-aware output compression (JSON 80%, HTML 96%, Logs 81% smaller)
- **Sandbox** — Landlock/Docker/chroot jail confinement for tool subprocesses
- **Model Router** — Auto-selects best AI model per task type (scan, exploit, report, code, chat)
- **Encrypted Secrets** — Fernet (AES-CBC) encrypted API keys with PBKDF2 key derivation
- **Model Council** — Multi-model deliberation with weighted voting for critical decisions
- **Memory Tree** — Hierarchical summary tree for large tool outputs
- **Agent Intelligence Layer** — Structured plan, act, reflect, adapt loop
- **Knowledge Graph** — SQLite-backed entities + relationships
- **65 Security Tools** — Nmap, Nuclei, Metasploit, Burp Suite, BloodHound, Certipy, and more

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
| **Reconnaissance** | 8 tools | Nmap, DNSRecon, Subfinder, Masscan, Amass, Whois, TheHarvester, WhatWeb |
| **Scanning** | 17 tools | Nuclei, Gobuster, Feroxbuster, FFUF, Nikto, WPScan, Burp Suite, and more |
| **Exploitation** | 13 tools | SQLMap, Hydra, Metasploit, Responder, Impacket, custom exploit chains |
| **Active Directory** | 6 tools | BloodHound, Certipy, CrackMapExec, Kerbrute, Impacket |
| **Browsing** | 1 tool | Stealth web browsing with anti-bot-detection |
| **Orchestration** | 13 tools | Engagement, planning, knowledge graph, decisions |
| **Utility** | 9 tools | Findings, journal, reporting, delegation |

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
│   └── ares/               # Cybersecurity plugin (v4.1.0)
│       ├── state/          # Engagement state + knowledge graph
│       │   ├── models.py       # Entity, Relationship, PlanTask dataclasses
│       │   └── engagement_store.py  # SQLite CRUD
│       ├── hooks/          # Auto-reflection + event bus
│       │   └── reflection.py   # Post-tool entity extraction
│       ├── tools/
│       │   ├── permission.py   # 5-tier permission system + tool governance
│       │   ├── tokenjuice.py   # Content-aware token compressor
│       │   ├── sandbox.py      # Landlock/Docker/chroot jail
│       │   ├── router.py       # Task-based model routing
│       │   ├── secrets.py      # Fernet-encrypted secrets store
│       │   ├── council.py      # Multi-model deliberation
│       │   ├── memory_tree.py  # Hierarchical output summaries
│       │   ├── orchestration/  # 13 orchestration tools
│       │   ├── recon/          # 8 recon tools
│       │   ├── scanning/       # 17 scanning tools
│       │   ├── exploitation/   # 13 exploit tools
│       │   ├── ad/             # 6 AD tools
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
- **Scope Validation** — Only targets within authorized scope
- **Approval Gates** — Dangerous tools require explicit user confirmation
- **Sandbox Confinement** — Landlock/Docker/chroot jail for tool subprocesses
- **Encrypted Secrets** — Fernet-encrypted API keys with PBKDF2 derivation
- **Audit Trail** — Complete logging of all actions with sanitized arguments
- **Doom Loop Detection** — Prevents infinite retry loops
- **Token Compression** — Reduces API costs while preserving signal
- **OPSEC Guidelines** — Phase-appropriate noise levels

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
