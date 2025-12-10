# Evaluation Metrics — Secure Steganographic Messaging System

**Author:** Sbusiso Mdingi  
**Version:** 1.0  
**Date:** 2025-12-10

---

## Purpose

This document defines how the system’s **security, robustness, performance, and usability** are measured and evaluated.

These metrics transform the project from a functional prototype into an **engineered security system**.

---

## 1. Security Metrics

### 1.1 Confidentiality Metrics

| Metric | Description |
|--------|-------------|
| Encryption Strength | AES-256-GCM used for payload confidentiality |
| Key Derivation Strength | PBKDF2 iteration count effectiveness |
| Brute Force Resistance | Estimated time to break derived keys |

**Measurement Method:**
- Analyze PBKDF2 iterations
- Estimate key-search time using standard GPU benchmarks

---

### 1.2 Integrity Metrics

| Metric | Description |
|--------|-------------|
| Authentication Tag Validation | % of detected tampered payloads |
| Corruption Detection Rate | Ability to reject modified ciphertext |

**Success Criteria:**
- 100% detection of modified ciphertext

---

## 2. Steganographic Robustness Metrics

### 2.1 Payload Survival Rate

| Metric | Description |
|--------|-------------|
| Survival % | % of hidden messages successfully recovered after attack |
| Bit Error Rate (BER) | Number of incorrect bits per payload after extraction |

---

### 2.2 Attack Resistance Tests

| Attack Type | Evaluation Metric |
|------------|-------------------|
| JPEG Compression | Payload recovery success rate |
| Gaussian Noise | BER after noise injection |
| Cropping | % payload loss |
| Resizing | Recovery consistency |

---

## 3. Imperceptibility Metrics

### 3.1 Visual Distortion

| Metric | Description |
|--------|-------------|
| PSNR (Peak Signal-to-Noise Ratio) | Measures visible degradation |
| SSIM (Structural Similarity Index) | Measures structural changes |

**Target Thresholds:**
- PSNR > 40 dB
- SSIM > 0.95

---

## 4. Performance Metrics

### 4.1 Runtime Metrics

| Metric | Description |
|--------|-------------|
| Encryption Time | Time to encrypt message |
| Embedding Time | Time to hide payload |
| Extraction Time | Time to recover payload |

---

### 4.2 Resource Usage

| Metric | Description |
|--------|-------------|
| CPU Usage | % CPU consumed during embedding/extraction |
| Memory Usage | RAM consumed during processing |

---

## 5. Usability Metrics

| Metric | Description |
|--------|-------------|
| Task Completion Time | Time user takes to complete workflow |
| Error Rate | % of failed attempts due to user mistakes |
| UI Responsiveness | Perceived interface latency |

---

## 6. Reliability Metrics

| Metric | Description |
|--------|-------------|
| Crash Rate | Number of failures per 100 runs |
| Exception Handling Coverage | % of handled errors |

---

## 7. Attack Simulation Evaluation

Each attack is evaluated using:

| Metric | Description |
|--------|-------------|
| Recovery Rate | % of successful decryptions |
| Confidence Score | Steganalysis detection probability |

---

## 8. Success Criteria (Planned Targets)

The following metrics represent **intended evaluation targets** and are not measured results:

| Category | Planned Target |
|----------|----------------|
| Confidentiality | AES-GCM provides authenticated encryption |
| Integrity | System detects tampering via authentication tags |
| Robustness | Designed to withstand mild image transformations |
| Imperceptibility | Aims to minimise perceptual visual changes |
| Performance | Intended to be near real-time on consumer hardware |

These values represent **engineering intent**, not measured performance.

---

## 9. Limitations of Metrics

- Metrics are environment-dependent
- GPU acceleration not tested
- Advanced steganalysis not implemented

---

## 10. Future Evaluation Enhancements

- Add BER visualisation plots
- Monte-Carlo robustness modelling
- Adversarial deep-learning detection tests

---
