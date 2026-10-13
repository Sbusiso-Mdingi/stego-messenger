# Roadmap

## v0.2 — Evaluation framework foundation

- [x] Apache-2.0 licensing and OSS governance files
- [x] Replace delimiter framing with a length-prefixed payload format
- [x] Move cryptography to AES-256-GCM with scrypt-derived keys
- [x] Add deterministic transformation attacks
- [x] Add PSNR, MSE, BER, capacity utilisation, and transparent LSB diagnostics
- [x] Add automated tests and CI
- [x] Document measured-vs-planned claims

## v0.3 — Reproducible benchmark suite

- [x] Add a public image corpus (scikit-image samples) and benchmark CLI (`src/benchmark.py`)
- [x] Add SSIM via scikit-image (`src/evaluation.py: ssim`)
- [x] Export benchmark results as JSON/CSV with environment metadata
- [x] Add payload-size sweeps and confidence intervals over seeds
- [x] Add calibrated steganalysis detectors (chi-square and RS analysis) and report
      detectability alongside distortion
- [ ] Add a baseline comparison against at least one external steganography library

## v0.4 — Robust embedding experiments

- [ ] Implement a documented transform-domain baseline (DCT or DWT)
- [ ] Add error-correcting codes and quantify capacity/robustness trade-offs
- [ ] Add a learned steganalysis classifier on labelled cover/stego datasets, calibrated
      against the structural detectors already implemented
- [ ] Publish reproducible experiment notebooks/reports

## Non-goals

This project will not become a covert command-and-control framework, malware delivery mechanism, surveillance-evasion product, or production messaging service.
