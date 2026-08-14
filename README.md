# Stego Messenger

**An open-source research toolkit for evaluating encrypted image steganography.**

Stego Messenger combines authenticated encryption, a simple LSB embedding baseline, deterministic image transformations, and reproducible evaluation metrics. The project's differentiator is not a claim that messages are undetectable or transformation-resistant; it is a framework for **measuring** capacity, distortion, recovery, and simple LSB statistics under explicit experimental conditions.

> **Status:** experimental research software. Not a production secure-messaging service and not a guarantee of covert or undetectable communication.

## What v0.2 implements

- AES-256-GCM authenticated encryption.
- scrypt password-based key derivation.
- Length-prefixed LSB embedding into lossless PNG output.
- Capacity validation before embedding.
- Deterministic JPEG, Gaussian-noise, centre-crop, and resize transformations.
- MSE, PSNR, bit-error rate (BER), payload capacity utilisation, and LSB-plane diagnostics.
- Automated tests and GitHub Actions CI.

## What it does **not** currently implement

- DCT or DWT embedding.
- Error-correcting codes.
- A calibrated steganalysis classifier.
- Guaranteed survival under lossy transformations.
- Network transport, covert command-and-control, or a production messaging protocol.

Those distinctions are deliberate: measured results and implemented features should be clearly separated from planned research.

## Evaluation-first workflow

1. Select a cover image and payload.
2. Encrypt the payload with AES-GCM using a scrypt-derived key.
3. Embed the ciphertext using the baseline LSB method.
4. Verify exact round-trip recovery.
5. Measure distortion and capacity utilisation.
6. Apply controlled transformations.
7. Record recovery success and BER instead of assuming robustness.
8. Compare transparent LSB diagnostics between cover and stego images.

See [`ROADMAP.md`](ROADMAP.md) for the planned benchmark corpus, SSIM, transform-domain baselines, error correction, and calibrated detection experiments.

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
attacks = evaluate_attacks("stego.png", b"payload", "benchmark-output")
```

The current LSB diagnostics are descriptive heuristics, **not probabilities of hidden data** and not a substitute for validated steganalysis.

## Development

```bash
ruff check src tests
pytest -q
```

Contributions should include reproducible parameters and tests. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Project structure

```text
src/                  cryptography, embedding, attacks, diagnostics, evaluation
ui/                   Streamlit demonstration UI
tests/                automated test suite
.github/workflows/     continuous integration
docs/releases/         versioned release notes
ROADMAP.md             planned research milestones
```

## Security and ethics

The repository is scoped to offline image-steganography research, defensive evaluation, and reproducibility. It is not intended for malware delivery, credential theft, covert persistence, command-and-control, or operational surveillance evasion. Review the threat model and security policy before interpreting results.

## Licence

Copyright 2026 Sbusiso Mdingi.

Licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
