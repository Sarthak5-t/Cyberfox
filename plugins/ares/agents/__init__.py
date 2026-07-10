from __future__ import annotations

AGENT_DEFINITIONS = {
    "pentester": {
        "name": "Pentester",
        "description": "Reconnaissance and exploitation specialist. Runs scans, probes services, and attempts controlled exploitation.",
        "allowed_toolsets": ["ares_recon", "ares_scanning", "ares_exploit"],
        "allowed_targets": None,
    },
    "soc_analyst": {
        "name": "SOC Analyst",
        "description": "Defensive security analyst. Reviews logs, analyzes findings, assesses risk, and produces reports.",
        "allowed_toolsets": ["ares_utility"],
        "allowed_targets": None,
    },
    "lead_orchestrator": {
        "name": "Lead Orchestrator",
        "description": "Coordinates the engagement. Assigns tasks to specialists, tracks progress, and consolidates results.",
        "allowed_toolsets": ["ares_utility", "ares_recon"],
        "allowed_targets": None,
    },
    "osint_analyst": {
        "name": "OSINT Analyst",
        "description": "Passive reconnaissance specialist. Performs domain intelligence, subdomain enumeration, email harvesting, and technology fingerprinting without direct target contact.",
        "allowed_toolsets": ["ares_recon"],
        "allowed_targets": None,
    },
    "web_attacker": {
        "name": "Web Attacker",
        "description": "Web application exploitation specialist. Tests for OWASP Top 10 vulnerabilities, performs fuzzing, and attempts web-based exploitation.",
        "allowed_toolsets": ["ares_scanning", "ares_exploit"],
        "allowed_targets": None,
    },
    "ad_specialist": {
        "name": "AD Specialist",
        "description": "Active Directory attack specialist. Performs Kerberoasting, certificate abuse, lateral movement, and domain escalation.",
        "allowed_toolsets": ["ares_scanning", "ares_ad", "ares_exploit"],
        "allowed_targets": None,
    },
    "privesc_specialist": {
        "name": "Privilege Escalation Specialist",
        "description": "Privilege escalation specialist. Identifies and exploits local and domain privilege escalation paths.",
        "allowed_toolsets": ["ares_exploit", "ares_ad"],
        "allowed_targets": None,
    },
    "cloud_specialist": {
        "name": "Cloud Security Specialist",
        "description": "Cloud infrastructure security specialist. Identifies and exploits cloud misconfigurations, container vulnerabilities, and IAM weaknesses.",
        "allowed_toolsets": ["ares_recon", "ares_scanning", "ares_exploit"],
        "allowed_targets": None,
    },
    "mobile_specialist": {
        "name": "Mobile Security Specialist",
        "description": "Mobile application security specialist. Analyzes and tests mobile applications for vulnerabilities and insecure practices.",
        "allowed_toolsets": ["ares_scanning", "ares_exploit"],
        "allowed_targets": None,
    },
    "wireless_specialist": {
        "name": "Wireless Security Specialist",
        "description": "Wireless network security specialist. Tests wireless encryption, performs rogue AP detection, and exploits wireless protocols.",
        "allowed_toolsets": ["ares_recon", "ares_scanning"],
        "allowed_targets": None,
    },
    "social_engineer": {
        "name": "Social Engineering Specialist",
        "description": "Social engineering assessment specialist. Designs and executes phishing campaigns, pretexting scenarios, and physical security tests.",
        "allowed_toolsets": ["ares_recon", "ares_utility"],
        "allowed_targets": None,
    },
    "malware_analyst": {
        "name": "Malware Analyst",
        "description": "Malware reverse engineering specialist. Analyzes malware samples, extracts IOCs, and provides threat intelligence.",
        "allowed_toolsets": ["ares_recon", "ares_scanning", "ares_utility"],
        "allowed_targets": None,
    },
}
