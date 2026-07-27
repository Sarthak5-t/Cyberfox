---
name: scanning-tools
description: "Master essential security scanning tools for network discovery, vulnerability assessment, web application testing, wireless security, and compliance validation. Covers tool selection, configuration, and practical usage across different scanning categories."
version: 1.0.0
author: Cyberfox Agent
license: MIT
metadata:
  cyberfox:
    tags: [red-teaming, scanning, nmap, nikto, nessus, openvas, burp, zap, aircrack, lynis, openscap]
    related_skills: [red-teaming/ethical-hacking-methodology, red-teaming/red-team-tools, ares/recon, ares/scanning]
    category: red-teaming
---

# Security Scanning Tools

## Purpose

Master essential security scanning tools for network discovery, vulnerability assessment, web application testing, wireless security, and compliance validation. This skill covers tool selection, configuration, and practical usage across different scanning categories.

## Prerequisites

### Required Environment
- Linux-based system (Kali Linux recommended)
- Network access to target systems
- Proper authorization for scanning activities

### Required Knowledge
- Basic networking concepts (TCP/IP, ports, protocols)
- Understanding of common vulnerabilities
- Familiarity with command-line interfaces

## Outputs and Deliverables

1. **Network Discovery Reports** - Identified hosts, ports, and services
2. **Vulnerability Assessment Reports** - CVEs, misconfigurations, risk ratings
3. **Web Application Security Reports** - OWASP Top 10 findings
4. **Compliance Reports** - CIS benchmarks, PCI-DSS, HIPAA checks

## Core Workflow

### Phase 1: Network Scanning Tools

#### Nmap (Network Mapper)

Primary tool for network discovery and security auditing:

```bash
# Host discovery
nmap -sn 192.168.1.0/24              # Ping scan (no port scan)
nmap -sL 192.168.1.0/24              # List scan (DNS resolution)
nmap -Pn 192.168.1.100               # Skip host discovery

# Port scanning techniques
nmap -sS 192.168.1.100               # TCP SYN scan (stealth)
nmap -sT 192.168.1.100               # TCP connect scan
nmap -sU 192.168.1.100               # UDP scan
nmap -sA 192.168.1.100               # ACK scan (firewall detection)

# Port specification
nmap -p 80,443 192.168.1.100         # Specific ports
nmap -p- 192.168.1.100               # All 65535 ports
nmap -p 1-1000 192.168.1.100         # Port range
nmap --top-ports 100 192.168.1.100   # Top 100 common ports

# Service and OS detection
nmap -sV 192.168.1.100               # Service version detection
nmap -O 192.168.1.100                # OS detection
nmap -A 192.168.1.100                # Aggressive (OS, version, scripts)

# Timing and performance
nmap -T0 192.168.1.100               # Paranoid (slowest, IDS evasion)
nmap -T4 192.168.1.100               # Aggressive (faster)
nmap -T5 192.168.1.100               # Insane (fastest)

# NSE Scripts
nmap --script=vuln 192.168.1.100     # Vulnerability scripts
nmap --script=http-enum 192.168.1.100  # Web enumeration
nmap --script=smb-vuln* 192.168.1.100  # SMB vulnerabilities
nmap --script=default 192.168.1.100  # Default script set

# Output formats
nmap -oN scan.txt 192.168.1.100      # Normal output
nmap -oX scan.xml 192.168.1.100      # XML output
nmap -oG scan.gnmap 192.168.1.100    # Grepable output
nmap -oA scan 192.168.1.100          # All formats
```

#### Masscan

High-speed port scanning for large networks:

```bash
# Basic scanning
masscan -p80 192.168.1.0/24 --rate=1000
masscan -p80,443,8080 192.168.1.0/24 --rate=10000

# Full port range
masscan -p0-65535 192.168.1.0/24 --rate=5000

# Large-scale scanning
masscan 0.0.0.0/0 -p443 --rate=100000 --excludefile exclude.txt

# Output formats
masscan -p80 192.168.1.0/24 -oG results.gnmap
masscan -p80 192.168.1.0/24 -oJ results.json
masscan -p80 192.168.1.0/24 -oX results.xml

# Banner grabbing
masscan -p80 192.168.1.0/24 --banners
```

---

### Phase 2: Vulnerability Scanning Tools

#### Nessus

Enterprise-grade vulnerability assessment:

```bash
# Start Nessus service
sudo systemctl start nessusd

# Access web interface
# https://localhost:8834

# Command-line (nessuscli)
nessuscli scan --create --name "Internal Scan" --targets 192.168.1.0/24
nessuscli scan --list
nessuscli scan --launch <scan_id>
nessuscli report --format pdf --output report.pdf <scan_id>
```

**Key Nessus features:**
- Comprehensive CVE detection
- Compliance checks (PCI-DSS, HIPAA, CIS)
- Custom scan templates
- Credentialed scanning for deeper analysis
- Regular plugin updates

#### OpenVAS (Greenbone)

Open-source vulnerability scanning:

```bash
# Install OpenVAS
sudo apt install openvas
sudo gvm-setup

# Start services
sudo gvm-start

# Access web interface (Greenbone Security Assistant)
# https://localhost:9392

# Command-line operations
gvm-cli socket --xml "<get_version/>"
gvm-cli socket --xml "<get_tasks/>"

# Create and run scan
gvm-cli socket --xml '
<create_target>
  <name>Test Target</name>
  <hosts>192.168.1.0/24</hosts>
</create_target>'

gvm-cli socket --xml '
<create_task>
  <name>Test Scan</name>
  <config id="daba56c8-73ec-11df-a475-002264764cea"/>
  <target id="TARGET_ID"/>
</create_task>'
```

---

### Phase 3: Web Application Scanning Tools

#### Burp Suite

Comprehensive web application testing:

```bash
# Proxy configuration
1. Set browser proxy to 127.0.0.1:8080
2. Import Burp CA certificate for HTTPS
3. Add target to scope

# Key modules:
# - Proxy: Intercept and modify requests
# - Spider: Crawl web applications
# - Scanner: Automated vulnerability detection
# - Intruder: Automated attacks (fuzzing, brute-force)
# - Repeater: Manual request manipulation
# - Decoder: Encode/decode data
# - Comparer: Compare responses
```

**Core testing workflow:**
1. Configure proxy and scope
2. Spider the application
3. Analyze sitemap
4. Run active scanner
5. Manual testing with Repeater/Intruder
6. Review findings and generate report

#### OWASP ZAP

Open-source web application scanner:

```bash
# Start ZAP
zaproxy

# Automated scan from CLI
zap-cli quick-scan https://target.com

# Full scan
zap-cli spider https://target.com
zap-cli active-scan https://target.com

# Generate report
zap-cli report -o report.html -f html

# API mode
zap.sh -daemon -port 8080 -config api.key=<your_key>

# Docker-based scanning
docker run -t owasp/zap2docker-stable zap-full-scan.py \
  -t https://target.com -r report.html

# Baseline scan (passive only)
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://target.com -r report.html
```

#### Nikto

Web server vulnerability scanner:

```bash
# Basic scan
nikto -h https://target.com

# Scan specific port
nikto -h target.com -p 8080

# Scan with SSL
nikto -h target.com -ssl

# Multiple targets
nikto -h targets.txt

# Output formats
nikto -h target.com -o report.html -Format html
nikto -h target.com -o report.xml -Format xml
nikto -h target.com -o report.csv -Format csv

# Tuning options
nikto -h target.com -Tuning 123456789  # All tests
nikto -h target.com -Tuning x          # Exclude specific tests
```

---

### Phase 4: Wireless Scanning Tools

#### Aircrack-ng Suite

Wireless network penetration testing:

```bash
# Check wireless interface
airmon-ng

# Enable monitor mode
sudo airmon-ng start wlan0

# Scan for networks
sudo airodump-ng wlan0mon

# Capture specific network
sudo airodump-ng -c <channel> --bssid <target_bssid> -w capture wlan0mon

# Deauthentication attack
sudo aireplay-ng -0 10 -a <bssid> wlan0mon

# Crack WPA handshake
aircrack-ng -w wordlist.txt -b <bssid> capture*.cap

# Crack WEP
aircrack-ng -b <bssid> capture*.cap
```

#### Kismet

Passive wireless detection:

```bash
# Start Kismet
kismet

# Specify interface
kismet -c wlan0

# Access web interface
# http://localhost:2501

# Detect hidden networks
# Kismet passively collects all beacon frames
# including those from hidden SSIDs
```

---

### Phase 5: Malware and Exploit Scanning

#### ClamAV

Open-source antivirus scanning:

```bash
# Update virus definitions
sudo freshclam

# Scan directory
clamscan -r /path/to/scan

# Scan with verbose output
clamscan -r -v /path/to/scan

# Move infected files
clamscan -r --move=/quarantine /path/to/scan

# Remove infected files
clamscan -r --remove /path/to/scan

# Scan specific file types
clamscan -r --include='\.exe$|\.dll$' /path/to/scan

# Output to log
clamscan -r -l scan.log /path/to/scan
```

#### Metasploit Vulnerability Validation

Validate vulnerabilities with exploitation:

```bash
# Start Metasploit
msfconsole

# Database setup
msfdb init
db_status

# Import Nmap results
db_import /path/to/nmap_scan.xml

# Vulnerability scanning
use auxiliary/scanner/smb/smb_ms17_010
set RHOSTS 192.168.1.0/24
run

# Auto exploitation
vulns                           # View vulnerabilities
analyze                         # Suggest exploits
```

---

### Phase 6: Cloud Security Scanning

#### Prowler (AWS)

AWS security assessment:

```bash
# Install Prowler
pip install prowler

# Basic scan
prowler aws

# Specific checks
prowler aws -c iam s3 ec2

# Compliance framework
prowler aws --compliance cis_aws

# Output formats
prowler aws -M html json csv

# Specific region
prowler aws -f us-east-1

# Assume role
prowler aws -R arn:aws:iam::123456789012:role/ProwlerRole
```

#### ScoutSuite (Multi-cloud)

Multi-cloud security auditing:

```bash
# Install ScoutSuite
pip install scoutsuite

# AWS scan
scout aws

# Azure scan
scout azure --cli

# GCP scan
scout gcp --user-account

# Generate report
scout aws --report-dir ./reports
```

---

### Phase 7: Compliance Scanning

#### Lynis

Security auditing for Unix/Linux:

```bash
# Run audit
sudo lynis audit system

# Quick scan
sudo lynis audit system --quick

# Specific profile
sudo lynis audit system --profile server

# Output report
sudo lynis audit system --report-file /tmp/lynis-report.dat

# Check specific section
sudo lynis show profiles
sudo lynis audit system --tests-from-group malware
```

#### OpenSCAP

Security compliance scanning:

```bash
# List available profiles
oscap info /usr/share/xml/scap/ssg/content/ssg-<distro>-ds.xml

# Run scan with profile
oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_pci-dss \
  --report report.html \
  /usr/share/xml/scap/ssg/content/ssg-rhel8-ds.xml

# Generate fix script
oscap xccdf generate fix \
  --profile xccdf_org.ssgproject.content_profile_pci-dss \
  --output remediation.sh \
  /usr/share/xml/scap/ssg/content/ssg-rhel8-ds.xml
```

---

### Phase 8: Scanning Methodology

Structured scanning approach:

1. **Planning**
   - Define scope and objectives
   - Obtain proper authorization
   - Select appropriate tools

2. **Discovery**
   - Host discovery (Nmap ping sweep)
   - Port scanning
   - Service enumeration

3. **Vulnerability Assessment**
   - Automated scanning (Nessus/OpenVAS)
   - Web application scanning (Burp/ZAP)
   - Manual verification

4. **Analysis**
   - Correlate findings
   - Eliminate false positives
   - Prioritize by severity

5. **Reporting**
   - Document findings
   - Provide remediation guidance
   - Executive summary

---

### Phase 9: Tool Selection Guide

Choose the right tool for each scenario:

| Scenario | Recommended Tools |
|----------|-------------------|
| Network Discovery | Nmap, Masscan |
| Vulnerability Assessment | Nessus, OpenVAS |
| Web App Testing | Burp Suite, ZAP, Nikto |
| Wireless Security | Aircrack-ng, Kismet |
| Malware Detection | ClamAV, YARA |
| Cloud Security | Prowler, ScoutSuite |
| Compliance | Lynis, OpenSCAP |
| Protocol Analysis | Wireshark, tcpdump |

---

### Phase 10: Reporting and Documentation

Generate professional reports:

```bash
# Nmap XML to HTML
xsltproc nmap-output.xml -o report.html

# OpenVAS report export
# Use Greenbone Security Assistant web interface

# Professional reporting templates should include:
# - Executive summary
# - Technical findings with evidence
# - Risk ratings and prioritization
# - Remediation recommendations
# - Retesting guidance
```

---

## OPSEC Considerations

| Scanner | Noise Level | WAF Alert Risk |
|---------|-------------|----------------|
| Nuclei | Medium-High | High - signature-based |
| Gobuster | Medium | Medium - high request rate |
| Nikto | Medium | Medium - known signatures |
| FFUF | High (if aggressive) | High - fuzzing patterns |
| WPScan | Medium | Medium - fingerprinting |

**Rate limiting strategy:**
- Start with nuclei (high signal, low noise if targeted)
- Use gobuster with moderate threads (25-50)
- Save aggressive fuzzing for after WAF assessment
- If WAF triggers, slow down or switch to manual

---

## Pitfalls

- Nuclei can be noisy and trigger WAFs — start with targeted templates
- Wordlist selection matters: `common` is fast, `big` is thorough — start with common
- enum4linux only works on Windows/Samba — skip if no SMB
- Web fuzzing can take time — use background tasks for large scans
- Do NOT run nuclei on out-of-scope targets
- Some servers drop connections on high thread counts — reduce threads if errors occur
- **ALWAYS log discoveries to the journal** (`journal_write`) — services, versions, CVEs, findings. This is your persistent memory.

---

## Verification Checklist

- [ ] All web services scanned with nuclei (critical + high at minimum)
- [ ] Directory enumeration completed for all HTTP services
- [ ] Parameter fuzzing completed for discovered endpoints
- [ ] SMB enumeration completed (if port 445 open)
- [ ] SNMP enumeration completed (if port 161 open)
- [ ] Exploit research completed for all discovered versions
- [ ] All findings saved with severity and evidence
- [ ] Prioritized list of exploitable findings ready for Phase 3

## When to Use

This skill is applicable to execute the workflow or actions described in the overview.