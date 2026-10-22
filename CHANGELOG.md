# Changelog

All notable changes are documented here.

## [0.4.0] - 2026-10-22

### Added
- Keyed LSB matching (`method="keyed"` in `src/lsb_stego.py`): each payload bit changes a
  value by a random +1 or -1 where needed, at positions drawn from a key-seeded
  permutation, instead of overwriting LSBs in raster order. Sequential replacement stays
  available as the baseline.
- Self-contained stego images (`src/package.py`): `seal` and `open_package` carry the
  format version, scrypt parameters and salt inside the embedded blob, so a PNG and a
  password are all that is needed. Random padding fills a chosen share of capacity, so the
  payload size does not reveal the message length.
- Calibrated HCF centre-of-mass detector (`hcf_com_calibrated` in `src/steganalysis.py`,
  after Harmsen and Pearlman 2003 and Ker 2005), which targets LSB matching.
- The benchmark sweeps both methods (`--methods`) and records the HCF-COM ratio and its
  shift from the cover.
- A web preview (`web/`): a FastAPI service and a React page that hide a message with both
  methods, run all three detectors on the results and read messages back. Packaged with
  the `Dockerfile` and deployed by `deploy/azure.sh`.
- Tests for the keyed method, the package format and the web service.

### Changed
- `seal` defaults to the keyed method.
- Benchmark results are grouped per method under `summary` (was `summary_by_fraction`).
- The Streamlit UI (`ui/`) is replaced by the web preview; the `ui` extra becomes `web`.

### Measured
- RS analysis reads 0.25 for sequential replacement at a 25% payload and 0.044 for keyed
  matching, against 0.028 for clean covers. At 90% the figures are 0.83 and 0.068.
- HCF-COM moves with keyed embedding (a shift of -0.148 at 90%), so keyed matching
  defeats the two replacement detectors without being undetectable. On images with many
  saturated values (astronaut) RS still rises with keyed embedding.

## [0.3.0] - 2026-10-13

### Added
- Calibrated steganalysis detectors in `src/steganalysis.py`: the Westfeld-Pfitzmann
  chi-square attack and Fridrich-Goljan-Du RS analysis, which estimates the LSB embedding
  rate. RS flags its singular point near a saturated LSB plane as unreliable.
- SSIM distortion metric (`src/evaluation.py: ssim`), via scikit-image.
- `evaluate_embedding` now reports SSIM and the detectability of both cover and stego.
- Reproducible benchmark (`src/benchmark.py`, `stego-benchmark` entry point): payload-size
  sweeps across a public-domain image corpus over several seeds, with confidence intervals,
  exported as JSON and CSV with full environment metadata. Results in `docs/benchmarks/`.
- Tests for the detectors and the benchmark.

### Changed
- `scikit-image` is now a runtime dependency (SSIM and the benchmark corpus).

### Measured
- At a 10% payload the stego image is 61 dB (SSIM 0.9996) from its cover yet RS analysis
  recovers an embedding rate of 0.12, cleanly separated from a clean cover at 0.03. The
  embedding is visually invisible but statistically detectable.

## [0.2.0] - 2026-08-14

### Added
- Apache-2.0 licence, contribution guidance, security policy, code of conduct, roadmap, citation metadata, and CI.
- Reproducible embedding metrics: MSE, PSNR, BER, capacity utilisation, and LSB diagnostics.
- Deterministic attack evaluation helpers for JPEG compression, noise, cropping, and resizing.
- Automated pytest coverage for cryptography, framing, capacity validation, and evaluation metrics.

### Changed
- Repositioned the project as an evaluation-oriented research toolkit rather than a production covert messenger.
- Replaced Fernet/PBKDF2 with AES-256-GCM and scrypt.
- Replaced delimiter-based LSB framing with a length-prefixed binary format.
- Corrected Gaussian noise handling and made attack parameters reproducible.

### Removed
- Claims of implemented DCT support and transformation resilience that were not supported by the code.

### Breaking changes
- v0.1 metadata and embedded payloads are not compatible with the v0.2 cryptographic/framing format.
