# Architecture: v0.4

Stego Messenger is an **offline experimental pipeline** with a web preview on top. It does not provide transport, identity, key exchange, or a production messaging protocol.

## Embed path (`src/package.py: seal`)

1. Generate a 16-byte random salt and derive a 256-bit key from the password with scrypt.
2. Build the plaintext `message length (4) | UTF-8 message | random padding`. Padding fills a chosen share of the image's capacity, so the payload size does not reveal the message length.
3. Encrypt with AES-256-GCM using a fresh 96-bit nonce and versioned associated data.
4. Prefix the token with `version (1) | log2 scrypt n (1) | r (1) | p (1) | salt (16)`, so the image carries everything except the password.
5. Frame the blob with a 32-bit big-endian length header and embed it with one of two methods:
   - **sequential**: LSB replacement in raster order (the baseline);
   - **keyed** (default): LSB matching, changing a value by a random +1 or -1 where its LSB differs from the bit, at positions from a permutation seeded by a second scrypt derivation of the password with a fixed public salt. At 0 the change is always +1 and at 255 always -1.
6. Save the stego image as PNG to avoid lossy destruction of LSBs.

## Extract path (`open_package`)

1. Try the keyed layout, then the sequential one: read the 32-bit length, reject zero or over-capacity lengths, and recover the blob.
2. Check the format version and the scrypt parameter range, then re-derive the key from the salt in the blob.
3. Authenticate and decrypt with AES-GCM. A wrong password, a damaged image or an image without a payload fails authentication and is reported as "no message found".

The v0.2 low-level path (`encrypt_message`, `embed_data`, JSON metadata in `src/metadata.py`) remains available.

## Evaluation path

`src/evaluation.py` and `src/benchmark.py` measure exact recovery, BER, MSE, PSNR, SSIM and capacity utilisation, and run three detectors from `src/steganalysis.py`: the chi-square attack and RS analysis, which target LSB replacement, and calibrated HCF-COM, which targets LSB matching. Controlled transformations in `src/attacks.py` are applied with explicit parameters. Results are in `docs/benchmarks/`.

## Web preview (`web/`)

A FastAPI service (`web/service/main.py`) hides a message with both methods, runs the detectors on the cover and both results, and returns the images, change maps and readings. It works in a per-request temporary directory, stores nothing, caps uploads at 8 MB and scales them to 640 pixels, and limits concurrent jobs to two. A React page (`web/dashboard/`) presents the comparison and can be embedded in an iframe on the allowed origins.

## Boundaries

- LSB embedding is a baseline, not a claim of state-of-the-art steganography.
- Keyed matching defeats the replacement detectors in the benchmark; it is not undetectable.
- No claim is made that payloads survive JPEG compression, resizing, cropping, or noise.
- DCT/DWT methods and error correction remain roadmap items.
