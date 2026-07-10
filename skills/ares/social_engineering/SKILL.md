# Social Engineering Skill

## Objective
Conduct social engineering assessments to test human security controls including phishing, pretexting, and physical security awareness.

## Pre-Engagement
- Confirm social engineering in scope
- Identify target organization and personnel
- Establish rules of engagement
- Create legal documentation
- Set up testing infrastructure

## Reconnaissance Phase

### 1. Target Research
```
# OSINT reconnaissance
theharvester -d <domain> -b all
recon-ng
Maltego
```

### 2. Organization Mapping
- Identify organizational structure
- Map employee roles and responsibilities
- Research company culture
- Identify key personnel
- Review public communications

### 3. Pretext Development
- Create believable cover stories
- Research current events
- Identify potential pretexts
- Develop social media personas
- Prepare supporting materials

## Execution Phase

### 1. Phishing Campaigns
```
# Set up phishing infrastructure
gophish
King Phisher
SET (Social Engineering Toolkit)

# Create phishing emails
# - Use convincing templates
# - Include malicious links/attachments
# - Track open rates and clicks
```

### 2. Vishing (Voice Phishing)
```
# Prepare vishing scripts
# - Impersonate IT support
# - Use authority figures
# - Create urgency
# - Record all interactions
```

### 3. Pretexting
```
# In-person pretexting
# - Impersonate maintenance staff
# - Use delivery伪装
# - Create diversions
# - Document all interactions
```

### 4. Physical Security Testing
```
# Tailgating attempts
# - Follow authorized personnel
# - Hold doors open
# - Use piggybacking techniques

# Baiting
# - Leave infected USB drives
# - Use enticing file names
# - Monitor for execution
```

## Post-Exploitation

### 1. Data Collection
- Harvest credentials
- Capture sensitive information
- Document successful breaches
- Record employee responses

### 2. Access Maintenance
- Maintain persistent access
- Create backup entry points
- Document access methods
- Cover tracks

### 3. Lateral Movement
- Use harvested credentials
- Access additional systems
- Pivot to other departments
- Escalate privileges

## Reporting

### 1. Executive Summary
- Scope of assessment
- Campaign results
- High-level findings
- Risk recommendations

### 2. Technical Findings
- Campaign statistics
- Successful attacks
- Failed attempts
- Employee responses

### 3. Remediation Recommendations
- Security awareness training
- Policy improvements
- Technical controls
- Organizational changes

## References
- `social_engineering.md` - Social engineering reference
- GoPhish documentation
- SET documentation
- Security awareness training resources
