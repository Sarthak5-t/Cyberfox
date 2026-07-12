# Cyberfox 🔥

<p align="center">
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Tools-52+-red?style=for-the-badge" alt="Tools"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Platform-Kali%20Linux-purple?style=for-the-badge" alt="Platform"></a>
</p>

<p align="center">
  <b>Elite cybersecurity operations agent</b> with 52+ security tools, 12 specialist roles, stealth browsing, and full kill-chain methodology.
</p>

---

## What's New (v1.0.0)

- **52+ Security Tools** — Nmap, Nuclei, Metasploit, Burp Suite, BloodHound, Certipy, and more
- **Stealth Browsing** — Anti-bot-detection browser with Cloudflare bypass, CAPTCHA handling, and fingerprint spoofing
- **Engagement Journal** — Persistent memory across turns — track discoveries, CVEs, credentials, and decisions
- **OpenRouter Integration** — Use any model via OpenRouter (default: `tencent/hy3:free`)
- **12 Specialist Roles** — Pentester, SOC Analyst, Cloud Security, Mobile, Wireless, Social Engineering, Malware, AD, Web, OSINT, Privesc, Lead
- **11 Expert Skills** — Recon, Scanning, Exploitation, AD, Cloud, Mobile, Wireless, Social Engineering, Physical, Report, Evasion
- **14 Reference Files** — OWASP, MITRE ATT&CK, Cloud Security, AD Attack Trees, and more

---

## Features

### Security Capabilities

| Category | Tools | Description |
|----------|-------|-------------|
| **Reconnaissance** | 8 tools | Nmap, DNSRecon, Subfinder, Masscan, Amass, Whois, TheHarvester, WhatWeb |
| **Scanning** | 17 tools | Nuclei, Gobuster, Feroxbuster, FFUF, Nikto, WPScan, Burp Suite, and more |
| **Exploitation** | 13 tools | SQLMap, Hydra, Metasploit, Responder, Impacket, custom exploit chains |
| **Active Directory** | 4 tools | BloodHound, Certipy, CrackMapExec, Kerbrute |
| **Browsing** | 1 tool | Stealth web browsing with anti-bot-detection |
| **Utility** | 9 tools | Findings management, engagement journal, reporting, delegation |

### Stealth Browsing

The `browse_autonomously` tool opens a real Chromium browser with:
- **playwright-stealth** — anti-detection patches
- **WebDriver flag disabled** — avoids headless detection
- **Chrome runtime spoofing** — appears as real browser
- **Cloudflare bypass** — detects and waits through challenges
- **Turnstile checkbox clicking** — auto-solves Turnstile CAPTCHAs
- **JS rendering wait** — waits for data tables and dynamic content

### Engagement Journal

Persistent markdown memory at `~/.cyberfox/ares/journal.md`:
- `journal_init` — Start a new engagement
- `journal_write` — Log discoveries (CVEs, credentials, decisions)
- `journal_read` — Recall progress across turns

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
1. RECON → 2. SCANNING → 3. EXPLOITATION → 4. AD ATTACKS → 5. REPORTING
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

- Kali Linux (required — no Windows/macOS support)
- Python 3.11+
- Node.js (for agent-browser)

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
# Add your OpenRouter API key
echo 'OPENROUTER_API_KEY=your_key_here' >> ~/.cyberfox/.env

# Configure model
cyberfox model
# Select: openrouter → tencent/hy3:free
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

### Ares Plugin

The Ares cybersecurity plugin provides all security tools:

```bash
# Enable the plugin
echo "plugins:\n  enabled:\n    - ares" >> ~/.cyberfox/config.yaml

# Start a pentest session
cyberfox
> Run an nmap scan against 10.10.10.10
```

### Example Workflow

```
> Scan target 10.10.10.10 for open ports
> Enumerate services on discovered ports
> Run nuclei scan for known vulnerabilities
> Attempt SQL injection on web application
> Browse exploit-db for public exploits
> Export findings to report
```

---

## Architecture

```
cyberfox/
├── agent/              # Core agent logic
├── cyberfox_cli/       # CLI interface
├── plugins/
│   └── ares/           # Cybersecurity plugin
│       ├── tools/      # 52+ security tools
│       │   ├── recon/          # 8 recon tools
│       │   ├── scanning/       # 17 scanning tools
│       │   ├── exploitation/   # 13 exploit tools
│       │   ├── ad/             # 4 AD tools
│       │   ├── browsing/       # Stealth browsing
│       │   └── utility/        # Findings, journal, reports
│       ├── agents/     # 12 specialist roles
│       ├── references/ # 14 security reference files
│       └── safety/     # Scope validation, audit trail
├── skills/
│   └── ares/           # 11 expert skills
│       ├── recon/      # Reconnaissance
│       ├── scanning/   # Vulnerability scanning
│       ├── exploit/    # Exploitation
│       ├── ad/         # Active Directory
│       ├── cloud_pentest/
│       ├── mobile_pentest/
│       ├── wireless_pentest/
│       ├── social_engineering/
│       ├── physical_pentest/
│       ├── report/
│       └── evasion/
└── docs/               # Documentation
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

- **Scope Validation** — Only targets within authorized scope
- **Approval Gates** — User confirmation for dangerous operations
- **Audit Trail** — Complete logging of all actions
- **Doom Loop Detection** — Prevents infinite retry loops
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
