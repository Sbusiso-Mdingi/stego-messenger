# Changelog

All notable changes are documented here.

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
