# Security Controls — v0.2

## Cryptographic controls

- AES-256-GCM authenticated encryption.
- 96-bit random nonce per encryption.
- 128-bit random salt per package.
- scrypt password-based key derivation with versioned parameters.
- Versioned associated data (`stego-messenger:v2`) binds ciphertext to the payload format generation.

## Input and framing controls

- Empty passwords are rejected by the KDF helper.
- Payload size is checked before embedding.
- Payloads use a fixed-width length header instead of sentinel delimiters.
- Extraction rejects impossible or truncated payload lengths.
- Stego output is forced to PNG to prevent accidental lossy encoding at the embedding step.

## Evaluation controls

- Gaussian-noise experiments accept an explicit seed for reproducibility.
- Transformation failures are recorded as failures rather than reclassified as successful partial recovery.
- LSB statistics are labelled as diagnostics rather than probabilities or detection guarantees.

## Software-quality controls

- Automated pytest suite.
- GitHub Actions on pull requests and `main`.
- Ruff static checks.
- Public security reporting policy and explicit research scope.

## Remaining risks

See `ROADMAP.md` and `threat_model.md`. In particular, v0.2 does not provide error correction, robust transform-domain embedding, a calibrated steganalysis model, secure network transport, or formal cryptographic verification.
