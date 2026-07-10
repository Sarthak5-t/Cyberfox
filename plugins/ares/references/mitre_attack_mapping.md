# MITRE ATT&CK → Ares Tool Mapping

## Enterprise Attack Matrix

### TA0043: Reconnaissance
| Technique | Tool | Command |
|---|---|---|
| T1595: Active Scanning | nmap_scan, masscan_scan | Port sweep, service detection |
| T1592: Gather Victim Host Info | whois_scan, theharvester_scan | Domain/IP OSINT |
| T1589: Gather Victim Identity | theharvester_scan | Email/subdomain harvesting |
| T1588: Obtain Capabilities | searchsploit_tool | Exploit research |
| T1591: Gather Victim Org Info | whois_scan | Registration details |

### TA0042: Resource Development
| Technique | Tool | Command |
|---|---|---|
| T1583: Acquire Infrastructure | subdomain_enum, amass_scan | Subdomain discovery |
| T1587: Develop Capabilities | searchsploit_tool | Find public exploits |
| T1585: Establish Accounts | manual | Create test accounts |

### TA0001: Initial Access
| Technique | Tool | Command |
|---|---|---|
| T1190: Exploit Public App | nuclei_scan, msf_exec, sqlmap_scan | Web exploit |
| T1133: External Remote Services | hydra_brute | Brute-force login |
| T1078: Valid Accounts | hydra_brute, crackmapexec | Credential testing |
| T1566: Phishing | manual | Social engineering (out of scope) |

### TA0002: Execution
| Technique | Tool | Command |
|---|---|---|
| T1059: Command/Script Interpreter | msf_exec, impacket_exec | RCE via exploit |
| T1203: Exploitation for Client | msf_exec | Client-side exploit |
| T1047: WMI | impacket_exec(wmiexec) | Remote execution |

### TA0003: Persistence
| Technique | Tool | Command |
|---|---|---|
| T1078: Valid Accounts | hydra_brute, crackmapexec | Credential reuse |
| T1543: Create/Modify Process | impacket_exec(psexec) | Service creation |
| T1136: Create Account | manual | Backdoor account |

### TA0004: Privilege Escalation
| Technique | Tool | Command |
|---|---|---|
| T1068: Exploitation for PE | msf_exec | Local exploit |
| T1078: Valid Accounts | crackmapexec | Admin credential spray |
| T1548: Abuse Elevation | impacket_exec(secretsdump) | Credential extraction |

### TA0005: Defense Evasion
| Technique | Tool | Command |
|---|---|---|
| T1027: Obfuscated Files | manual | Payload encoding |
| T1055: Process Injection | msf_exec | Meterpreter migrate |
| T1070: Indicator Removal | manual | Log cleanup |

### TA0006: Credential Access
| Technique | Tool | Command |
|---|---|---|
| T1003: OS Credential Dumping | impacket_exec(secretsdump) | SAM/LSA dump |
| T1110: Brute Force | hydra_brute, crackmapexec | Credential attacks |
| T1558: Steal Kerberos Tickets | impacket(kerberoast) | Kerberoast |
| T1555: Credentials from Stores | impacket_exec | Password stores |

### TA0007: Discovery
| Technique | Tool | Command |
|---|---|---|
| T1046: Network Service Scan | nmap_scan, masscan_scan | Port scanning |
| T1087: Account Discovery | kerbrute_enum, crackmapexec | User enumeration |
| T1082: System Info Discovery | enum4linux_scan | System info |
| T1016: System Network Config | dnsrecon_scan | DNS/network config |

### TA0008: Lateral Movement
| Technique | Tool | Command |
|---|---|---|
| T1021: Remote Services | impacket_exec(psexec/wmiexec) | PtH/PtT movement |
| T1550: Use Alternate Auth | crackmapexec | Pass-the-Hash |
| T1570: Lateral Tool Transfer | smbclient_tool | File transfer |

### TA0009: Collection
| Technique | Tool | Command |
|---|---|---|
| T1005: Data from Local System | impacket_exec | File collection |
| T1039: Data from Network Share | smbclient_tool | Share access |
| T1213: Data from Info Repos | enum4linux_scan | Share enumeration |

### TA0010: Exfiltration
| Technique | Tool | Command |
|---|---|---|
| T1048: Exfil Over Alt Protocol | curl_tool | HTTP exfil |
| T1567: Exfil Over Web Service | manual | Web-based exfil |

### TA0011: Command and Control
| Technique | Tool | Command |
|---|---|---|
| T1071: Application Layer Protocol | curl_tool | HTTP C2 |
| T1572: Protocol Tunneling | impacket_exec | Encrypted channels |

### TA0040: Impact
| Technique | Tool | Command |
|---|---|---|
| T1486: Data Encrypted for Impact | manual | Ransomware (out of scope) |
| T1489: Service Stop | manual | Service disruption |
