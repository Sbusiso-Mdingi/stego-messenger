# Stego Messenger

**An open-source research toolkit for evaluating encrypted image steganography.**

Stego Messenger combines authenticated encryption, a simple LSB embedding baseline, deterministic image transformations, and reproducible evaluation metrics. The project's differentiator is not a claim that messages are undetectable or transformation-resistant; it is a framework for **measuring** capacity, distortion, recovery, and simple LSB statistics under explicit experimental conditions.

> **Status:** experimental research software. Not a production secure-messaging service and not a guarantee of covert or undetectable communication.

## What it implements

- AES-256-GCM authenticated encryption.
- scrypt password-based key derivation.
- Length-prefixed LSB embedding into lossless PNG output.
- Capacity validation before embedding.
- Deterministic JPEG, Gaussian-noise, centre-crop, and resize transformations.
- MSE, PSNR, SSIM, bit-error rate (BER), payload capacity utilisation, and LSB-plane diagnostics.
- **Two calibrated steganalysis detectors**: the Westfeld-Pfitzmann chi-square attack and
  Fridrich-Goljan-Du RS analysis, which estimates the embedding rate of sequential LSB
  replacement.
- **A reproducible benchmark** (`python -m src.benchmark`) that sweeps payload size across a
  fixed public-domain image corpus over several seeds and exports JSON and CSV with full
  environment metadata and confidence intervals.
- Automated tests and GitHub Actions CI.

## What it does **not** implement

- DCT or DWT embedding.
- Error-correcting codes.
- A learned (machine-learned) steganalysis classifier; the detectors here are the classical
  structural ones.
- Guaranteed survival under lossy transformations.
- Network transport, covert command-and-control, or a production messaging protocol.

Those distinctions are deliberate: measured results and implemented features should be clearly separated from planned research.

## Measured results

Full detail and the reproduction command are in [`docs/benchmarks/`](docs/benchmarks/README.md).
Five public-domain images, payload sizes from 0 to 90% of capacity, five seeds each.

| Payload | PSNR (dB) | SSIM | RS estimated rate | Recovery (PNG) |
| --- | --- | --- | --- | --- |
| 0% (control) | lossless | 1.0000 | 0.03 | 100% |
| 10% | 61.1 | 0.9996 | 0.12 | 100% |
| 50% | 54.2 | 0.9979 | 0.45 | 100% |
| 90% | 51.6 | 0.9960 | 0.83 | 100% |

The result worth stating plainly: the embedding is **visually invisible but statistically
obvious**. At a 10% payload the stego image is 61 dB from its cover (no perceptible change),
yet RS analysis recovers the embedding rate and separates it cleanly from a clean cover.
AES-256-GCM protects the content of the message; sequential LSB embedding does not hide its
presence from a standard detector. Recovery is exact only on the lossless PNG carrier; the
transformation experiments show JPEG, noise, cropping and resizing destroy the payload.

## Evaluation-first workflow

1. Select a cover image and payload.
2. Encrypt the payload with AES-GCM using a scrypt-derived key.
3. Embed the ciphertext using the baseline LSB method.
4. Verify exact round-trip recovery.
5. Measure distortion and capacity utilisation.
6. Apply controlled transformations.
7. Record recovery success and BER instead of assuming robustness.
8. Compare transparent LSB diagnostics between cover and stego images.

See [`ROADMAP.md`](ROADMAP.md) for the remaining milestones: transform-domain baselines, error-correcting codes, and a learned steganalysis classifier.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
```

For the Streamlit UI:

```bash
pip install -e '.[ui]'
streamlit run ui/app.py
```

## Minimal Python example

```python
from src.crypto_utils import generate_salt, derive_key_from_password, encrypt_message
from src.lsb_stego import embed_data

salt = generate_salt()
key = derive_key_from_password("research-passphrase", salt)
payload = encrypt_message("example", key)
embed_data("cover.png", payload, "stego.png")
```

## Reproducible evaluation

```python
from src.evaluation import evaluate_embedding, evaluate_attacks

result = evaluate_embedding("cover.png", b"payload", "stego.png")
# result includes psnr_db, ssim, and stego_detection (RS rate + chi-square probability)
attacks = evaluate_attacks("stego.png", b"payload", "benchmark-output")
```

## Steganalysis and benchmark

```python
from src.steganalysis import rs_analysis, chi_square_attack

rs_analysis("stego.png")["estimated_embedding_rate"]   # ~0 clean, ~payload fraction if embedded
chi_square_attack("stego.png")["mean_embedding_probability"]
```

```bash
python -m src.benchmark --out docs/benchmarks/latest   # full sweep, JSON + CSV
```

`lsb_diagnostics` / `lsb_randomness_score` are descriptive heuristics, **not probabilities
of hidden data**. `rs_analysis` and `chi_square_attack` are the calibrated detectors; RS is
the quantitative estimator and chi-square is a coarse screen (see the benchmark notes).

## Development

```bash
ruff check src tests
pytest -q
```

Contributions should include reproducible parameters and tests. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Project structure

```text
src/                  cryptography, embedding, attacks, steganalysis, evaluation, benchmark
ui/                   Streamlit demonstration UI
tests/                automated test suite
.github/workflows/     continuous integration
docs/benchmarks/       benchmark results (JSON, CSV) and notes
docs/releases/         versioned release notes
ROADMAP.md             planned research milestones
```

## Security and ethics

The repository is scoped to offline image-steganography research, defensive evaluation, and reproducibility. It is not intended for malware delivery, credential theft, covert persistence, command-and-control, or operational surveillance evasion. Review the threat model and security policy before interpreting results.

## Licence

Copyright 2026 Sbusiso Mdingi.

Licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
