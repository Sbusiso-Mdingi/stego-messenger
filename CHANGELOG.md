# Changelog

All notable changes are documented here.

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
