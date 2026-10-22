# Threat Model: v0.4

## Scope

This threat model covers the local creation, storage, transformation, and extraction of encrypted payloads embedded in images. It does not model network transport, anonymous communication, endpoint compromise, or production key management.

## Assets

- plaintext message;
- user password;
- derived encryption key;
- encrypted embedded payload;
- integrity/authenticity of decrypted plaintext.

The salt and scrypt parameters are intentionally non-secret. Since v0.4 they travel inside the embedded blob instead of a metadata file. The presence of a message is something the toolkit tries to hide but does not claim to protect.

## Adversary capabilities

An evaluator/adversary may obtain the stego image (and, for the v0.2 path, its metadata), inspect source code, modify image bytes, apply lossy transformations, and attempt offline password guessing. The adversary is assumed not to have the user's password or direct access to the process memory holding the derived key.

## Controls

- AES-256-GCM provides authenticated encryption of the message payload.
- A memory-hard scrypt KDF raises the cost of password guessing relative to direct password use.
- Fresh random salts prevent precomputed key reuse across packages.
- Fresh AES-GCM nonces prevent nonce reuse under normal operation.
- Length-prefixed framing avoids delimiter ambiguity and rejects structurally invalid payload lengths.
- Random padding to a chosen share of capacity hides the message length from the payload size.
- Keyed LSB matching at key-seeded positions removes the pairs-of-values signature that chi-square and RS analysis detect, and the position key is derived with scrypt so it costs as much to guess as the encryption key.

## Important limitations

- Password strength remains critical; scrypt does not make weak passwords strong.
- LSB embedding is fragile under many transformations and is not assumed to be undetectable.
- The scrypt parameters in the blob (or the v0.2 metadata) are not separately signed; tampering causes decryption failure, and the log2 n field is bounded to 10..20 to cap KDF work.
- The position key uses a fixed public salt, so an attacker can precompute position keys for common passwords across all images. This weakens hiding, not confidentiality, which rests on the random-salted encryption key.
- Keyed matching is still detectable: HCF-COM moves with payload size, learned classifiers are stronger, and saturated image regions (values at 0 or 255) behave like replacement.
- The web preview receives messages and passwords over HTTPS and processes them in memory; anyone using it trusts the operator. It is a demonstration, not a messaging service.
- Endpoint compromise, keylogging, memory inspection, and social engineering are out of scope.
- The project does not claim security against advanced targeted steganalysis or a warden who compares the stego image with its cover.
