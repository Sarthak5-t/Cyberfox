name: ares/scanning
description: "Vulnerability scanning — nuclei, web fuzzing, service enumeration, WAF detection."
version: 2.0.0
author: Cyberfox Agent
platforms: [linux]
metadata:
  cyberfox:
    tags: [Ares, Scanning, Vulnerability, Pentest]
    related_skills: [ares/lead, ares/recon, ares/exploit]
    category: ares

---

# Ares Scanning Skill — Vulnerability Discovery

Probe discovered services for vulnerabilities using automated scanners, web fuzzers, WAF detection, and service-specific enumeration. This phase consumes the output of reconnaissance to find exploitable weaknesses.

## When to Use

- After recon phase is complete (open ports + services identified)
- Web services are present (HTTP/HTTPS on discovered hosts)
- SMB/NetBIOS services are present (Windows targets)
- Need to prioritize which vulnerabilities to exploit

## Prerequisites

- Recon phase complete — live hosts with identified services
- Tools: nuclei, gobuster, feroxbuster, ffuf, wfuzz, nikto, wpscan, enum4linux, wafw00f, smbclient, snmpwalk

## Scanning Decision Tree

```
RECON RESULTS
├── HTTP/HTTPS service?
│   ├── WAF detection (wafw00f) → plan evasion
│   ├── Nuclei scan (critical,high) → known CVEs
│   ├── Technology fingerprint → CMS check (wpscan if WordPress)
│   ├── Directory busting (gobuster/feroxbuster) → hidden paths
│   ├── Parameter fuzzing (ffuf/wfuzz) → injectable params
│   └── Nikto scan → server misconfigs
│
├── SMB/NetBIOS (445/139)?
│   ├── enum4linux → shares, users, policies
│   ├── smbclient → share access, file listing
│   └── crackmapexec(smb) → signing status, domain info
│
├── SNMP (161/162)?
│   ├── snmpwalk → MIB walk, community string validation
│   └── onesixtyone → community string brute-force
│
├── DNS (53)?
│   └── zone transfer attempt → full DNS dump
│
└── Other services?
    └── Nmap NSE scripts → service-specific vuln checks
```

## Step-by-Step Procedure

### 1. WAF Detection (Before Aggressive Scanning)

```bash
wafw00f_scan(target="http://example.com")
```

If WAF detected:
- Use evasion flags on all subsequent scans
- Reduce scan speed and intensity
- Consider fragmentation (`nmap -f`), decoys (`nmap -D`), source port manipulation
- For web scanning: use `curl_tool` for manual probing instead of automated scanners

**WAF Bypass Strategies:**
| WAF | Technique |
|---|---|
| Cloudflare | IP direct access, origin leak via Censys/Shodan |
| AWS WAF | HTTP/2 smuggling, chunked encoding |
| ModSecurity | Unicode normalization, null bytes, case variation |
| Imperva | Fragmented requests, slow POST |
| Generic | Slowloris, HTTP parameter pollution, encoding tricks |

### 2. Nuclei — Known CVE Scanning

```bash
# Critical and high first
nuclei_scan(target="http://example.com", severity="critical,high")

# If nothing critical, expand to medium
nuclei_scan(target="http://example.com", severity="medium")

# Specific template categories
nuclei_scan(target="http://example.com", templates="cves", severity="critical,high")
nuclei_scan(target="http://example.com", templates="misconfigurations")
nuclei_scan(target="http://example.com", templates="exposures")
```

**Nuclei Strategy:**
1. Start with `critical,high` — focus on exploitable vulns
2. If nothing found, expand to `medium` — misconfigurations and info leaks
3. Use template categories to target specific vuln types
4. Check for nuclei template updates regularly: `nuclei -update-templates`

### 3. Web Directory & File Discovery

**Gobuster — Fast Directory Brute-Force**
```bash
# Standard directory scan
gobuster_scan(target="http://example.com", mode="dir", wordlist="common", threads=50)

# With file extensions
gobuster_scan(target="http://example.com", mode="dir", wordlist="common", extensions="php,html,js,txt")

# Subdomain brute-force
gobuster_scan(target="example.com", mode="dns", wordlist="subdomains")

# VHost discovery
gobuster_scan(target="http://example.com", mode="vhost", wordlist="subdomains")
```

**Feroxbuster — Recursive, Filter-Aware**
```bash
feroxbuster_scan(target="http://example.com", wordlist="common", threads=50, extensions="php,html,js")
```
Feroxbuster auto-handles filtering, recursion, and size-based exclusion.

**FFUF — High-Speed Fuzzing**
```bash
# Directory fuzzing
ffuf_scan(target="http://example.com/FUZZ", wordlist="common", threads=50)

# Parameter fuzzing
ffuf_scan(target="http://example.com/api?FUZZ=test", wordlist="params")

# POST data fuzzing
ffuf_scan(target="http://example.com/login", wordlist="users", flags="-X POST -d 'user=FUZZ&pass=admin'")

# Header fuzzing
ffuf_scan(target="http://example.com", wordlist="headers", flags="-H 'FUZZ: true'")
```

**Wfuzz — Payload-Based Fuzzing**
```bash
wfuzz_scan(target="http://example.com/FUZZ", wordlist="common", threads=30)
```

### 4. Web Vulnerability Scanning

**Nikto — Server Misconfiguration**
```bash
nikto_scan(target="http://example.com")
nikto_scan(target="http://example.com", port="8443", ssl="true")
```
Checks: outdated software, dangerous files/CGIs, server misconfigurations, missing security headers.

**WPScan — WordPress**
```bash
wpscan_scan(target="http://example.com", enumerate="vp,vt,u")
```
Enumerates: plugins, themes, users, versions. Cross-refs with vuln databases.

### 5. Service-Specific Enumeration

**SMB — enum4linux**
```bash
enum4linux_scan(target="10.10.10.1")
```
Returns: shares, users, groups, policies, OS info, password policy.

**SMB — smbclient**
```bash
smbclient_tool(target="10.10.10.1", share="IPC$", action="list")
```

**SNMP — snmpwalk**
```bash
snmpwalk_tool(target="10.10.10.1", community="public")
```
Walks MIB tree for system info, network config, running processes, user accounts.

**SNMP — Community String Brute-Force**
```bash
# Use onesixtyone for fast community string testing
onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt 10.10.10.1
```

### 6. Exploit Research

```bash
searchsploit_tool(query="Apache 2.4.49")
searchsploit_tool(query="WordPress 5.8")
searchsploit_tool(query="Samba 4.15")
```
For each discovered service version, find matching public exploits.

### 7. Prioritization

After scanning, categorize findings:

| Priority | Criteria | Example |
|---|---|---|
| P1 — Critical | Unauth RCE, domain admin | Log4Shell, EternalBlue |
| P2 — High | Auth bypass, SQLi, file read | SQL injection, path traversal |
| P3 — Medium | Info disclosure, weak config | Directory listing, verbose errors |
| P4 — Low | Version disclosure, default banners | Server header leak |

## OPSEC Considerations

| Scanner | Noise Level | WAF Alert Risk |
|---|---|---|
| Nuclei | Medium-High | High — signature-based |
| Gobuster | Medium | Medium — high request rate |
| Nikto | Medium | Medium — known signatures |
| FFUF | High (if aggressive) | High — fuzzing patterns |
| WPScan | Medium | Medium — fingerprinting |

**Rate limiting strategy:**
- Start with nuclei (high signal, low noise if targeted)
- Use gobuster with moderate threads (25-50)
- Save aggressive fuzzing for after WAF assessment
- If WAF triggers, slow down or switch to manual

## Pitfalls

- Nuclei can be noisy and trigger WAFs — start with targeted templates
- Wordlist selection matters: `common` is fast, `big` is thorough — start with common
- enum4linux only works on Windows/Samba — skip if no SMB
- Web fuzzing can take time — use background tasks for large scans
- Do NOT run nuclei on out-of-scope targets
- Some servers drop connections on high thread counts — reduce threads if errors occur

## Verification Checklist

- [ ] All web services scanned with nuclei (critical + high at minimum)
- [ ] Directory enumeration completed for all HTTP services
- [ ] Parameter fuzzing completed for discovered endpoints
- [ ] SMB enumeration completed (if port 445 open)
- [ ] SNMP enumeration completed (if port 161 open)
- [ ] Exploit research completed for all discovered versions
- [ ] All findings saved with severity and evidence
- [ ] Prioritized list of exploitable findings ready for Phase 3
