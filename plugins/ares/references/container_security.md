# Container Security Reference

## Docker Security
### Image Security
- Use official images from Docker Hub
- Scan images with Trivy, Clair, or Snyk
- Use multi-stage builds to reduce attack surface
- Pin image versions to specific digests
- Use Docker Content Trust for image signing

### Runtime Security
- Run containers as non-root
- Use read-only file systems
- Limit container resources (CPU, memory)
- Use security profiles (AppArmor, SELinux)
- Enable Docker daemon logging

### Network Security
- Use bridge networks for isolation
- Implement network segmentation
- Use Docker secrets for sensitive data
- Enable TLS for Docker daemon
- Use private registries

## Kubernetes Security
### Pod Security
- Use Pod Security Policies (PSP)
- Implement Security Contexts
- Use OPA/Gatekeeper for policies
- Enable admission controllers
- Use Pod Security Standards

### Network Policies
- Implement default deny policies
- Use namespace isolation
- Enable network policy enforcement
- Use service mesh for mTLS
- Implement ingress/egress controls

### Secrets Management
- Use Kubernetes Secrets
- Enable encryption at rest
- Use external secret stores (Vault)
- Rotate secrets regularly
- Audit secret access

### RBAC
- Follow least privilege principle
- Use role bindings appropriately
- Audit RBAC permissions
- Enable audit logging
- Use service accounts wisely

## Container Runtime Security
### Falco
- Detect abnormal behavior
- Monitor system calls
- Alert on suspicious activity
- Integrate with SIEM
- Custom rules for specific needs

### Sysdig
- Capture system activity
- Monitor container performance
- Detect security anomalies
- Integrate with threat intelligence
- Real-time visibility

## Container Scanning
### Trivy
- Scan images for vulnerabilities
- Scan file systems
- Scan repositories
- Integrate with CI/CD
- Generate SBOMs

### Clair
- Static analysis of vulnerabilities
- Integrate with registries
- Custom vulnerability data
- API-based scanning
- Support for multiple formats

## Container Hardening
### CIS Benchmarks
- Follow CIS Docker Benchmark
- Follow CIS Kubernetes Benchmark
- Regular compliance audits
- Automated remediation
- Continuous monitoring

### Best Practices
- Use minimal base images
- Remove unnecessary tools
- Enable security updates
- Use immutable infrastructure
- Implement defense in depth

## Container Penetration Testing
### Attack Vectors
- Container escapes
- Privilege escalation
- Network pivoting
- Secret extraction
- Resource abuse

### Testing Tools
- **kube-hunter**: Kubernetes penetration testing
- **kubeletctl**: Kubelet security testing
- **kube-bench**: CIS benchmark checks
- **kubeaudit**: Kubernetes security auditing
- **starscan**: Secret scanning

### Exploitation Techniques
- Container escape via kernel vulnerabilities
- Privileged container abuse
- Service account token theft
- Persistent backdoors
- Lateral movement in clusters
