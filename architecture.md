# Architecture — Secure Steganographic Messaging System

**Author:** Sbusiso Mdingi  
**Version:** 1.0  
**Date:** 2025-12-10

---

## Purpose

This document describes the system architecture for the **Secure Steganographic Messaging System**, including system components, data flow, trust boundaries, storage, deployment models, and security controls.

---

## System Diagram (Text Architecture)

        +---------------------------+
        |        End User           |
        |  (Browser / Streamlit UI) |
        +-----------+---------------+
                    |
                    | Upload Image + Password + Message
                    v
        +-----------+---------------+
        |     UI / Web Frontend     |
        |      (Streamlit App)      |
        +-----------+---------------+
                    |
                    | Local module calls
                    v
        +-----------+---------------+
        |   Embedding Engine Core   |
        | - PBKDF2 Key Derivation   |
        | - AES-GCM Encryption      |
        | - LSB/DCT Steganography   |
        | - Metadata Generator      |
        +-----------+---------------+
                   / \
                  /   \
                 /     \
    +------------+       +-------------+
    |   Storage  |       |  Attack &   |
    |  (Temp FS) |       |  Detection  |
    +------------+       +-------------+
                  \     /
                   \   /
                    v v
             +---------------+
             |   Investigator |
             | (Extraction &  |
             |  Forensics)    |
             +---------------+


---

## Core Components

### 1. User Interface (UI / Frontend)

- Built using Streamlit
- Handles:
  - Image upload/download
  - Password input
  - Message input
  - Attack simulation selection
  - Displaying recovered messages

---

### 2. Embedding Engine (Core Logic)

- Derives encryption keys using **PBKDF2**
- Encrypts messages using **AES-GCM**
- Embeds encrypted data using:
  - LSB (Least Significant Bit)
  - Optional DCT-based embedding
- Generates metadata including:
  - Salt
  - Iteration count
  - Embedding parameters

---

### 3. Storage Layer

- Uses temporary filesystem storage during runtime
- Creates downloadable packages:
  - `stego_image.png`
  - `stego_meta.json`
- No persistent storage by default

---

### 4. Attack Simulation Module

Simulates real-world image distortions:

- JPEG recompression
- Gaussian noise injection
- Cropping
- Resizing

Used to test message recovery under adversarial conditions.

---

### 5. Steganalysis / Detection Module

- Performs statistical analysis on images
- Detects LSB anomalies
- Optional ML-based detection

Outputs a suspicion/confidence score.

---

### 6. Investigation / Forensics Module

- Extracts data from stego images
- Performs ECC (optional) correction
- Verifies message integrity
- Generates forensic reports

---

## Data Flow

### Message Embedding Flow

1. User uploads an image and enters a password and message
2. System generates a random salt
3. Key is derived using PBKDF2
4. Message encrypted using AES-GCM
5. Ciphertext embedded using LSB or DCT
6. Metadata generated
7. Output packaged and delivered to user

---

### Message Extraction Flow

1. User uploads stego image and metadata
2. Salt and parameters read from metadata
3. Key derived from password
4. Hidden ciphertext extracted
5. Ciphertext decrypted
6. Plaintext returned to user

---

### Attack Simulation Flow

1. Stego image passed to attack engine
2. Image manipulated (compression/noise/etc.)
3. Modified image tested for extraction success
4. Success metrics displayed

---

## Trust Boundaries

- Client ↔ Application boundary (user input)
- Application ↔ Temporary Storage
- Application ↔ Attack Engine

Sensitive material (keys, plaintext) exists **only in memory** and is wiped after use.

---

## Security Controls

- PBKDF2 for key derivation
- AES-GCM for authenticated encryption
- Random per-session salt
- No plaintext storage on disk
- Optional ECC for robustness

---

## Deployment Models

### Local Mode
- Single-device Streamlit deployment
- Ideal for demos and research

### Server Mode
- Hosted via Flask/FastAPI or Streamlit Cloud
- TLS enabled
- Optional persistent storage

---

## Performance Considerations

- Embedding large images increases CPU/memory usage
- DCT-based embedding is more CPU-intensive
- Attack simulations are batch-processed

---

## Testing Strategy

- Unit tests for encryption and steganography
- Integration tests for full embed → extract flow
- Regression tests for robustness

---

## Privacy Considerations

- No personally identifiable information stored
- Metadata only contains cryptographic material
- Logs are optionally signed

---

## Project Structure

stego-messenger/
├── src/
│   ├── __init__.py
│   ├── lsb_stego.py
│   ├── dct_stego.py
│   ├── crypto_utils.py
│   ├── metadata.py
│   ├── attacks.py
│   ├── steganalysis.py
│   └── tests/
├── ui/
│   └── app.py
├── README.md
├── architecture.md
├── threat_model.md
├── security_controls.md
├── evaluation_metrics.md
└── requirements.txt


---

## Future Improvements

- Add Reed–Solomon error correction
- Integrate Argon2 as KDF
- Add KMS support
- More robust DCT embedding
- Forensic report signing

---