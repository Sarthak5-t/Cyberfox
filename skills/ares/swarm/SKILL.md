name: ares/swarm
description: "Multi-agent parallel engagement — concurrent recon, scanning, and exploitation."
version: 1.0.0
author: Cyberfox Agent
platforms: [linux]
metadata:
  cyberfox:
    tags: [Ares, Swarm, Parallel, Pentest, Red-Team]
    related_skills: [ares/lead, ares/recon, ares/scanning, ares/exploit]
    category: ares

---

# Ares Swarm Skill — Parallel Agent Coordination

You are **Ares**, running in swarm mode. Multiple specialist agents work in parallel to maximize coverage and minimize engagement time.

## When to Use

- User says "swarm" or "parallel assessment"
- Target is a large network or domain requiring broad coverage
- Time-critical engagement
- Multiple services discovered that need simultaneous testing

## Strategy Selection

| Strategy | When to Use | Behavior |
|----------|-------------|----------|
| `recon_first` | Single IP, careful approach (DEFAULT) | Recon agent runs first → parallel scan + exploit based on findings |
| `parallel_full` | Domain/range, known scope | All agents dispatched simultaneously |
| `stealth` | Sensitive environment, IDS/IPS | Single recon agent with low noise → targeted follow-up |
| `aggressive` | Time-critical, maximum coverage | All 5 agents with maximum tools |

## Workflow

### Step 1: Initialize Engagement
```
engage_init(name="swarm-{target}", scope=["{target}"])
plan_create(template="kill_chain")
```

### Step 2: Dispatch Swarm
```
swarm_dispatch(target="{target}", strategy="recon_first", max_agents=3)
```

### Step 3: Monitor Progress
```
findings_stats()
entity_count()
```

### Step 4: Generate Report
```
findings_query(severity="critical,high")
```

## Agent Roles

| Role | Toolsets | Purpose |
|------|----------|---------|
| `swarm_recon` | `ares_recon` | Port scan, DNS, subdomains, service fingerprint |
| `swarm_web` | `ares_scanning` | Web vuln scanning, dir brute, WAF detect |
| `swarm_network` | `ares_scanning` | SMB enum, SNMP, network vulns |
| `swarm_ad` | `ares_scanning`, `ares_ad` | AD enumeration, Kerberoast, BloodHound |
| `swarm_exploit` | `ares_exploit`, `ares_scanning` | Exploitation, credential attacks |

## Inter-Agent Coordination

All agents share data via:
1. **findings.db** — Write findings with `findings_save`, query with `findings_query`
2. **engagement.db** — Entity/relationship graph updated in real-time
3. **EventBus** — Real-time signals between agents

## Strategy Details

### recon_first (Default)
1. Phase 1: Single recon agent (nmap, dnsrecon, subfinder, whatweb)
2. Coordinator queries engagement.db for discovered services
3. Phase 2: Parallel web + network + exploit agents based on findings
4. All agents write to shared findings.db

### parallel_full
- All agents dispatched simultaneously
- Recon, web, network, exploit run in parallel
- Fastest but may waste resources on undiscovered services

### stealth
- Single recon agent with SYN scan only, passive DNS
- No noisy tools (no gobuster, no masscan)
- Targeted follow-up based on recon findings

### aggressive
- All 5 agents with maximum tools enabled
- Maximum parallelism
- Highest noise level — expect WAF/IDS alerts

## OPSEC Considerations

- `stealth` strategy: SYN scan only, passive DNS, rate-limited
- `recon_first`: Recon completed before noisy scan/exploit phases
- `parallel_full`: All agents respect individual OPSEC levels
- `aggressive`: Maximum noise, all tools enabled

## Error Recovery

| Error | Recovery |
|-------|----------|
| Agent timeout | Check findings.db for partial results, retry with different strategy |
| No services found | Expand recon, try masscan, verify target is live |
| WAF blocking | Switch to stealth strategy, use evasion flags |
| All agents fail | Fall back to sequential kill chain via lead skill |

## Constraints

- Max 5 concurrent agents
- Each agent inherits scope validation
- Exploit agents require user approval
- All agents log to shared findings.db
- Clean up after exploitation
