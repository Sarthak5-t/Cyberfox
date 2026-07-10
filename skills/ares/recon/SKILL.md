name: ares/recon
description: "Reconnaissance phase — map attack surface with nmap, DNS, subdomain enum, OSINT."
version: 2.0.0
author: Cyberfox Agent
platforms: [linux]
metadata:
  cyberfox:
    tags: [Ares, Recon, Pentest, Network-Scanning, OSINT]
    related_skills: [ares/lead, ares/scanning]
    category: ares

---

# Ares Recon Skill — Attack Surface Mapping

Map the target's attack surface through passive enumeration, active scanning, DNS discovery, and OSINT. This is always the first phase — you cannot scan or exploit what you haven't found.

## When to Use

- Initial engagement — no prior knowledge of the target
- Expanding a foothold — new IP ranges discovered during exploitation
- Continuous monitoring — periodic rescan of known scope

## Prerequisites

- Target IPs/ranges/domains in scope (scope.yaml)
- Outbound network access to targets
- Tools: nmap, subfinder, dnsrecon, masscan, amass, whois, theHarvester, whatweb

## Reconnaissance Decision Tree

```
TARGET INPUT
├── Domain name?
│   ├── WHOIS lookup → registrant info, name servers, related domains
│   ├── theHarvester → emails, subdomains, IPs
│   ├── Subdomain enum (subfinder + amass) → full subdomain list
│   ├── DNS recon (dnsrecon) → records, zone transfer, SRV
│   └── Resolve all to IPs → feed into port scanning
│
├── IP address / CIDR?
│   ├── Masscan → fast full-range port sweep (65535 ports)
│   ├── Nmap quick → service identification on live hosts
│   └── Nmap version → exact software + version on open ports
│
└── Both?
    └── Process domain → IPs first, then merge with IP list
```

## Step-by-Step Procedure

### 1. Passive Reconnaissance (No direct contact)

**WHOIS — Domain Intelligence**
```bash
whois_scan(target="example.com")
```
Returns: registrant, creation/expiry dates, name servers, related IPs, ASN info.
Use for: identifying infrastructure ownership, related domains, IP ranges.

**theHarvester — Email & Subdomain OSINT**
```bash
theharvester_scan(domain="example.com", limit=500)
```
Returns: email addresses, subdomains, IPs, hosts.
Use for: building target list, identifying naming patterns, email-based attacks.

**Certificate Transparency — Subdomain Discovery**
```bash
subdomain_enum(domain="example.com")
```
Returns: all subdomains found via CT logs and DNS brute-force.
Use for: expanding attack surface beyond known subdomains.

### 2. Active Reconnaissance — Port Discovery

**Masscan — Ultra-Fast Port Sweep**
```bash
masscan_scan(target="10.10.10.0/24", ports="1-65535", rate=10000)
```
Returns: list of live hosts and open ports.
Use for: initial sweep of large ranges. 10k packets/sec is fast but noisy.

**Nmap — Service Identification**
```bash
nmap_scan(target="10.10.10.1", scan_type="quick")
nmap_scan(target="10.10.10.1", scan_type="version")
```
Returns: open ports, services, versions, OS detection.
Use for: understanding what's running on each host.

**Scan Type Selection:**
| Situation | Scan Type | Why |
|---|---|---|
| First contact | `quick` (-T4 -F) | Fast, top 1000 ports |
| All ports | `full` (-T4 -p- -A) | Comprehensive, slower |
| Known ports | custom ports | Target specific services |
| Vulnerability check | `vuln` (--script vuln) | NSE vuln scripts |
| Stealth required | `stealth` (-T2 -sS -F) | SYN scan, slow, less detectable |
| UDP services | `udp` (-sU --top-ports 100) | DNS, SNMP, SIP |

### 3. DNS Reconnaissance

**dnsrecon — Full DNS Analysis**
```bash
dnsrecon_scan(target="example.com", type="std")
```
Returns: A, AAAA, MX, NS, TXT, SOA, SRV records. Zone transfer attempt.
Use for: mapping infrastructure, finding mail servers, discovering services.

**DNS Record Types to Collect:**
| Record | Attack Value |
|---|---|
| A/AAAA | IP addresses → port scan targets |
| MX | Mail servers → email attacks, credential harvesting |
| NS | Name servers → DNS poisoning, zone transfer |
| TXT | SPF, DKIM, DMARC → email spoofing opportunities |
| SRV | Service locations → Kerberos, LDAP, Exchange endpoints |
| SOA | Authority info → infrastructure mapping |

### 4. Web Reconnaissance

**whatweb — Technology Fingerprinting**
```bash
whatweb_scan(target="http://example.com", aggression=3)
```
Returns: CMS, frameworks, languages, server version, headers.
Use for: identifying tech stack for targeted vuln scanning.

**Technology Stack Analysis:**
| Detected | Next Step |
|---|---|
| WordPress | `wpscan_scan` for plugin/theme vulns |
| Joomla/Drupal | `nuclei_scan` with CMS-specific templates |
| Apache/IIS/Nginx | `nikto_scan` + version-specific exploits |
| Custom framework | `gobuster_scan` + `ffuf_scan` for hidden paths |
| API endpoints | `curl_tool` + manual analysis |

### 5. Documentation

After each recon step, save findings:
```bash
findings_save(
    title="Open port 445 on 10.10.10.1 — SMB",
    severity="info",
    category="recon",
    target="10.10.10.1",
    port=445,
    protocol="tcp",
    evidence="nmap output: Microsoft Windows 7 Professional 6.1.7601",
    tool="nmap_scan"
)
```

## OPSEC Considerations

| Technique | Noise Level | Detection Risk |
|---|---|---|
| WHOIS/DNS/subdomain enum | Very Low | Almost none |
| Masscan at 10k pps | High | IDS will alert |
| Nmap quick scan | Medium | Some IDS alert |
| Nmap version scan | Medium-High | Service logs, IDS |
| Nmap vuln scripts | High | WAF/IDS will flag |
| whatweb/aggressive | Medium | Web server logs |

**Rate limiting strategy:**
1. Start passive (WHOIS, DNS, CT logs) — zero detection risk
2. Masscan for port discovery — fast but use realistic rates (1000-5000)
3. Nmap for service detail — only on live hosts with open ports
4. Save the aggressive scans for Phase 2

## Pitfalls

- Do NOT scan all 65535 ports on a /16 with nmap — use masscan first, then nmap on discovered ports
- DNS tools only work when you have a domain — skip if pure IP range
- Subdomain enum can be slow on large domains — set reasonable limits
- Save findings incrementally — don't wait until end of recon
- Always verify host is live before deep scanning (ping, ARP, or quick nmap)

## Verification Checklist

- [ ] All live hosts in scope identified
- [ ] Open ports and services documented
- [ ] Software versions identified
- [ ] DNS records collected (if domain in scope)
- [ ] Subdomains enumerated (if domain in scope)
- [ ] Web technologies fingerprinted
- [ ] All findings saved to database
- [ ] Findings categorized for Phase 2 scanning
