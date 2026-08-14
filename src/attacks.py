# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Deterministic image transformations used by the evaluation harness."""

from __future__ import annotations

import cv2
import numpy as np


def read_image(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"could not read image: {image_path}")
    return image


def jpeg_compress(image: np.ndarray, quality: int = 70) -> np.ndarray:
    if not 1 <= quality <= 100:
        raise ValueError("quality must be between 1 and 100")
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError("JPEG decoding failed")
    return decoded


def add_gaussian_noise(
    image: np.ndarray,
    mean: float = 0.0,
    std: float = 5.0,
    *,
    seed: int = 0,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(mean, std, image.shape)
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def crop_image(image: np.ndarray, crop_ratio: float = 0.95) -> np.ndarray:
    if not 0 < crop_ratio <= 1:
        raise ValueError("crop_ratio must be in (0, 1]")
    h, w = image.shape[:2]
    new_h, new_w = max(1, int(h * crop_ratio)), max(1, int(w * crop_ratio))
    top = (h - new_h) // 2
    left = (w - new_w) // 2
    return image[top : top + new_h, left : left + new_w]


def resize_image(image: np.ndarray, scale: float = 0.75) -> np.ndarray:
    if scale <= 0:
        raise ValueError("scale must be positive")
    h, w = image.shape[:2]
    return cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))))
