# Threat Model — v0.2

## Scope

This threat model covers the local creation, storage, transformation, and extraction of encrypted payloads embedded in images. It does not model network transport, anonymous communication, endpoint compromise, or production key management.

## Assets

- plaintext message;
- user password;
- derived encryption key;
- encrypted embedded payload;
- integrity/authenticity of decrypted plaintext.

The salt and scrypt parameters in metadata are intentionally non-secret.

## Adversary capabilities

An evaluator/adversary may obtain the stego image and metadata, inspect source code, modify image bytes, apply lossy transformations, and attempt offline password guessing. The adversary is assumed not to have the user's password or direct access to the process memory holding the derived key.

## Controls

- AES-256-GCM provides authenticated encryption of the message payload.
- A memory-hard scrypt KDF raises the cost of password guessing relative to direct password use.
- Fresh random salts prevent precomputed key reuse across packages.
- Fresh AES-GCM nonces prevent nonce reuse under normal operation.
- Length-prefixed framing avoids delimiter ambiguity and rejects structurally invalid payload lengths.

## Important limitations

- Password strength remains critical; scrypt does not make weak passwords strong.
- LSB embedding is fragile under many transformations and is not assumed to be undetectable.
- Metadata authenticity is not separately signed; malicious metadata primarily causes decryption failure or increased KDF work.
- Endpoint compromise, keylogging, memory inspection, and social engineering are out of scope.
- The project does not claim security against advanced targeted steganalysis.
