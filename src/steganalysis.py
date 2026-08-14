# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Transparent LSB diagnostics. These metrics are not a stego classifier."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image


def lsb_diagnostics(image_path: str | Path) -> dict[str, float]:
    with Image.open(image_path) as image:
        arr = np.asarray(image.convert("L"), dtype=np.uint8)

    bits = (arr.reshape(-1) & 1).astype(np.uint8)
    if bits.size < 2:
        raise ValueError("image is too small for LSB diagnostics")

    ones = float(bits.mean())
    entropy = 0.0
    for probability in (ones, 1.0 - ones):
        if probability > 0:
            entropy -= probability * math.log2(probability)

    transition_rate = float(np.mean(bits[1:] != bits[:-1]))
    balance_deviation = abs(ones - 0.5) * 2.0

    return {
        "lsb_one_ratio": ones,
        "lsb_entropy_bits": entropy,
        "lsb_transition_rate": transition_rate,
        "balance_deviation": balance_deviation,
    }


def lsb_randomness_score(image_path: str | Path) -> float:
    """Heuristic 0..1 randomness score; not a probability of hidden data."""
    metrics = lsb_diagnostics(image_path)
    balance = 1.0 - min(1.0, metrics["balance_deviation"])
    transition = 1.0 - min(1.0, abs(metrics["lsb_transition_rate"] - 0.5) * 2.0)
    return float((metrics["lsb_entropy_bits"] + balance + transition) / 3.0)
