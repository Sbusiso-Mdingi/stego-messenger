# Secure Steganographic Messenger

A covert communication system that combines modern authenticated encryption with image-based steganography to enable hidden, end-to-end secure messaging. This project focuses on concealing both **message content** and the **existence of communication**, demonstrating real-world covert channel techniques used in advanced cybersecurity systems.

---

## 🚀 Project Overview

Traditional secure messaging protects the *content* of communication, but not the *presence* of communication itself.  
This project explores how to build a system that hides encrypted messages inside ordinary-looking media to enable private, covert communication.

The system integrates:

- Strong cryptography
- Secure key derivation
- Steganographic embedding
- Adversarial robustness testing

It serves as both a learning project and a practical demonstration of applied cryptography and information hiding.

---

## 🧠 Security Objectives

This project is designed around the following security goals:

- **Confidentiality** – Message contents are protected using authenticated encryption.
- **Stealth** – Messages are hidden inside innocent-looking carrier images.
- **Integrity** – Encrypted payloads are authenticated to prevent tampering.
- **Robustness** – Embedded messages survive common transformations such as compression and resizing.
- **Resistance to Passive Surveillance** – Designed to obscure both data and communication patterns.

---

## 🔐 Cryptography

The system uses modern, secure cryptographic primitives:

| Component | Algorithm |
|-----------|------------|
| Symmetric Encryption | AES-GCM / Fernet (Authenticated Encryption) |
| Key Derivation | PBKDF2 |
| Integrity | Built-in via AEAD (Authenticated Encryption with Associated Data) |

All cryptographic operations are performed **before** steganographic embedding.

---

## 🖼 Steganography Techniques

Multiple embedding techniques are supported:

- **LSB (Least Significant Bit) embedding** – High-capacity, simple technique.
- **DCT (Discrete Cosine Transform) embedding** – Robust against compression and resizing.
- (Planned) **DWT (Discrete Wavelet Transform)** – For multi-scale robustness.

Each method can be evaluated against common attack simulations.

---

## ⚔️ Attack Simulation

The system includes tools to test the robustness of hidden messages against real-world transformations:

- JPEG compression
- Image resizing and rescaling
- Cropping
- Additive noise
- Colour depth reduction

A recovery success rate is calculated after each simulated attack.

---

## 🧩 System Architecture

High-level pipeline:

Plaintext message → Key derivation (PBKDF2) → Authenticated encryption (AES-GCM) → Steganographic embedding (LSB / DCT) → Stego-image generation

Extraction follows the reverse process.

---

## 🖥️ Features

- End-to-end encrypted hidden messaging
- Multiple steganography algorithms
- Screenshot and compression resilience
- Attack testing framework
- Interactive user interface
- Forensic-style extraction with confidence scoring

---

## 🧪 Threat Model

This project assumes:

- Adversaries can observe all transmitted media
- Adversaries may apply common image transformations
- Adversaries cannot break modern cryptography
- Adversaries do not have access to secret embedding keys

A full threat model is available in `threat_model.md`.

---

## 📊 Limitations

This system is a research and educational implementation and does **not** claim absolute resistance against advanced, targeted steganalysis or nation-state adversaries.

Trade-offs exist between:
- Payload capacity
- Invisibility
- Robustness

These trade-offs are explored and documented within the project.

---

## 🧰 Tech Stack

- Python
- NumPy
- OpenCV
- Pillow
- Cryptography (Fernet / AES-GCM)
- Streamlit (UI)

---

## 📁 Project Structure

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

## 🧪 Future Work

Planned enhancements:

- Add Reed–Solomon error correction
- Integrate Argon2 as KDF
- Add KMS support
- More robust DCT embedding
- Forensic report signing

---

## ⚠️ Disclaimer

This project is intended for educational and research purposes only.  
Users are responsible for complying with applicable laws and regulations regarding encryption and data hiding technologies.

---

## 👨‍💻 Author

**Sbusiso Mdingi** 

