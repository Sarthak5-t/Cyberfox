# Cyberfox 🔥

<p align="center">
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Tools-48+-red?style=for-the-badge" alt="Tools"></a>
  <a href="https://github.com/Sarthak5-t/Cyberfox"><img src="https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
</p>

<p align="center">
  <b>Elite cybersecurity operations agent</b> with 48+ security tools, 12 specialist roles, and full kill-chain methodology.
</p>

---

## Features

### Security Capabilities

| Category | Tools | Description |
|----------|-------|-------------|
| **Reconnaissance** | 8 tools | Nmap, DNSRecon, Subfinder, Masscan, Amass, Whois, TheHarvester, WhatWeb |
| **Scanning** | 17 tools | Nuclei, Gobuster, Feroxbuster, FFUF, Nikto, WPScan, Burp Suite, and more |
| **Exploitation** | 13 tools | SQLMap, Hydra, Metasploit, Responder, Impacket, custom exploit chains |
| **Active Directory** | 4 tools | BloodHound, Certipy, CrackMapExec, Kerbrute |
| **Utility** | 3 tools | Findings management, reporting, delegation |

### Specialist Roles

- **Pentester** — Reconnaissance and exploitation specialist
- **SOC Analyst** — Defensive security analyst
- **Cloud Security Specialist** — AWS, Azure, GCP security testing
- **Mobile Security Specialist** — Android/iOS application security
- **Wireless Security Specialist** — WiFi and Bluetooth security
- **Social Engineering Specialist** — Phishing and pretexting assessments
- **Malware Analyst** — Reverse engineering and threat intelligence
- **AD Specialist** — Active Directory attack specialist
- **Web Attacker** — Web application exploitation
- **OSINT Analyst** — Passive reconnaissance specialist
- **Privilege Escalation Specialist** — Local and domain privesc
- **Lead Orchestrator** — Engagement coordination

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
│       ├── tools/      # 48+ security tools
│       ├── agents/     # 12 specialist roles
│       ├── references/ # Security knowledge base
│       └── safety/     # Scope validation, audit trail
├── skills/
│   └── ares/           # Expert skills
│       ├── recon/      # Reconnaissance
│       ├── scanning/   # Vulnerability scanning
│       ├── exploit/    # Exploitation
│       ├── ad/         # Active Directory
│       └── ...         # More specialized skills
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
| `ares/report` | Report generation |
| `ares/cloud_pentest` | Cloud security testing |
| `ares/mobile_pentest` | Mobile app security |
| `ares/wireless_pentest` | Wireless security testing |
| `ares/social_engineering` | Social engineering assessments |
| `ares/physical_pentest` | Physical security testing |

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

## License

MIT License — see [LICENSE](LICENSE)

---

<p align="center">
  <b>Created by <a href="https://linkedin.com/in/khatalsarthak">Sarthak Khatal</a></b>
</p>
