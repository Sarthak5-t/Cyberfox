# Active Directory Attack Tree — Full Decision Tree

## Phase 0: Discovery

```
SMB OPEN (445)?
├── crackmapexec(smb, target=DC) → domain name, signing, OS
├── enum4linux(target) → users, groups, shares, policies
├── smbclient(IPC$) → null session check
└── rpcclient -N target → RPC enumeration
```

## Phase 1: Enumeration

```
HAVE DOMAIN INFO?
├── YES → kerbrute(userenum) with userlist
│         crackmapexec(smb) for user enum via RID brute
│         ldapsearch for user attributes
│
└── NO → enum4linux(target) for user list
          rpcclient "enumdomusers"
          snmpwalk for user accounts
```

## Phase 2: Credential Harvesting

```
ENUMERATED USERS?
├── Kerberoastable accounts? (service accounts with SPNs)
│   └── impacket(kerberoast) → offline crack (hashcat -m 13100)
│
├── AS-REP roastable? (pre-auth disabled)
│   └── impacket(getTGT) → offline crack (hashcat -m 18200)
│
├── LLMNR/NBT-NS enabled?
│   └── responder_listener → capture NetNTLM hashes
│       ├── crack with hashcat -m 5600
│       └── relay with impacket(smbrelay) if SMB signing disabled
│
├── GPP passwords?
│   └── powershell: Get-GPPPassword
│       crack hashcat -m 8300
│
├── Default service creds?
│   └── crackmapexec(smb) with default pass list
│
└── Password spray?
    └── crackmapexec(passwordspray) with seasonal/company defaults
```

## Phase 3: Privilege Escalation

```
HAVE LOW-PRIv CREDENTIALS?
├── Bloodhound ingested?
│   ├── Shortest path to DA?
│   │   ├── ACL abuse → AddKeyCredentialLink
│   │   ├── Group membership escalation
│   │   └── Controlled group → DA
│   │
│   ├── Kerberoastable DA account?
│   │   └── kerberoast → crack → DA
│   │
│   └── Delegation configured?
│       ├── Unconstrained delegation → extract TGTs
│       ├── Constrained delegation → S4U abuse
│       └── RBCD → resource-based constrained delegation → DA
│
├── Certificate templates? (ADCS)
│   ├── ESC1 → impersonate any user via SAN
│   ├── ESC2 → Any Purpose EKU abuse
│   ├── ESC4 → template modification → ESC1
│   ├── ESC7 → CA management abuse
│   ├── ESC8 → HTTP enrollment relay
│   └── certipy(find) → certipy(req) → DA
│
├── GPO abuse?
│   ├── Edit GPO → scheduled task → DA
│   └── SharpGPOAbuse
│
├── OU-based attacks?
│   └── Modify OU permissions → write-DACL
│
└── ACL abuse?
    ├── GenericAll → AddMember → DA group
    ├── WriteDACL → GPO abuse
    ├── WriteOwner → own account → DA
    └── AddKeyCredentialLink → shadow credentials → DA
```

## Phase 4: Domain Compromise

```
HAVE DOMAIN ADMIN?
├── DCSync all hashes
│   └── impacket(secretsdump) → full domain dump
│       ├── krbtgt hash → golden ticket
│       ├── Service account hashes → silver ticket
│       └── Admin hashes → persistent access
│
├── Golden Ticket
│   └── impacket(ticketer) with krbtgt hash
│       └── Persistent Domain Admin access
│
├── DCShadow
│   └── Register rogue DC → modify domain attributes
│
├── Skeleton Key
│   └── Mimikatz → inject skeleton key into LSASS
│
└── Full domain dump
    └── secretsdump on DC → all hashes, keys, credentials
```

## Quick Decision Matrix

| Situation | First Action | Escalation |
|---|---|---|
| SMB open, no creds | enum4linux → user list | kerberoast / spray |
| One user hash | crackmapexec → find local admins | lateral movement |
| Service account creds | kerberoast → crack | AD CS / delegation |
| Null session | rpcclient enum | LDAP anonymous bind |
| LLMNR enabled | responder → hash capture | relay or crack |
| AD CS present | certipy(find) | ESC1-8 abuse |
| Bloodhound shows path | follow shortest path | ACL/group abuse |
| Domain Admin hash | DCSync → full dump | golden ticket |

## Common AD Misconfigurations

| Misconfiguration | Exploit | Impact |
|---|---|---|
| Kerberoasting weak SPN passwords | Hashcat offline | Domain compromise |
| AS-REP roastable accounts | Hashcat offline | Account compromise |
| Unconstrained delegation | TGT extraction | Domain compromise |
| Weak certificate templates | certipy abuse | Domain compromise |
| LLMNR/NBT-NS enabled | Responder poisoning | Hash capture |
| SMB signing disabled | NTLM relay | Privilege escalation |
| GPP passwords | Credential extraction | Privilege escalation |
| WriteDACL on domain | GPO abuse → DA | Domain compromise |
| Anonymous LDAP bind | Full user enumeration | Reconnaissance |
| Null session access | RPC enumeration | Reconnaissance |
