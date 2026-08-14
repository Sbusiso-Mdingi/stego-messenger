# Architecture — v0.2

Stego Messenger is structured as an **offline experimental pipeline**. It does not provide transport, identity, key exchange, or a production messaging protocol.

## Embed path

1. Generate a 16-byte random salt.
2. Derive a 256-bit key from the user password with scrypt.
3. Encrypt UTF-8 plaintext with AES-256-GCM using a fresh 96-bit nonce and fixed versioned associated data.
4. Frame the encrypted payload with a 32-bit big-endian length header.
5. Embed the frame sequentially in RGB least-significant bits.
6. Save the stego image as PNG to avoid accidental lossy destruction of LSBs.
7. Store non-secret KDF parameters and salt in a versioned JSON metadata file.

## Extract path

1. Parse the 32-bit payload length.
2. Reject lengths that are zero or exceed image capacity.
3. Recover the encrypted payload.
4. Load KDF parameters and salt from metadata.
5. Re-derive the key from the supplied password.
6. Authenticate and decrypt with AES-GCM. Modified ciphertext or the wrong key fails authentication.

## Evaluation path

The evaluation module treats robustness as an empirical result. It measures exact round-trip recovery, BER, MSE, PSNR, capacity utilisation, and descriptive LSB-plane statistics. Controlled transformations are applied with explicit parameters and recovery is attempted after each transformation.

## Boundaries

- LSB is a baseline algorithm, not a claim of state-of-the-art steganography.
- The current LSB diagnostics are heuristics, not a trained/calibrated detector.
- The current release makes no claim that payloads survive JPEG compression, resizing, cropping, or noise.
- DCT/DWT methods and error correction remain roadmap items.
