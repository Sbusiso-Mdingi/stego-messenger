# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Length-prefixed least-significant-bit image steganography.

Two embedding methods share one framing (a 32-bit big-endian length, then the payload):

* ``sequential`` (the baseline) writes bits by LSB *replacement* into the first channel
  values of the image, in raster order. It is simple and exactly what the classical
  chi-square and RS detectors were designed to catch.
* ``keyed`` writes bits by LSB *matching* (a random +1 or -1 change wherever the LSB
  disagrees) at channel values chosen by a key-seeded permutation, so the changes are
  scattered across the whole image. LSB matching does not create the pairs-of-values
  symmetry that chi-square and RS measure. It is still detectable by other methods; see
  ``src/steganalysis.py`` and ``docs/benchmarks``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

HEADER_BYTES = 4
METHODS = ("sequential", "keyed")


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


def _check(method: str, key: bytes | None) -> None:
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if method == "keyed" and not key:
        raise ValueError("the keyed method needs a key")


def _positions(size: int, method: str, key: bytes | None) -> np.ndarray:
    """Channel-value order in which bits are written: raster, or a key-seeded permutation."""
    if method == "sequential":
        return np.arange(size)
    digest = hashlib.sha256(b"stego-messenger:positions:" + key).digest()
    rng = np.random.default_rng(np.frombuffer(digest, dtype=np.uint32))
    return rng.permutation(size)


def embed_data(
    image_path: str | Path,
    data: bytes,
    output_path: str | Path,
    *,
    method: str = "sequential",
    key: bytes | None = None,
    seed: int | None = None,
) -> None:
    """Embed bytes in RGB channel LSBs and write a lossless PNG.

    ``key`` selects the positions for the keyed method. ``seed`` only fixes the +1/-1
    choices of LSB matching, for reproducible benchmarks; it does not affect extraction.
    """
    _check(method, key)
    max_capacity = capacity_bytes(image_path)
    if len(data) > max_capacity:
        raise ValueError(f"payload is {len(data)} bytes but image capacity is {max_capacity} bytes")

    arr = _load_rgb(image_path)
    framed = len(data).to_bytes(HEADER_BYTES, "big") + data
    bits = _bytes_to_bits(framed)
    flat = arr.reshape(-1)
    where = _positions(flat.size, method, key)[: len(bits)]

    if method == "sequential":
        flat[where] = (flat[where] & 0xFE) | bits
    else:
        values = flat[where].astype(np.int16)
        step = np.random.default_rng(seed).choice(np.array([-1, 1], dtype=np.int16), len(bits))
        step[values == 0] = 1
        step[values == 255] = -1
        change = (values & 1) != bits
        flat[where] = np.where(change, values + step, values).astype(np.uint8)
    Image.fromarray(arr, mode="RGB").save(output_path, format="PNG")


def extract_data(
    image_path: str | Path,
    *,
    method: str = "sequential",
    key: bytes | None = None,
) -> bytes:
    """Extract one length-prefixed payload from an LSB stego image."""
    _check(method, key)
    arr = _load_rgb(image_path)
    flat = arr.reshape(-1)
    order = _positions(flat.size, method, key)
    header_bits = flat[order[: HEADER_BYTES * 8]] & 1
    payload_length = int.from_bytes(_bits_to_bytes(header_bits), "big")
    max_payload = max(0, flat.size // 8 - HEADER_BYTES)

    if payload_length <= 0 or payload_length > max_payload:
        raise ValueError("no valid length-prefixed payload found")

    total_bits = (HEADER_BYTES + payload_length) * 8
    payload_bits = flat[order[HEADER_BYTES * 8 : total_bits]] & 1
    payload = _bits_to_bytes(payload_bits)
    if len(payload) != payload_length:
        raise ValueError("embedded payload is truncated")
    return payload
