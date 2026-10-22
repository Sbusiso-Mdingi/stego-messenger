# Security Controls: v0.4

## Cryptographic controls

- AES-256-GCM authenticated encryption.
- 96-bit random nonce per encryption.
- 128-bit random salt per package.
- scrypt password-based key derivation with versioned parameters.
- Versioned associated data (`stego-messenger:v2`) binds ciphertext to the payload format generation.
- Self-contained package format (version 3) with a format version byte and bounded scrypt parameters.
- Random padding hides the message length; a separate scrypt-derived key seeds keyed embedding positions.

## Input and framing controls

- Empty passwords are rejected by the KDF helper.
- Payload size is checked before embedding.
- Payloads use a fixed-width length header instead of sentinel delimiters.
- Extraction rejects impossible or truncated payload lengths.
- The keyed method refuses to run without a key.
- Stego output is forced to PNG to prevent accidental lossy encoding at the embedding step.

## Evaluation controls

- Gaussian-noise experiments accept an explicit seed for reproducibility.
- Transformation failures are recorded as failures rather than reclassified as successful partial recovery.
- LSB statistics are labelled as diagnostics rather than probabilities or detection guarantees.
- Three calibrated detectors (chi-square, RS, HCF-COM) are reported for every embedding, including the detector that targets the default method.

## Web preview controls

- No storage: each request uses a temporary directory deleted before the response.
- Uploads are capped at 8 MB, decoded with Pillow and scaled to 640 pixels; message and password lengths are bounded.
- At most two CPU-heavy jobs run at once; others wait briefly, then get a 503.
- `Content-Security-Policy: frame-ancestors` and CORS allow only the portfolio origins and localhost; responses from `/api` are `no-store`.
- The container runs as an unprivileged user.

## Software-quality controls

- Automated pytest suite.
- GitHub Actions on pull requests and `main`.
- Ruff static checks.
- Public security reporting policy and explicit research scope.

## Remaining risks

See `ROADMAP.md` and `threat_model.md`. In particular, v0.4 does not provide error correction, robust transform-domain embedding, a learned steganalysis model, secure network transport, or formal cryptographic verification.
