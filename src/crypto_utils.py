# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Authenticated encryption and password-based key derivation."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
DEFAULT_SCRYPT_N = 2**14
DEFAULT_SCRYPT_R = 8
DEFAULT_SCRYPT_P = 1
AAD = b"stego-messenger:v2"


def generate_salt(length: int = SALT_SIZE) -> bytes:
    if length < 16:
        raise ValueError("salt length must be at least 16 bytes")
    return os.urandom(length)


def derive_key_from_password(
    password: str | bytes,
    salt: bytes,
    *,
    n: int = DEFAULT_SCRYPT_N,
    r: int = DEFAULT_SCRYPT_R,
    p: int = DEFAULT_SCRYPT_P,
) -> bytes:
    """Derive a 256-bit key using scrypt."""
    if not password:
        raise ValueError("password must not be empty")
    password_bytes = password.encode("utf-8") if isinstance(password, str) else password
    kdf = Scrypt(salt=salt, length=KEY_SIZE, n=n, r=r, p=p)
    return kdf.derive(password_bytes)


def encrypt_message(message: str, key: bytes) -> bytes:
    """Encrypt UTF-8 text with AES-256-GCM; returned bytes are nonce || ciphertext."""
    if len(key) != KEY_SIZE:
        raise ValueError("AES-GCM key must be 32 bytes")
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, message.encode("utf-8"), AAD)
    return nonce + ciphertext


def decrypt_message(token: bytes, key: bytes) -> str:
    """Decrypt a nonce-prefixed AES-GCM token."""
    if len(key) != KEY_SIZE:
        raise ValueError("AES-GCM key must be 32 bytes")
    if len(token) <= NONCE_SIZE:
        raise ValueError("encrypted payload is too short")
    nonce, ciphertext = token[:NONCE_SIZE], token[NONCE_SIZE:]
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
    return plaintext.decode("utf-8")
