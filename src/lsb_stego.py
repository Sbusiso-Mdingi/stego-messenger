# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Length-prefixed least-significant-bit image steganography."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HEADER_BYTES = 4


def _load_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()


def capacity_bytes(image_path: str | Path) -> int:
    """Return maximum payload bytes after the 32-bit length header."""
    arr = _load_rgb(image_path)
    return max(0, arr.size // 8 - HEADER_BYTES)


def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    usable = bits[: (len(bits) // 8) * 8]
    return np.packbits(usable).tobytes()


def embed_data(image_path: str | Path, data: bytes, output_path: str | Path) -> None:
    """Embed bytes in RGB channel LSBs and write a lossless PNG."""
    max_capacity = capacity_bytes(image_path)
    if len(data) > max_capacity:
        raise ValueError(f"payload is {len(data)} bytes but image capacity is {max_capacity} bytes")

    arr = _load_rgb(image_path)
    framed = len(data).to_bytes(HEADER_BYTES, "big") + data
    bits = _bytes_to_bits(framed)
    flat = arr.reshape(-1)
    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
    Image.fromarray(arr, mode="RGB").save(output_path, format="PNG")


def extract_data(image_path: str | Path) -> bytes:
    """Extract one length-prefixed payload from an LSB stego image."""
    arr = _load_rgb(image_path)
    flat = arr.reshape(-1)
    header_bits = flat[: HEADER_BYTES * 8] & 1
    payload_length = int.from_bytes(_bits_to_bytes(header_bits), "big")
    max_payload = max(0, flat.size // 8 - HEADER_BYTES)

    if payload_length <= 0 or payload_length > max_payload:
        raise ValueError("no valid length-prefixed payload found")

    total_bits = (HEADER_BYTES + payload_length) * 8
    payload_bits = flat[HEADER_BYTES * 8 : total_bits] & 1
    payload = _bits_to_bytes(payload_bits)
    if len(payload) != payload_length:
        raise ValueError("embedded payload is truncated")
    return payload
