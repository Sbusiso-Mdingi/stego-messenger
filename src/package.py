# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Self-contained stego images: one PNG and a password, no separate metadata file.

The embedded blob carries everything decryption needs except the password::

    version (1) | log2 scrypt n (1) | scrypt r (1) | scrypt p (1) | salt (16) | AES-GCM token

The AES-GCM plaintext is ``message length (4) | UTF-8 message | random padding``. Padding
lets a short message fill a chosen share of the image's capacity, so the payload size
does not reveal the message length, and it is what the benchmark sweeps.

For the keyed method the embedding positions come from a second scrypt derivation of the
password with a fixed, public salt, because the random salt is itself inside the
embedded blob. The positions only spread the changes across the image; confidentiality
rests on AES-256-GCM with the random-salted key.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

from cryptography.exceptions import InvalidTag

from .crypto_utils import (
    DEFAULT_SCRYPT_N,
    DEFAULT_SCRYPT_P,
    DEFAULT_SCRYPT_R,
    SALT_SIZE,
    decrypt_bytes,
    derive_key_from_password,
    encrypt_bytes,
)
from .lsb_stego import METHODS, capacity_bytes, embed_data, extract_data

FORMAT_VERSION = 3
POSITION_SALT = b"stego-messenger:positions:v3"
_PREFIX = struct.Struct(">BBBB")
# Blob bytes around the message: prefix, salt, AES-GCM nonce and tag, message length.
OVERHEAD = _PREFIX.size + SALT_SIZE + 12 + 16 + 4


def position_key(password: str) -> bytes:
    """Key that seeds the keyed method's embedding positions."""
    return derive_key_from_password(password, POSITION_SALT)


def max_message_bytes(cover_path: str | Path) -> int:
    """Largest UTF-8 message that fits in the cover."""
    return max(0, capacity_bytes(cover_path) - OVERHEAD)


def seal(
    cover_path: str | Path,
    message: str,
    password: str,
    output_path: str | Path,
    *,
    method: str = "keyed",
    fill: float = 0.0,
) -> dict[str, int | float | str]:
    """Encrypt ``message`` and embed it, padded to ``fill`` (0 to 1) of capacity."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if not 0.0 <= fill <= 1.0:
        raise ValueError("fill must be between 0 and 1")
    text = message.encode("utf-8")
    capacity = capacity_bytes(cover_path)
    room = capacity - OVERHEAD
    if len(text) > room:
        raise ValueError(f"message is {len(text)} bytes but this image holds at most {max(0, room)}")
    padding = max(0, min(room, round(capacity * fill) - OVERHEAD) - len(text))

    salt = os.urandom(SALT_SIZE)
    key = derive_key_from_password(password, salt)
    plaintext = len(text).to_bytes(4, "big") + text + os.urandom(padding)
    log_n = DEFAULT_SCRYPT_N.bit_length() - 1
    blob = (
        _PREFIX.pack(FORMAT_VERSION, log_n, DEFAULT_SCRYPT_R, DEFAULT_SCRYPT_P)
        + salt
        + encrypt_bytes(plaintext, key)
    )
    embed_data(
        cover_path,
        blob,
        output_path,
        method=method,
        key=position_key(password) if method == "keyed" else None,
    )
    return {
        "method": method,
        "message_bytes": len(text),
        "payload_bytes": len(blob),
        "capacity_bytes": capacity,
        "capacity_utilization": len(blob) / capacity if capacity else 0.0,
    }


def open_package(stego_path: str | Path, password: str) -> tuple[str, str]:
    """Recover ``(message, method)``. Tries the keyed layout first, then sequential.

    A wrong password or an image without a payload raises ``ValueError``; AES-GCM
    authentication makes a false recovery practically impossible.
    """
    for method in ("keyed", "sequential"):
        key = position_key(password) if method == "keyed" else None
        try:
            blob = extract_data(stego_path, method=method, key=key)
            return _open_blob(blob, password), method
        except ValueError:
            continue
    raise ValueError("no message found for this password")


def _open_blob(blob: bytes, password: str) -> str:
    if len(blob) < OVERHEAD:
        raise ValueError("payload is too short")
    version, log_n, r, p = _PREFIX.unpack_from(blob)
    if version != FORMAT_VERSION or not 10 <= log_n <= 20:
        raise ValueError("unsupported payload format")
    salt = blob[_PREFIX.size : _PREFIX.size + SALT_SIZE]
    key = derive_key_from_password(password, salt, n=2**log_n, r=r, p=p)
    try:
        plaintext = decrypt_bytes(blob[_PREFIX.size + SALT_SIZE :], key)
    except InvalidTag:
        raise ValueError("wrong password or damaged image") from None
    length = int.from_bytes(plaintext[:4], "big")
    if length > len(plaintext) - 4:
        raise ValueError("payload length is invalid")
    return plaintext[4 : 4 + length].decode("utf-8")
