# Wireless Security Reference

## WiFi Security
### WPA3
- **SAE**: Simultaneous Authentication of Equals
- **OWE**: Opportunistic Wireless Encryption
- **GCMP-256**: Galois/Counter Mode Protocol
- **HAR2**: Hash-to-Element
- **Protected Management Frames**

### WPA2
- **CCMP**: Counter Mode CBC MAC Protocol
- **PMF**: Protected Management Frames
- **4-Way Handshake**
- **Group Key Handshake**

### WEP (Deprecated)
- **RC4** stream cipher (broken)
- **IV** reuse vulnerabilities
- **FMS attack**
- **KoreK attack**
- **PTW attack**

## Wireless Attacks
### Deauthentication
- Send deauth frames to disconnect clients
- Capture 4-way handshake
- Use for offline cracking
- Tools: aireplay-ng, mdk4

### Evil Twin
- Create rogue access point
- Intercept client traffic
- Perform MITM attacks
- Tools: hostapd, Fluxion

### Karma Attack
- Respond to client probes
- Impersonate known networks
- Intercept connections
- Tools: mana toolkit

### KRACK Attack
- Key Reinstallation Attack
- Exploits 4-way handshake
- Forces nonce reuse
- Affects WPA2

### FragAttacks
- Fragmentation and Aggregation Attacks
- Exploits WiFi frame aggregation
- Allows data injection
- Affects all WiFi security

## Wireless Penetration Testing
### Reconnaissance
- Scan for wireless networks
- Identify access points
- Map wireless coverage
- Identify client devices
- Review wireless policies

### Discovery
- Use wireless adapters in monitor mode
- Capture beacon frames
- Identify hidden networks
- Map BSSIDs and ESSIDs
- Identify encryption types

### Exploitation
- Capture 4-way handshake
- Perform deauthentication
- Crack WPA/WPA2 passwords
- Test for KRACK vulnerability
- Test for FragAttacks

### Post-Exploitation
- Intercept client traffic
- Perform MITM attacks
- Access internal networks
- Pivoting to wired network
- Data exfiltration

## Wireless Security Tools
### Scanning
- **airodump-ng**: Packet capture
- **Kismet**: Wireless detector
- **Wifite**: Automated attack tool
- **LinSSID**: Wireless scanner
- **WiFi-Pumpkin**: Rogue AP

### Cracking
- **aircrack-ng**: WEP/WPA cracking
- **hashcat**: Password cracking
- **John the Ripper**: Password cracking
- **cowpatty**: WPA PSK cracking
- **pyrit**: WPA PSK cracking

### Attack
- **aireplay-ng**: Packet injection
- **mdk4**: Wireless attacks
- **Reaver**: WPS attack
- **Bully**: WPS attack
- **Fern WiFi Cracker**: GUI attack tool

### Monitoring
- **Wireshark**: Packet analysis
- **tcpdump**: Packet capture
- **Kismet**: Wireless monitoring
- **Airmon-ng**: Monitor mode
- **airodump-ng**: Packet capture

## Wireless Security Best Practices
### Network Design
- Use WPA3 where possible
- Implement network segmentation
- Use separate networks for guests
- Enable rogue AP detection
- Implement wireless IDS/IPS

### Access Control
- Use 802.1X authentication
- Implement RADIUS server
- Use certificate-based authentication
- Enable MAC filtering (weak)
- Implement device profiling

### Monitoring
- Enable wireless logging
- Monitor for rogue APs
- Implement anomaly detection
- Use wireless IDS/IPS
- Regular security audits

### Physical Security
- Control physical access to APs
- Disable unused ports
- Secure network closets
- Implement cable security
- Monitor physical perimeter
