# OWASP Top 10 Reference

## OWASP Top 10 (2021)

### A01: Broken Access Control
**Description**: Restrictions on what authenticated users are allowed to do are not properly enforced.
**Examples**:
- Violation of the principle of least privilege
- Bypassing access control checks
- Viewing or editing someone else's account
- Accessing API without proper access controls

**Prevention**:
- Implement access control mechanisms once and reuse them
- Model access controls should enforce record ownership
- Disable web server directory listing
- Log and alert on access control failures

### A02: Cryptographic Failures
**Description**: Failures related to cryptography which often leads to sensitive data exposure.
**Examples**:
- Data transmitted in clear text
- Weak cryptographic algorithms
- Poor key management
- Missing or weak cryptographic controls

**Prevention**:
- Classify data processed and identify which is sensitive
- Don't store sensitive data unnecessarily
- Encrypt all sensitive data at rest
- Ensure up-to-date and strong standard algorithms

### A03: Injection
**Description**: User-supplied data is not validated, filtered, or sanitized by the application.
**Examples**:
- SQL injection
- NoSQL injection
- OS command injection
- LDAP injection

**Prevention**:
- Use positive server-side input validation
- Escape special characters using ORM tools
- Use LIMIT and other SQL controls to prevent mass disclosure

### A04: Insecure Design
**Description**: Risks related to design flaws, missing or ineffective security controls.
**Examples**:
- Missing threat modeling
- Insecure design patterns
- Missing security controls
- Insecure business logic

**Prevention**:
- Establish and use a secure development lifecycle
- Use threat modeling for critical authentication and access flows
- Integrate security language and controls into user stories
- Write integration and unit tests to validate all critical flows

### A05: Security Misconfiguration
**Description**: Missing appropriate security hardening across any part of the application stack.
**Examples**:
- Missing appropriate security hardening
- Improperly configured permissions on cloud services
- Unnecessary features enabled
- Default accounts and passwords enabled

**Prevention**:
- A repeatable hardening process
- A minimal platform without unnecessary features
- Review and update configurations regularly
- Automated configuration verification

### A06: Vulnerable and Outdated Components
**Description**: Using components with known vulnerabilities.
**Examples**:
- Using components with known vulnerabilities
- Unsupported or out of date software
- Not scanning for vulnerabilities regularly
- Not fixing or upgrading underlying frameworks

**Prevention**:
- Remove unused dependencies, unnecessary features, components
- Continuously inventory versions of components
- Monitor for vulnerabilities in components
- Only obtain components from official sources

### A07: Identification and Authentication Failures
**Description**: Confirmation of the user's identity, authentication, and session management is not implemented correctly.
**Examples**:
- Permitting automated attacks
- Permitting brute force or other automated attacks
- Permitting weak passwords
- Missing or ineffective multi-factor authentication

**Prevention**:
- Implement multi-factor authentication
- Do not ship with default credentials
- Implement weak password checks
- Limit failed login attempts

### A08: Software and Data Integrity Failures
**Description**: Code and infrastructure that does not protect against integrity violations.
**Examples**:
- Insecure CI/CD pipelines
- Auto-update without sufficient integrity verification
- Deserialization of untrusted data
- Insecure software supply chain

**Prevention**:
- Use digital signatures to verify software/data
- Ensure libraries and dependencies are consuming trusted repositories
- Use a software supply chain security tool
- Ensure CI/CD pipeline has proper segregation and configuration

### A09: Security Logging and Monitoring Failures
**Description**: Insufficient logging, detection, monitoring, and active response.
**Examples**:
- Auditable events not logged
- Warnings and errors generate no, inadequate, or unclear log messages
- Logs only stored locally
- Penetration testing and scans do not trigger alerts

**Prevention**:
- Ensure all login, access control, and server-side input validation failures are logged
- Ensure logs are generated in a format easily consumed by log management solutions
- Establish effective monitoring and alerting
- Establish an incident response and recovery plan

### A10: Server-Side Request Forgery (SSRF)
**Description**: SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.
**Examples**:
- Fetching remote resources without validating the URL
- Remote code execution
- Internal service enumeration
- Access to internal services

**Prevention**:
- Segment remote resource access functionality in separate networks
- Enforce "deny by default" firewall policies
- Disable HTTP redirections
- Sanitize and validate all client-supplied input data
