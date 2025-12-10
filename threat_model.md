# Threat Model — Secure Steganographic Messaging System

**Author:** Sbusiso Mdingi  
**Version:** 1.0  
**Last Updated:** 2025-12-10

---

## 1. Overview

This document defines the threat model for the Secure Steganographic Messaging System, a project designed to securely embed encrypted messages inside digital images while maintaining confidentiality, stealth, integrity, and resilience against adversarial manipulation.

The system combines cryptographic primitives (AES-GCM, PBKDF2) with steganographic embedding techniques and includes an adversarial simulation framework for security testing.

---

## 2. System Scope

### In Scope

- Image based steganographic embedding
- Message encryption and decryption
- Password based key derivation
- Metadata handling
- User facing web interface
- Attack simulation framework
- Steganalysis detection module

### Out of Scope

- Full enterprise key management systems (HSM / hardware KMS)
- Protection against nation state level adversaries
- Hardware memory extraction attacks
- Endpoint device compromise

---

## 3. Assets to Protect

The primary sensitive assets in the system include:

- Plaintext user messages  
- Encrypted payloads (ciphertext)  
- User passwords  
- Derived cryptographic keys  
- Carrier and stego images  
- Metadata mappings  
- System logs and audit traces  

---

## 4. Threat Actors

| Actor Type | Description |
|------------|-------------|
| Honest User | Legitimate user of the system |
| Curious Recipient | Receives an image and attempts to inspect it |
| Malicious Insider | Has partial internal access to system components |
| Passive Observer | Third party platforms (e.g., image hosting services) |
| Active Attacker | Deliberately alters or destroys steganographic payloads |
| Automated Systems | Steganalysis scanners and content moderation systems |

---

## 5. Security Objectives

The system is designed to achieve the following objectives:

- **Confidentiality** — Protect plaintext and encryption keys  
- **Integrity** — Detect tampering of encrypted payloads  
- **Stealth** — Minimize detectability of hidden data  
- **Robustness** — Survive common image transformations  
- **Availability** — Ensure system remains responsive under load  
- **Auditability** — Enable forensic analysis post incident  

---

## 6. Methodology

Threats were evaluated using a hybrid STRIDE and risk-based approach:

- Attack vectors were mapped to system entry points  
- Risk was assessed using Likelihood × Impact analysis  
- Mitigations were designed based on industry best practices  

---

## 7. Key Threats and Risks

| ID | Threat | Likelihood | Impact | Risk |
|----|--------|------------|--------|------|
| T1 | Cryptographic key compromise | Medium | High | High |
| T2 | Image recompression destroys payload | High | Medium | High |
| T3 | Steganalysis detection | Medium | Medium | Medium |
| T4 | Deliberate image tampering | Medium | Medium | Medium |
| T5 | Metadata leakage | Low | High | Medium |

---

## 8. Threat Analysis and Mitigations

### T1 — Cryptographic Key Compromise

**Description:**  
An attacker gains access to password-derived encryption keys or internal secrets, allowing decryption or forgery of embedded data.

**Mitigations:**
- Strong password requirements  
- PBKDF2 with high iteration count  
- Ephemeral in memory key handling  
- No persistent key storage  
- Optional key rotation strategies  

**Residual Risk:** Medium

---

### T2 — Image Transformation Attacks

**Description:**  
Platforms may recompress or resize images, damaging embedded payloads.

**Mitigations:**
- Redundant embedding across pixel regions  
- Optional error tolerance via repetition coding  
- Robustness testing framework  
- User warnings for high loss formats  

**Residual Risk:** Medium

---

### T3 — Steganalysis Detection

**Description:**  
Automated detection tools could identify statistical anomalies in images.

**Mitigations:**
- Low density embedding  
- Randomized bit selection  
- High entropy carrier images  
- Built-in steganalysis scoring  

**Residual Risk:** Medium High

---

### T4 — Tampering and Corruption Attacks

**Description:**  
Attackers modify the stego image to prevent extraction.

**Mitigations:**
- Use of authenticated encryption (AES-GCM)  
- Tamper detection through authentication tags  
- Forensic-grade failure handling  

**Residual Risk:** Medium

---

### T5 — Metadata Leakage

**Description:**  
Exposure of metadata could reveal relationships between senders and recipients.

**Mitigations:**
- Local-only metadata storage  
- Encrypted metadata packages  
- Avoid cloud storage by default  

**Residual Risk:** Low–Medium

---

## 9. Detection and Response Strategy

The system is designed to:

- Log failed decryption attempts  
- Detect anomalous extraction patterns  
- Provide forensic output when tampering is detected  
- Support incident response workflows  

On detection of compromise:
- Disable active sessions  
- Invalidate sensitive in-memory data  
- Preserve forensic artifacts  

---

## 10. Security Testing Approach

Security testing includes:

- Unit testing of cryptographic functions  
- Robustness testing under lossy compression  
- Adversarial simulations  
- Fuzz testing of extraction logic  

---

## 11. Assumptions and Limitations

- Assumes the host environment is not fully compromised  
- Does not defend against advanced forensic laboratories  
- Not intended for whistleblower-grade anonymous channels  

---

## 12. Residual Risk Statement

Despite layered security controls, residual risks remain due to the nature of steganography and the limitations of consumer-grade image formats. These risks are considered acceptable for the intended use-cases of this system.

---

## 13. Review and Maintenance

This document will be reviewed and updated:

- After major feature changes  
- After new attack techniques are discovered  
- At least once per major version release  
