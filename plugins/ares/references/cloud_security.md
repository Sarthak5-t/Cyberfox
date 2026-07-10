# Cloud Security Reference

## Cloud Service Models
- **IaaS**: Infrastructure as a Service (AWS EC2, Azure VMs, GCP Compute)
- **PaaS**: Platform as a Service (Heroku, Google App Engine)
- **SaaS**: Software as a Service (Office 365, Salesforce)

## AWS Security
### IAM
- Follow principle of least privilege
- Use IAM roles instead of access keys
- Enable MFA for all users
- Rotate access keys regularly
- Use AWS Organizations for multi-account

### S3 Buckets
- Block public access by default
- Enable server-side encryption
- Use bucket policies with conditions
- Enable access logging
- Use pre-signed URLs for temporary access

### EC2
- Use security groups as firewalls
- Enable VPC flow logs
- Use Systems Manager for patching
- Enable CloudTrail for API logging
- Use AWS Config for compliance

## Azure Security
### Active Directory
- Enable Conditional Access
- Use Privileged Identity Management
- Enable Azure AD Identity Protection
- Use Managed Identities for applications
- Enable sign-in and audit logs

### Storage
- Enable encryption at rest
- Use shared access signatures (SAS)
- Enable logging for diagnostics
- Use Azure Key Vault for secrets
- Enable soft delete for recovery

## GCP Security
### IAM
- Use service accounts with minimal permissions
- Enable Audit Logging
- Use Organization Policies
- Enable VPC Service Controls
- Use Cloud KMS for encryption

### Compute
- Use OS Login for SSH
- Enable Shielded VMs
- Use VPC firewall rules
- Enable Flow Logs
- Use Cloud Security Scanner

## Container Security
### Docker
- Use official base images
- Scan images for vulnerabilities
- Use multi-stage builds
- Don't run as root
- Use Docker Content Trust

### Kubernetes
- Enable RBAC
- Use Network Policies
- Enable Pod Security Policies
- Use Secrets management
- Enable audit logging

## Serverless Security
- Use function-level permissions
- Validate input
- Use environment variables for secrets
- Enable logging
- Use API Gateway for authentication

## Cloud Penetration Testing
### Reconnaissance
- Enumerate public resources
- Check for misconfigured storage
- Identify exposed services
- Map network topology
- Review IAM policies

### Exploitation
- Test for SSRF vulnerabilities
- Check for privilege escalation
- Test for container escapes
- Evaluate serverless functions
- Test for data exposure

## Compliance Frameworks
- **SOC 2**: Service Organization Control
- **PCI DSS**: Payment Card Industry
- **HIPAA**: Health Insurance Portability
- **GDPR**: General Data Protection Regulation
- **ISO 27001**: Information Security Management
