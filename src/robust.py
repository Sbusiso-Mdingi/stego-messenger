# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""The ``robust`` method: a sealed blob that survives a WhatsApp standard-quality photo.

Follows ``docs/robust_protocol.md``. The cover is pre-shaped to what the WhatsApp iPhone app
sends (long side at most 1,280 px, whole 16 px blocks, a standard quality-75 4:2:0 JPEG), so the
app's own re-encode lands on nearly the same quantised coefficients. Bits go into luma AC
coefficients at zigzag indices 1 to ``Z`` by dither modulation with an even step ``k``, in an
order keyed by the password, behind a 7-times repeated length header and interleaved
Reed-Solomon RS(255, ``m``) codewords. AES-GCM in the blob decides whether a recovery is right.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import jpeglib
import numpy as np
from PIL import Image, ImageOps
from reedsolo import ReedSolomonError, RSCodec

from .package import make_blob, open_blob, position_key

LONG_SIDE = 1280
QUALITY = 75
HEADER_BITS = 32
HEADER_REPEAT = 7
# Zigzag scan order of an 8x8 block, as row-major indices.
ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7,
    14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39,
    46, 53, 60, 61, 54, 47, 55, 62, 63,
])


@dataclass(frozen=True)
class Config:
    """Highest zigzag index used ``Z``, even QIM step ``k`` and RS data bytes ``m``."""

    Z: int
    k: int
    m: int

    def __post_init__(self):
        if not 1 <= self.Z <= 63 or self.k < 2 or self.k % 2 or not 1 <= self.m < 255:
            raise ValueError(f"invalid robust config {self}")

    @property
    def nsym(self) -> int:
        return 255 - self.m


# --- the cover --------------------------------------------------------------------------------

def preshape(path: str | Path) -> np.ndarray:
    """RGB pixels resized to a long side of at most 1,280 px and cropped to whole 16 px blocks."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        if max(w, h) > LONG_SIDE:
            s = LONG_SIDE / max(w, h)
            im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
            w, h = im.size
        w16, h16 = w // 16 * 16, h // 16 * 16
        left, top = (w - w16) // 2, (h - h16) // 2
        return np.asarray(im.crop((left, top, left + w16, top + h16)))


def write_cover(rgb: np.ndarray, path: str | Path) -> None:
    """Baseline JPEG with the standard quality-75 tables and 4:2:0 (libjpeg's default)."""
    jpeglib.from_spatial(np.ascontiguousarray(rgb)).write_spatial(str(path), qt=QUALITY)


def reference_table() -> np.ndarray:
    """The standard quality-75 luma table the method works in."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "q.jpg")
        write_cover(np.zeros((16, 16, 3), np.uint8), p)
        j = jpeglib.read_dct(p)
        return j.qt[j.quant_tbl_no[0]].astype(float)


_QT75 = reference_table()


# --- positions and modulation -----------------------------------------------------------------

def _order(password: str, n: int) -> np.ndarray:
    seed = np.frombuffer(position_key(password), dtype="<u4")
    return np.random.default_rng(seed).permutation(n)


def _slots(cfg: Config) -> np.ndarray:
    return ZIGZAG[1 : cfg.Z + 1]


def capacity(blocks: int, cfg: Config) -> int:
    """Largest blob in bytes after the header and all Reed-Solomon parity."""
    coded = (blocks * cfg.Z - HEADER_BITS * HEADER_REPEAT) // 8
    full, rest = divmod(max(coded, 0), 255)
    return full * cfg.m + max(0, rest - cfg.nsym)


def _round_half_to_zero(x: np.ndarray) -> np.ndarray:
    return np.sign(x) * np.ceil(np.abs(x) - 0.5)


def qim_embed(c: np.ndarray, bits: np.ndarray, k: int) -> np.ndarray:
    """Move each whole-number coefficient to the nearest value of ``bit * k/2`` modulo ``k``.

    Ties go to the value nearer zero; when both are equally near zero (0 between -1 and 1 at
    ``k`` = 2, for example), to the positive one.
    """
    c = c.astype(np.int64)
    r = np.mod(c - bits * (k // 2), k)
    down, up = c - r, c - r + k
    pick_up = (k - r < r) | ((k - r == r) & ((np.abs(up) < np.abs(down)) | (up == -down)))
    return np.where(pick_up, up, down)


def qim_extract(c: np.ndarray, k: int) -> np.ndarray:
    """Nearest point of the combined lattice (step ``k/2``), ties toward zero, as a bit."""
    return np.mod(_round_half_to_zero(c / (k // 2)), 2).astype(np.uint8)


# --- framing ----------------------------------------------------------------------------------

def _interleave(coded: bytes) -> bytes:
    cws = [coded[i : i + 255] for i in range(0, len(coded), 255)]
    return bytes(cw[j] for j in range(255) for cw in cws if j < len(cw))


def _deinterleave(data: bytes) -> bytes:
    lengths = [min(255, len(data) - i) for i in range(0, len(data), 255)]
    cws = [bytearray() for _ in lengths]
    it = iter(data)
    for j in range(255):
        for cw, n in zip(cws, lengths):
            if j < n:
                cw.append(next(it))
    return b"".join(cws)


def frame(blob: bytes, cfg: Config) -> np.ndarray:
    """Header bits then interleaved codeword bits, in embedding order."""
    coded = bytes(RSCodec(cfg.nsym, nsize=255).encode(blob))
    header = np.unpackbits(np.frombuffer(len(coded).to_bytes(4, "big"), np.uint8))
    body = np.unpackbits(np.frombuffer(_interleave(coded), np.uint8))
    return np.concatenate([np.repeat(header, HEADER_REPEAT), body])


def unframe(bits: np.ndarray, cfg: Config, slots: int) -> bytes:
    """Blob from read bits, or ``ValueError``. ``slots`` is the number of positions read."""
    h = HEADER_BITS * HEADER_REPEAT
    votes = bits[:h].reshape(HEADER_BITS, HEADER_REPEAT).sum(axis=1) > HEADER_REPEAT // 2
    length = int.from_bytes(np.packbits(votes.astype(np.uint8)).tobytes(), "big")
    last = length % 255
    if length == 0 or 8 * length > slots - h or (last and last <= cfg.nsym):
        raise ValueError("no robust payload found")
    coded = _deinterleave(np.packbits(bits[h : h + 8 * length]).tobytes())
    try:
        return bytes(RSCodec(cfg.nsym, nsize=255).decode(coded)[0])
    except ReedSolomonError:
        raise ValueError("too many errors to correct") from None


# --- embedding and extraction -----------------------------------------------------------------

def _luma(path: str | Path):
    j = jpeglib.read_dct(str(path))
    return j, j.Y.reshape(-1, 64), j.qt[j.quant_tbl_no[0]].reshape(64).astype(float)


def embed_blob(cover_jpeg: str | Path, blob: bytes, password: str, out: str | Path, cfg: Config) -> dict:
    j, y, _ = _luma(cover_jpeg)
    cap = capacity(len(y), cfg)
    if len(blob) > cap:
        raise ValueError(f"blob is {len(blob)} bytes but this cover holds at most {cap}")
    bits = frame(blob, cfg)
    slots = _slots(cfg)
    flat = y[:, slots].reshape(-1).copy()
    where = _order(password, flat.size)[: bits.size]
    flat[where] = qim_embed(flat[where], bits, cfg.k)
    y = y.copy()
    y[:, slots] = flat.reshape(-1, cfg.Z)
    j.Y = y.reshape(j.Y.shape).astype(np.int16)
    j.write_dct(str(out))
    return {"blocks": len(y), "capacity_bytes": cap, "blob_bytes": len(blob), "embedded_bits": int(bits.size)}


def read_bits(path: str | Path, password: str, cfg: Config) -> np.ndarray:
    """Bits at every keyed position, in order, after scaling to the quality-75 table."""
    _, y, qt = _luma(path)
    slots = _slots(cfg)
    c = y[:, slots].astype(float) * (qt[slots] / _QT75.reshape(64)[slots])
    flat = c.reshape(-1)
    return qim_extract(flat[_order(password, flat.size)], cfg.k)


def extract_blob(path: str | Path, password: str, cfg: Config) -> bytes:
    bits = read_bits(path, password, cfg)
    return unframe(bits, cfg, bits.size)


def seal(cover_path: str | Path, message: str, password: str, out: str | Path, cfg: Config) -> dict:
    """Pre-shape ``cover_path``, encrypt ``message`` and write the stego JPEG to ``out``."""
    with tempfile.TemporaryDirectory() as d:
        cover = os.path.join(d, "cover.jpg")
        write_cover(preshape(cover_path), cover)
        return embed_blob(cover, make_blob(message, password), password, out, cfg)


def open_robust(path: str | Path, password: str, cfg: Config) -> str:
    """The message, or ``ValueError``. One path: no fallbacks, no retries."""
    return open_blob(extract_blob(path, password, cfg), password)


def simulate_channel(src: str | Path, dst: str | Path) -> None:
    """Stand-in for the iPhone app: decode to pixels, re-encode with libjpeg at quality 75."""
    write_cover(jpeglib.read_spatial(str(src)).spatial, dst)
