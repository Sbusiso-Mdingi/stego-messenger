# Stego Messenger

**An open-source research toolkit for evaluating encrypted image steganography.**

Stego Messenger combines authenticated encryption, two LSB embedding methods, deterministic image transformations, and reproducible evaluation metrics. The project's differentiator is not a claim that messages are undetectable or transformation-resistant; it is a framework for **measuring** capacity, distortion, recovery, and detectability under explicit experimental conditions.

> **Status:** experimental research software. Not a production secure-messaging service and not a guarantee of covert or undetectable communication.

**Live preview:** [mdingi-stego.azurewebsites.net](https://mdingi-stego.azurewebsites.net) hides a message with both methods and runs the detectors on each result.

## What it implements

- AES-256-GCM authenticated encryption with scrypt password-based key derivation.
- **Self-contained stego images**: the salt and scrypt parameters travel inside the
  embedded payload, so the PNG and the password are all extraction needs (`src/package.py`).
- Optional random padding to a chosen share of capacity, so payload size does not reveal
  message length.
- Two embedding methods behind one length-prefixed framing:
  - `sequential`: LSB replacement in raster order, the baseline;
  - `keyed` (default): LSB matching (+1 or -1) at positions from a password-seeded
    permutation, so changes are scattered across the image.
- Capacity validation before embedding; lossless PNG output.
- Deterministic JPEG, Gaussian-noise, centre-crop, and resize transformations.
- MSE, PSNR, SSIM, bit-error rate (BER), payload capacity utilisation, and LSB-plane diagnostics.
- **Three steganalysis detectors**: the Westfeld-Pfitzmann chi-square attack and
  Fridrich-Goljan-Du RS analysis, which target LSB replacement, and the calibrated HCF
  centre of mass (Harmsen-Pearlman, Ker), which targets LSB matching.
- **A reproducible benchmark** (`python -m src.benchmark`) that sweeps payload size and
  method across a fixed public-domain image corpus over several seeds and exports JSON and
  CSV with full environment metadata and confidence intervals.
- A FastAPI + React web preview (`web/`) and a container image for Azure App Service.
- Automated tests and GitHub Actions CI.

## What it does **not** implement

- DCT or DWT embedding.
- Error-correcting codes or adaptive (content-aware) embedding.
- A learned (machine-learned) steganalysis classifier; the detectors here are the classical
  structural and histogram ones.
- Guaranteed survival under lossy transformations.
- Network transport, covert command-and-control, or a production messaging protocol.

Those distinctions are deliberate: measured results and implemented features should be clearly separated from planned research.

## Measured results

Full detail and the reproduction command are in [`docs/benchmarks/`](docs/benchmarks/README.md).
Five public-domain images, payload sizes from 0 to 90% of capacity, five seeds, both methods.

| Payload | PSNR (dB) | SSIM | RS rate, sequential | RS rate, keyed | HCF-COM shift, keyed |
| --- | --- | --- | --- | --- | --- |
| 0% (control) | lossless | 1.0000 | 0.03 | 0.03 | 0.000 |
| 10% | 61.1 | 0.9996 | 0.12 | 0.03 | -0.016 |
| 50% | 54.2 | 0.9979 | 0.45 | 0.06 | -0.091 |
| 90% | 51.6 | 0.9960 | 0.83 | 0.07 | -0.148 |

The results worth stating plainly:

- **Sequential replacement is visually invisible but statistically obvious.** At a 10%
  payload the stego image is 61 dB from its cover, yet RS analysis recovers the embedding
  rate and separates it cleanly from a clean cover.
- **Keyed matching takes RS and chi-square back to near the clean level** at the same
  distortion, because matching does not create the pairs-of-values symmetry they measure.
  The exception is images with large saturated areas, where a value of 0 can only move to 1.
- **It is not undetectable.** HCF-COM, built for matching, moves steadily with keyed
  payload size, and learned detectors are stronger still. AES-256-GCM protects the content;
  no method here guarantees nobody can tell a message is there.
- Recovery is exact only on the lossless PNG carrier; JPEG, noise, cropping and resizing
  destroy the payload.

## Evaluation-first workflow

1. Select a cover image and payload.
2. Encrypt the payload with AES-GCM using a scrypt-derived key.
3. Embed the ciphertext with either method.
4. Verify exact round-trip recovery.
5. Measure distortion and capacity utilisation.
6. Run the detectors on cover and stego.
7. Apply controlled transformations and record recovery success and BER instead of assuming robustness.

See [`ROADMAP.md`](ROADMAP.md) for the remaining milestones: transform-domain baselines, error-correcting codes, and a learned steganalysis classifier.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
```

For the web preview (FastAPI service and React page):

```bash
pip install -e '.[web]'
cd web/dashboard && bun install && bun run build && cd ../..
uvicorn web.service.main:app --port 8011   # open http://localhost:8011
```

## Minimal Python example

```python
from src.package import seal, open_package

seal("cover.png", "meet at the station", "research-passphrase", "stego.png", method="keyed")
open_package("stego.png", "research-passphrase")   # ("meet at the station", "keyed")
```

The lower-level pieces remain available: `src.crypto_utils` for AES-GCM and scrypt, and
`src.lsb_stego.embed_data` / `extract_data` with `method="sequential"` or
`method="keyed", key=...` for raw bytes.

## Reproducible evaluation

```python
from src.evaluation import evaluate_embedding, evaluate_attacks

result = evaluate_embedding("cover.png", b"payload", "stego.png", method="keyed", key=b"k")
# result includes psnr_db, ssim, and stego_detection (RS rate, chi-square, HCF-COM ratio)
attacks = evaluate_attacks("stego.png", b"payload", "benchmark-output")
```

## Steganalysis and benchmark

```python
from src.steganalysis import chi_square_attack, hcf_com_calibrated, rs_analysis

rs_analysis("stego.png")["estimated_embedding_rate"]   # ~0 clean, ~payload fraction if replaced
chi_square_attack("stego.png")["mean_embedding_probability"]
hcf_com_calibrated("stego.png")["ratio"]               # falls with LSB matching; compare to cover
```

```bash
python -m src.benchmark --out docs/benchmarks/latest   # full sweep, JSON + CSV
```

`lsb_diagnostics` / `lsb_randomness_score` are descriptive heuristics, **not probabilities
of hidden data**. `rs_analysis` and `chi_square_attack` are the calibrated replacement
detectors; RS is the quantitative estimator and chi-square is a coarse screen.
`hcf_com_calibrated` is a matching detector whose score is most informative against the
image's own cover (see the benchmark notes).

## Development

```bash
ruff check src tests web
pytest -q
```

Contributions should include reproducible parameters and tests. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Project structure

```text
src/                  cryptography, embedding, attacks, steganalysis, evaluation, benchmark
web/service/          FastAPI service behind the live preview
web/dashboard/        React preview page, embeddable in mdingi.co.za
deploy/               Azure App Service deployment script
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
