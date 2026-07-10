# Common CVEs — High-Value Exploits by Service

## Apache / HTTP Server
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-41773 | Path traversal + RCE (2.4.49) | 9.8 | `msf: exploit/multi/http/apache_normalize_path_rce` |
| CVE-2021-42013 | Path traversal bypass (2.4.50) | 9.8 | `msf: exploit/multi/http/apache_normalize_path_rce` |
| CVE-2021-44790 | Buffer overflow mod_lua (2.4.51) | 9.8 | `searchsploit apache mod_lua` |
| CVE-2017-15715 | Upload bypass (2.4.25-2.4.27) | 7.5 | `searchsploit apache upload` |
| CVE-2019-0211 | Local privilege escalation (2.4.29) | 7.8 | `searchsploit apache privilege escalation` |

## Nginx
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-23017 | DNS resolver off-by-one | 7.7 | Manual exploitation |
| CVE-2019-9511 | HTTP/2 Data Dribble DoS | 7.5 | `searchsploit nginx http2` |
| CVE-2016-4450 | NULL pointer dereference | 7.5 | `searchsploit nginx null pointer` |

## Microsoft IIS
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-31166 | HTTP protocol stack RCE (Win10/2019) | 9.8 | `msf: exploit/windows/http/cve_2021_31166_heap` |
| CVE-2017-7269 | WebDAV buffer overflow (6.0) | 9.8 | `msf: exploit/windows/iis/iis_webdav_scstoragepathfromurl` |
| CVE-2015-1635 | HTTP.sys RCE (IIS 7.5-8.5) | 10.0 | `msf: exploit/windows/http/ms15_034_sys内存_dump` |

## Apache Struts
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2017-5638 | Jakarta Multipart RCE | 10.0 | `msf: exploit/multi/http/struts2_content_type_ognl` |
| CVE-2018-11776 | OGNL injection RCE | 8.1 | `msf: exploit/multi/http/struts2_namespace_ognl` |
| CVE-2019-0230 | OGNL injection via tag attrs | 9.8 | `searchsploit apache struts` |

## Log4j
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-44228 | Log4Shell RCE (JNDI injection) | 10.0 | `nuclei -t cves/2021/CVE-2021-44228.yaml` |
| CVE-2021-45046 | Log4Shell bypass | 9.0 | Same as above |
| CVE-2021-45105 | DoS via recursive lookup | 7.5 | `nuclei -t cves/2021/CVE-2021-45105.yaml` |

## OpenSSL
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2014-0160 | Heartbleed (1.0.1-1.0.1f) | 7.5 | `msf: auxiliary/scanner/ssl/openssl_heartbleed` |
| CVE-2016-0800 | DROWN (SSLv2) | 4.3 | `searchsploit openssl drown` |
| CVE-2016-2183 | SWEET32 (64-bit block) | 5.3 | `nmap --script ssl-enum-ciphers` |

## OpenSSH
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2023-38408 | PKCS#11 forwarding RCE (8.7p1) | 9.8 | `searchsploit openssh pkcs11` |
| CVE-2016-0777 | Info leak via roaming | 5.0 | `searchsploit openssh` |
| Default creds | Common vendor defaults | Varies | `hydra_brute` with default lists |

## Samba
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2017-7494 | Remote code execution (3.5.0+) | 9.8 | `msf: exploit/linux/samba/is_known_pipename` |
| CVE-2015-0240 | Netlogon memory corruption | 6.8 | `searchsploit samba netlogon` |
| CVE-2016-2118 | BADLOCK (man-in-the-middle) | 4.3 | `searchsploit samba badlock` |

## SMB / Windows
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2017-0143 | EternalBlue (MS17-010) | 9.3 | `msf: exploit/windows/smb/ms17_010_eternalblue` |
| CVE-2017-0144 | EternalRomance | 9.3 | `msf: exploit/windows/smb/ms17_010_psexec` |
| CVE-2017-0145 | EternalSynergy | 9.3 | `msf: exploit/windows/smb/ms17_010_psexec` |
| CVE-2019-0708 | BlueKeep (RDP) | 9.8 | `msf: exploit/windows/rdp/cve_2019_0708_bluekeep_rce` |
| CVE-2021-34527 | PrintNightmare (Spooler) | 8.8 | `msf: exploit/windows/dcerpc/cve_2021_34527_printnightmare` |

## WordPress
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2019-9978 | Social Warfare plugin stored XSS | 6.1 | `wpscan --enumerate vp` |
| CVE-2019-16219 | Core editor block injection | 6.4 | `wpscan --enumerate vp,vt` |
| Various | Plugin/theme vulns | Varies | `wpscan_scan` full enumeration |

## SQL Databases
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| SQLi (various) | Injection via parameters | Varies | `sqlmap_scan` |
| CVE-2012-2122 | MySQL auth bypass | 10.0 | `searchsploit mysql auth bypass` |
| CVE-2017-3506 | WebLogic deserialization | 7.4 | `searchsploit weblogic deserialization` |

## Exchange
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-26855 | ProxyLogon SSRF → RCE | 9.8 | `msf: exploit/windows/http/exchange_proxylogon_rce` |
| CVE-2021-34473 | ProxyShell (pre-auth RCE) | 9.8 | `searchsploit exchange proxyshell` |
| CVE-2021-31207 | ProxyShell post-auth RCE | 6.6 | `searchsploit exchange proxyshell` |
| CVE-2022-41040 | ProxyNotShell SSRF | 8.8 | `searchsploit exchange proxynotshell` |

## Fortinet
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2018-13379 | Path traversal (FortiOS) | 9.8 | `nuclei -t cves/2018/CVE-2018-13379.yaml` |
| CVE-2022-40684 | Auth bypass (FortiOS 7.x) | 9.8 | `searchsploit fortios auth bypass` |

## SonicWall
| CVE | Description | CVSS | Exploit |
|---|---|---|---|
| CVE-2021-20038 | Stack buffer overflow (SMA 100) | 9.8 | `searchsploit sonicwall stack overflow` |
| CVE-2021-20045 | Command injection | 7.2 | `searchsploit sonicwall command injection` |
