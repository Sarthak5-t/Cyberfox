# Mobile Security Reference

## Android Security
### Application Security
- Use ProGuard/R8 for obfuscation
- Implement certificate pinning
- Encrypt sensitive data
- Use Android Keystore for keys
- Implement root detection

### Network Security
- Use Network Security Config
- Enforce HTTPS
- Implement certificate pinning
- Use TLS 1.2+
- Disable cleartext traffic

### Data Storage
- Use EncryptedSharedPreferences
- Encrypt databases with SQLCipher
- Use Android Keystore system
- Implement secure key management
- Clear sensitive data from memory

### Authentication
- Implement BiometricPrompt
- Use Android KeyStore for credentials
- Implement secure session management
- Use OAuth 2.0 with PKCE
- Implement timeout policies

## iOS Security
### Application Security
- Use App Transport Security (ATS)
- Implement Keychain Services
- Use Secure Enclave for keys
- Implement jailbreak detection
- Use code signing

### Data Protection
- Use iOS Data Protection API
- Implement Keychain items
- Use File Protection classes
- Encrypt CoreData/SQLite
- Implement secure deletion

### Network Security
- Enforce ATS
- Implement certificate pinning
- Use URLSession with TLS
- Implement SSL/TLS validation
- Use apples-transport-security

### Authentication
- Implement LocalAuthentication
- Use Keychain for credentials
- Implement Secure Enclave
- Use OAuth 2.0
- Implement session management

## Mobile Penetration Testing
### Reconnaissance
- Analyze app architecture
- Map API endpoints
- Identify authentication mechanisms
- Review app permissions
- Analyze network traffic

### Static Analysis
- Decompile APK/IPA
- Analyze source code
- Check for hardcoded secrets
- Review cryptographic implementations
- Analyze permission requests

### Dynamic Analysis
- Intercept network traffic
- Monitor API calls
- Test authentication flows
- Analyze data storage
- Test for common vulnerabilities

### Common Vulnerabilities
- **OWASP Mobile Top 10**:
  1. Improper Platform Usage
  2. Insecure Data Storage
  3. Insecure Communication
  4. Insecure Authentication
  5. Insufficient Cryptography
  6. Insecure Authorization
  7. Client Code Quality
  8. Code Tampering
  9. Reverse Engineering
  10. Extraneous Functionality

## Mobile Security Tools
### Android Tools
- **APKTool**: Reverse engineering
- **Jadx**: Decompiler
- **Drozer**: Security testing
- **Frida**: Dynamic instrumentation
- **Objection**: Runtime mobile exploration

### iOS Tools
- **class-dump**: Objective-C header dumping
- **Hopper**: Disassembler
- **Frida**: Dynamic instrumentation
- **Objection**: Runtime mobile exploration
- **iProxy**: Proxy tool

### Network Tools
- **Burp Suite**: Web proxy
- **mitmproxy**: Interactive proxy
- **Charles Proxy**: Web proxy
- **Wireshark**: Network analysis
- **tcpdump**: Packet capture

## Mobile Security Best Practices
### Development
- Use secure coding practices
- Implement proper error handling
- Use secure random number generation
- Implement input validation
- Use secure file permissions

### Testing
- Perform static analysis
- Conduct dynamic testing
- Test for common vulnerabilities
- Validate security controls
- Document findings

### Deployment
- Use secure deployment practices
- Implement certificate pinning
- Use secure update mechanisms
- Monitor for security events
- Implement incident response
