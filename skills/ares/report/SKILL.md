name: ares/report
description: "Consolidate findings, score impact, and generate structured security reports."
version: 2.0.0
author: Cyberfox Agent
platforms: [linux]
metadata:
  cyberfox:
    tags: [Ares, Reporting, Documentation, Pentest]
    related_skills: [ares/lead, ares/recon, ares/scanning, ares/exploit, ares/ad]
    category: ares

---

# Ares Report Skill — Professional Security Reporting

Consolidate all findings from recon, scanning, exploitation, and AD phases into structured reports. A good report is the final deliverable — make it complete, accurate, and actionable.

## When to Use

- End of engagement — produce the final deliverable
- User asks for a status summary or interim report
- Any time findings are discovered (save incrementally, not just at the end)

## Prerequisites

- Findings from earlier phases saved via `findings_save`
- `findings_stats` to verify coverage before reporting

## Report Structure

```
SECURITY ASSESSMENT REPORT
├── 1. Executive Summary (1 page max)
│   ├── Scope definition
│   ├── Critical findings count
│   ├── Overall risk rating
│   └── Key recommendations
│
├── 2. Methodology
│   ├── Testing approach (OWASP, PTES, NIST)
│   ├── Tools used
│   ├── Phases executed
│   └── Limitations and constraints
│
├── 3. Findings Summary
│   ├── Severity distribution (Critical/High/Medium/Low/Info)
│   ├── Category distribution (Network/Web/AD/Config)
│   └── Risk matrix visualization
│
├── 4. Detailed Findings (one section per finding)
│   ├── Title + CVSS score
│   ├── Affected asset (IP:port, URL)
│   ├── Description
│   ├── Evidence (command output, screenshots)
│   ├── Impact assessment
│   └── Remediation steps
│
├── 5. Attack Narrative
│   ├── Attack chain walkthrough
│   ├── Lateral movement path
│   └── Privilege escalation flow
│
├── 6. Remediation Roadmap
│   ├── Immediate (Critical/High)
│   ├── Short-term (Medium)
│   ├── Long-term (Low/Info)
│   └── Strategic recommendations
│
└── 7. Appendices
    ├── Tool output details
    ├── Raw scan results
    └── References (CVEs, advisories)
```

## Step-by-Step Procedure

### 1. Collect All Findings

```bash
findings_query(limit=200)
findings_stats()
```

Review completeness:
- Are all phases covered?
- Are critical findings documented with evidence?
- Are failed attempts included?

### 2. Classify and Prioritize

**CVSS 3.1 Scoring Reference:**

| Severity | CVSS Range | Examples |
|---|---|---|
| Critical | 9.0 - 10.0 | RCE, domain admin compromise, unauth data exfil |
| High | 7.0 - 8.9 | Auth bypass, SQLi with data access, privilege escalation |
| Medium | 4.0 - 6.9 | Info disclosure, weak config, limited SQLi |
| Low | 0.1 - 3.9 | Version disclosure, verbose errors, missing headers |
| Info | 0.0 | Default banners, open ports, DNS records |

**CVSS Vector Components:**
```
AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H = Critical (10.0)
AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N = High (7.5)
AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H = High (8.8)
AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H = Medium (6.3)
```

### 3. Write Executive Summary

Template:
```markdown
## Executive Summary

During [dates], a comprehensive security assessment was conducted against [scope].
The assessment identified [X] critical, [X] high, [X] medium, and [X] low severity
vulnerabilities.

The most significant findings include:
- [Critical finding 1 — one sentence]
- [Critical finding 2 — one sentence]
- [High finding 1 — one sentence]

Overall risk rating: [CRITICAL/HIGH/MEDIUM/LOW]

Immediate action is required to address the critical and high severity findings,
which could lead to [impact description].
```

### 4. Write Detailed Findings

Template for each finding:
```markdown
### F-[NNN]: [Title] (CVSS: [X.Y])

**Severity:** Critical/High/Medium/Low
**Category:** Network/Web/AD/Configuration
**Affected Asset:** [IP:port or URL]
**CWE:** [CWE-ID if applicable]
**CVE:** [CVE-ID if applicable]

#### Description
[What was found — clear, technical description]

#### Evidence
```
[Command output or proof of concept]
```

#### Impact
[What an attacker could achieve]

#### Remediation
1. [Specific fix step 1]
2. [Specific fix step 2]
3. [Verification step]

#### References
- [NVD link, vendor advisory, or relevant reference]
```

### 5. Attack Narrative

Document the attack chain as a story:
```markdown
## Attack Narrative

The assessment began with passive reconnaissance against [scope], revealing [X]
subdomains and [X] IP addresses. Port scanning identified [X] live hosts with
[X] open services.

The first compromise was achieved via [method] against [target], yielding
[access level]. From this foothold, lateral movement was performed using
[technique], eventually reaching [high-value target].

The final objective — [Domain Admin / full domain compromise / data access] —
was achieved via [technique], demonstrating that [impact summary].
```

### 6. Remediation Roadmap

| Priority | Finding | Remediation | Timeline |
|---|---|---|---|
| P1 | RCE via CVE-XXXX | Patch to version X.Y.Z | Immediate (24h) |
| P2 | SQL injection on /api | Parameterize queries, WAF | 1 week |
| P3 | Missing security headers | Add CSP, HSTS, X-Frame | 2 weeks |
| P4 | Version disclosure | Suppress server headers | 1 month |

### 7. Delegate Report Writing (Optional)

For large engagements, delegate report consolidation:
```bash
ares_delegate(
    role="soc_analyst",
    action="report",
    goal="Compile all findings into a structured security report",
    context="[engagement scope and key findings summary]"
)
```

## Report Quality Standards

### Do:
- Use precise technical language (CVE numbers, port numbers, service versions)
- Include command output as evidence for every finding
- Provide actionable remediation steps (not just "fix the issue")
- Separate findings by severity and category
- Include an attack narrative that shows the impact chain
- Add a remediation roadmap with timelines
- Reference industry standards (OWASP, NIST, PTES)

### Don't:
- Include raw scan output without analysis
- Use vague descriptions ("the server might be vulnerable")
- Forget to mention failed attacks (they inform risk assessment)
- Inflate severity (be honest about CVSS)
- Skip the executive summary (management reads this first)
- Omit evidence (findings without proof are not actionable)

## Report Templates

### Full Assessment Report
```markdown
# Security Assessment Report

**Client:** [Organization Name]
**Assessment Type:** [Penetration Test / Vulnerability Assessment / Red Team]
**Scope:** [IP ranges, domains, applications]
**Dates:** [Start Date] - [End Date]
**Assessor:** Ares (Cyberfox Agent)

## Executive Summary
[2-3 paragraphs]

## Scope
[Detailed scope definition]

## Methodology
[Testing approach and standards]

## Findings Summary
| Severity | Count |
|----------|-------|
| Critical | [X] |
| High | [X] |
| Medium | [X] |
| Low | [X] |
| Info | [X] |

## Detailed Findings
[Individual findings]

## Attack Narrative
[How the attack chain unfolded]

## Remediation Roadmap
[Prioritized fixes with timelines]

## Appendices
[Raw data and references]
```

### Quick Assessment Report
```markdown
# Quick Security Assessment

**Target:** [scope]
**Date:** [date]
**Assessor:** Ares

## Findings
[Top 5-10 findings with severity and brief description]

## Recommendations
[Prioritized action items]
```

## Pitfalls

- Do NOT wait until the end to save findings — save each one immediately
- Always include evidence — findings without evidence are not actionable
- CVSS scores should be honest — don't inflate severity
- Separate AD findings from network findings — different remediation owners
- If the engagement found nothing, write a negative report: "no exploitable vulnerabilities identified within scope"
- Include failed attempts — they help the client understand their defenses
- Executive summary should be readable by non-technical management

## Verification Checklist

- [ ] Every finding has a unique ID, severity, description, and evidence
- [ ] Executive summary covers the whole engagement
- [ ] Remediation steps are specific and actionable
- [ ] Attack narrative is present (if exploitation was performed)
- [ ] Remediation roadmap includes timelines
- [ ] Report is saved to `~/.cyberfox/ares/reports/`
- [ ] All findings from database are included (no missing findings)
