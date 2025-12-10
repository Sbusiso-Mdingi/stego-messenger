# Security Controls — Secure Steganographic Messaging System

**Author:** Sbusiso Mdingi  
**Version:** 1.0  
**Date:** 2025-12-10

---

## Purpose

This document defines the **technical and procedural security controls** implemented in the Secure Steganographic Messaging System and maps them to the threats identified in the threat model.

---

## 1. Cryptographic Controls

### 1.1 Key Derivation

| Control | Description |
|--------|-------------|
| PBKDF2 | Derives encryption keys from user passwords |
| Per-user Salt | Random salt generated for each session |
| Iteration Count | Configurable work factor to slow brute-force attacks |

---

### 1.2 Encryption

| Control | Description |
|--------|-------------|
| AES-GCM | Authenticated encryption for confidentiality and integrity |
| 256-bit Keys | Strong symmetric encryption standard |
| Authentication Tags | Detect ciphertext tampering |

---

## 2. Steganographic Controls

### 2.1 Data Hiding

| Control | Description |
|--------|-------------|
| LSB Embedding | Least Significant Bit data hiding in pixel channels |
| Configurable Payload Size | Limits embedding capacity to reduce detection risk |

---

### 2.2 Imperceptibility Controls

| Control | Description |
|--------|-------------|
| Visual Degradation Check | Avoids embedding beyond safe capacity |
| Adaptive Embedding Rate | Reduces changes in smooth regions of images |

---

## 3. Application-Level Controls

| Control | Description |
|--------|-------------|
| Input Validation | Checks image types and sizes |
| Error Handling | Prevents crashes from malformed inputs |
| Memory-Only Key Handling | Keys are not written to disk |

---

## 4. Threat → Control Mapping

| Threat | Control | Residual Risk |
|-------|--------|---------------|
| Brute-force password attacks | PBKDF2 + high iteration count | Weak user passwords still vulnerable |
| Payload extraction by attacker | AES-GCM encryption | Encrypted but detectable |
| Image recompression attacks | Attack simulation + user warning | Data loss possible |
| Metadata tampering | AES-GCM authentication tags | Replay attacks possible |
| Steganalysis detection | Limited embedding and randomness | Advanced ML detection possible |

---

## 5. Operational Controls

| Control | Description |
|--------|-------------|
| Secure Defaults | Secure crypto parameters set by default |
| Temporary Storage | Temp files auto-deleted |
| No Persistent Logs | Sensitive data not logged to disk |

---

## 6. Secure Development Practices

- Modular architecture
- Explicit trust boundaries
- Defensive coding patterns
- Dependency version pinning

---

## 7. Known Security Limitations

The system does **not** currently implement:

- Hardware-backed key storage (HSM/TPM)
- Forward secrecy
- Post-quantum cryptography
- Formal side-channel protections

---

## 8. Future Security Enhancements

- Migrate to Argon2 KDF
- Add Reed-Solomon error correction
- Introduce secure enclaves
- Add ML-based steganalysis resistance

---
