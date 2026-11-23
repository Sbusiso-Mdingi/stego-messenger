# Stego Messenger

**An open-source research toolkit for evaluating encrypted image steganography.**

Stego Messenger combines authenticated encryption, two LSB embedding methods, a JPEG-domain method that survives WhatsApp photos, deterministic image transformations, and reproducible evaluation metrics. The project's differentiator is not a claim that messages are undetectable or survive any transformation; it is a framework for **measuring** capacity, distortion, recovery, and detectability under explicit experimental conditions.

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
- **A `robust` method for WhatsApp photos** (`src/robust.py`): the cover is pre-shaped to
  what the WhatsApp iPhone app sends (long side at most 1,280 px, whole 16 px blocks, a
  standard quality-75 JPEG), and the sealed blob goes into luma DCT coefficients by
  quantisation index modulation, behind a repeated length header and interleaved
  Reed-Solomon codes. The output is a JPEG, and the image and password are all extraction
  needs.
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

- DWT embedding, or error correction for the two LSB methods.
- Adaptive (content-aware) embedding.
- A learned (machine-learned) steganalysis classifier; the detectors here are the classical
  structural and histogram ones.
- Survival under lossy transformations other than the one measured channel below.
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
- Recovery for the LSB methods is exact only on the lossless PNG carrier; JPEG, noise,
  cropping and resizing destroy the payload.

### The `robust` method through WhatsApp

A PNG sent as a WhatsApp photo comes back as a JPEG and the LSB payload is gone. The
`robust` method was built for that route under a protocol written and frozen before the
test ([`docs/robust_protocol.md`](docs/robust_protocol.md), hashes in
[`docs/robust_protocol.sha1`](docs/robust_protocol.sha1)). Development used ten images and
a simulated channel to choose the parameters, then two real confirmations; the final test
used 30 of the author's own iPhone photos (15 smooth, 15 textured) drawn by a fixed seed,
each with a 140-byte message, each sent once.

The channel: Mac to iPhone by AirDrop, sent as a standard-quality photo through the
WhatsApp iPhone app, saved and AirDropped back. iPhone 16 Pro, iOS 27.0.1, WhatsApp
2.26.45.75, November 2026.

| Measure | Result |
| --- | --- |
| Messages recovered exactly | 30 of 30 (smooth 15, textured 15) |
| Lower bound on the recovery rate, one-sided 95% | 90.5% |
| Bit error rate before error correction | 0.07% |
| PSNR / SSIM of stego against cover, luma, worst cover | 50.4 dB / 0.993 |
| PSNR of the pre-shaped cover against the resized original, worst cover | 34.6 dB |
| Message capacity per photo | 9,976 to 17,872 bytes (median 13,360) |
| Share of embedded bits that is header or Reed-Solomon parity | 53% |

What the test found along the way: WhatsApp's quantisation table depends on the image it
is given. The first configuration chosen in simulation (QIM step 2) failed all ten real
confirmation sends, because WhatsApp re-encoded those inputs with a finer table than the
standard quality-75 one. The next configuration in the frozen order (step 6) passed and
was the one tested. Repeat sends of the same file came back byte-identical.

The result holds for that route and those versions only. Android, HD mode, other apps and
later WhatsApp versions are not measured. The detectors in this repository are built for
LSB methods and say little about JPEG-domain embedding, so nothing here claims the
`robust` method is hard to detect. Results and per-cover figures are in
[`docs/robust/`](docs/robust/); the test photos are not published.

## Evaluation-first workflow

1. Select a cover image and payload.
2. Encrypt the payload with AES-GCM using a scrypt-derived key.
3. Embed the ciphertext with either method.
4. Verify exact round-trip recovery.
5. Measure distortion and capacity utilisation.
6. Run the detectors on cover and stego.
7. Apply controlled transformations and record recovery success and BER instead of assuming robustness.

See [`ROADMAP.md`](ROADMAP.md) for the remaining milestones: more channels for the `robust` method, a JPEG-domain detector, and a learned steganalysis classifier.

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

For WhatsApp, the `robust` method takes any image and writes a JPEG
(`pip install -e '.[robust]'`):

```python
from src.robust import Config, seal, open_robust

cfg = Config(Z=9, k=6, m=159)   # the tested configuration
seal("photo.png", "meet at the station", "research-passphrase", "stego.jpg", cfg)
open_robust("received.jpg", "research-passphrase", cfg)   # "meet at the station"
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
src/robust*.py        the robust method, its development run, pool draw and test scoring
web/service/          FastAPI service behind the live preview
web/dashboard/        React preview page, embeddable in mdingi.co.za
deploy/               Azure App Service deployment script
tests/                automated test suite
.github/workflows/     continuous integration
docs/benchmarks/       benchmark results (JSON, CSV) and notes
docs/robust_protocol.md  the robust method's protocol; results in docs/robust/
docs/releases/         versioned release notes
ROADMAP.md             planned research milestones
```

## Security and ethics

The repository is scoped to offline image-steganography research, defensive evaluation, and reproducibility. It is not intended for malware delivery, credential theft, covert persistence, command-and-control, or operational surveillance evasion. Review the threat model and security policy before interpreting results.

## Licence

Copyright 2026 Sbusiso Mdingi.

Licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
