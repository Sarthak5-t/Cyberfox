# OWASP API Security Top 10 Reference

## OWASP API Security Top 10 (2023)

### API1: Broken Object Level Authorization (BOLA)
**Description**: Attackers can manipulate the IDs of resources they shouldn't be able to access.
**Examples**:
- Accessing other users' data by changing IDs
- Enumerating resources by iterating IDs
- Accessing admin functions without authorization

**Prevention**:
- Implement object level authorization checks
- Use indirect object references
- Enforce authorization on every server function call
- Log and alert on authorization failures

### API2: Broken Authentication
**Description**: Authentication mechanisms are often implemented incorrectly, allowing attackers to compromise authentication.
**Examples**:
- Weak passwords allowed
- Credential stuffing attacks
- JWT tokens not validated properly
- Session tokens not invalidated

**Prevention**:
- Implement strong authentication mechanisms
- Limit failed login attempts
- Use multi-factor authentication
- Use secure session management

### API3: Broken Object Property Level Authorization
**Description**: Exposure of sensitive business functionality and data through API endpoints.
**Examples**:
- Returning more data than needed
- Not filtering response fields
- Exposing sensitive properties
- Mass assignment vulnerabilities

**Prevention**:
- Implement response filtering
- Use DTOs (Data Transfer Objects)
- Validate input against schema
- Implement property level access control

### API4: Unrestricted Resource Consumption
**Description**: APIs don't properly limit the consumption of resources.
**Examples**:
- No rate limiting
- No pagination
- No size limits on requests
- Denial of service through resource exhaustion

**Prevention**:
- Implement rate limiting
- Use pagination for large datasets
- Set maximum request size
- Implement resource quotas

### API5: Broken Function Level Authorization
**Description**: Authorization flaws allow attackers to access admin functions.
**Examples**:
- Regular users accessing admin endpoints
- Function level access control not enforced
- API endpoints not protected

**Prevention**:
- Implement function level authorization checks
- Deny all access by default
- Implement role-based access control
- Log and alert on access control failures

### API6: Unrestricted Access to Sensitive Business Flows
**Description**: APIs don't protect sensitive business flows from automated attacks.
**Examples**:
- Automated account creation
- Price manipulation
- Inventory hoarding
- Credit card fraud

**Prevention**:
- Identify and protect sensitive business flows
- Implement rate limiting per user/IP
- Use CAPTCHAs for critical operations
- Implement fraud detection

### API7: Server-Side Request Forgery (SSRF)
**Description**: APIs fetch remote resources without validating the user-supplied URL.
**Examples**:
- Fetching remote resources without validation
- Accessing internal services
- Remote code execution
- Internal port scanning

**Prevention**:
- Validate and sanitize all client-supplied input data
- Enforce "deny by default" firewall policies
- Disable HTTP redirections
- Segment remote resource access functionality

### API8: Security Misconfiguration
**Description**: APIs often have misconfigurations that can be exploited.
**Examples**:
- Unnecessary HTTP methods enabled
- Verbose error messages
- Missing security headers
- Default configurations

**Prevention**:
- Implement proper configuration management
- Use automated configuration verification
- Disable unnecessary features
- Implement security headers

### API9: Improper Inventory Management
**Description**: APIs don't properly track and manage their components.
**Examples**:
- Old API versions not deprecated
- Shadow APIs
- Missing documentation
- Inconsistent security controls

**Prevention**:
- Maintain an inventory of all APIs
- Deprecate old API versions
- Implement API documentation
- Use consistent security controls across all versions

### API10: Unsafe Consumption of APIs
**Description**: APIs consume third-party services without proper validation.
**Examples**:
- Trusting third-party APIs blindly
- Not validating third-party responses
- Using weak TLS configurations
- Not verifying response integrity

**Prevention**:
- Validate and sanitize data from third-party APIs
- Use secure communication channels
- Implement proper error handling
- Log and monitor third-party API consumption

## API Security Best Practices
### Authentication
- Use OAuth 2.0 with PKCE
- Implement API keys with rotation
- Use JWT tokens with proper validation
- Implement multi-factor authentication
- Use secure token storage

### Authorization
- Implement RBAC or ABAC
- Use object-level authorization
- Validate permissions on every request
- Log authorization failures
- Implement least privilege

### Input Validation
- Validate all input data
- Use schema validation
- Implement parameterized queries
- Sanitize output data
- Use content-type validation

### Rate Limiting
- Implement rate limiting per user/IP
- Use sliding window algorithms
- Implement backoff strategies
- Log rate limit violations
- Use distributed rate limiting

### Monitoring
- Log all API access
- Monitor for anomalies
- Implement alerting
- Use SIEM integration
- Regular security audits
