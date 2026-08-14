# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Reproducible evaluation utilities for image steganography experiments."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from .attacks import add_gaussian_noise, crop_image, jpeg_compress, read_image, resize_image
from .lsb_stego import capacity_bytes, embed_data, extract_data
from .steganalysis import lsb_diagnostics


def _rgb_array(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float64)


def mean_squared_error(reference_path: str | Path, candidate_path: str | Path) -> float:
    reference = _rgb_array(reference_path)
    candidate = _rgb_array(candidate_path)
    if reference.shape != candidate.shape:
        raise ValueError("images must have the same dimensions")
    return float(np.mean((reference - candidate) ** 2))


def psnr_db(reference_path: str | Path, candidate_path: str | Path) -> float:
    mse = mean_squared_error(reference_path, candidate_path)
    if mse == 0:
        return math.inf
    return float(10 * math.log10((255.0**2) / mse))


def bit_error_rate(expected: bytes, actual: bytes) -> float:
    if len(expected) != len(actual):
        return 1.0
    if not expected:
        return 0.0
    a = np.unpackbits(np.frombuffer(expected, dtype=np.uint8))
    b = np.unpackbits(np.frombuffer(actual, dtype=np.uint8))
    return float(np.mean(a != b))


def evaluate_embedding(
    cover_path: str | Path,
    payload: bytes,
    stego_path: str | Path,
) -> dict[str, object]:
    embed_data(cover_path, payload, stego_path)
    recovered = extract_data(stego_path)
    capacity = capacity_bytes(cover_path)
    return {
        "payload_bytes": len(payload),
        "capacity_bytes": capacity,
        "capacity_utilization": len(payload) / capacity if capacity else 0.0,
        "roundtrip_success": recovered == payload,
        "bit_error_rate": bit_error_rate(payload, recovered),
        "mse": mean_squared_error(cover_path, stego_path),
        "psnr_db": psnr_db(cover_path, stego_path),
        "cover_lsb": lsb_diagnostics(cover_path),
        "stego_lsb": lsb_diagnostics(stego_path),
    }


def evaluate_attacks(
    stego_path: str | Path,
    expected_payload: bytes,
    output_dir: str | Path,
) -> list[dict[str, object]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    original = read_image(str(stego_path))

    attacks: list[tuple[str, Callable[[np.ndarray], np.ndarray]]] = [
        ("jpeg_q70", lambda image: jpeg_compress(image, quality=70)),
        ("gaussian_std5", lambda image: add_gaussian_noise(image, std=5, seed=0)),
        ("center_crop_95pct", lambda image: crop_image(image, crop_ratio=0.95)),
        ("resize_75pct", lambda image: resize_image(image, scale=0.75)),
    ]

    rows: list[dict[str, object]] = []
    for name, transform in attacks:
        attacked = transform(original)
        attacked_path = output / f"{name}.png"
        cv2.imwrite(str(attacked_path), attacked)
        try:
            recovered = extract_data(attacked_path)
            success = recovered == expected_payload
            ber = bit_error_rate(expected_payload, recovered)
            error = None
        except Exception as exc:
            success = False
            ber = 1.0
            error = str(exc)
        rows.append(
            {
                "attack": name,
                "recovery_success": success,
                "bit_error_rate": ber,
                "error": error,
            }
        )
    return rows
