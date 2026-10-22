# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Steganalysis for LSB embedding.

Two kinds of tool live here, and the distinction matters:

* ``lsb_diagnostics`` / ``lsb_randomness_score`` are *descriptive statistics* of the
  least-significant-bit plane. They are not detectors and do not output a probability
  that an image carries a payload.
* ``chi_square_attack`` and ``rs_analysis`` are *calibrated detectors* from the public
  steganalysis literature. They estimate whether, and how much, LSB *replacement* has
  taken place. The purpose is defensive: to measure how detectable this project's own
  embedding is, so that any robustness claim is grounded in a measurement rather than
  assumed.
* ``hcf_com_calibrated`` targets LSB *matching*, which the two detectors above are
  largely blind to. Matching acts like adding low-amplitude noise, which smooths the
  histogram and lowers the centre of mass of its characteristic function; comparing the
  image with a downsampled copy of itself calibrates that measure.

References
----------
Westfeld and Pfitzmann (2000), "Attacks on Steganographic Systems" (chi-square).
Fridrich, Goljan and Du (2001), "Reliable Detection of LSB Steganography" (RS analysis).
Harmsen and Pearlman (2003), "Steganalysis of Additive Noise Modelable Information Hiding".
Ker (2005), "Steganalysis of LSB Matching in Grayscale Images" (calibrated HCF-COM).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image


def _load_gray(image_path: str | Path) -> np.ndarray:
    with Image.open(image_path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _load_rgb(image_path: str | Path) -> np.ndarray:
    with Image.open(image_path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


# --------------------------------------------------------------------------------------
# Descriptive diagnostics (not a detector)
# --------------------------------------------------------------------------------------

def lsb_diagnostics(image_path: str | Path) -> dict[str, float]:
    """Descriptive statistics of the grayscale LSB plane. Not a detector."""
    arr = _load_gray(image_path)
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


# --------------------------------------------------------------------------------------
# Chi-square attack (Westfeld & Pfitzmann, 2000)
# --------------------------------------------------------------------------------------

def _chi_square_pair_statistic(values: np.ndarray) -> float:
    """Probability of embedding over one block, from pairs-of-values histograms.

    Sequential LSB replacement makes the two members of each pair (2k, 2k+1) equally
    likely. The test compares the observed even-value count against the pair mean under
    that hypothesis. A high probability means the histogram already looks embedded.
    """
    hist = np.bincount(values.reshape(-1), minlength=256).astype(np.float64)
    even = hist[0:256:2]
    odd = hist[1:256:2]
    expected = (even + odd) / 2.0

    mask = expected > 0
    even, expected = even[mask], expected[mask]
    if even.size <= 1:
        return 0.0

    chi = float(np.sum((even - expected) ** 2 / expected))
    dof = even.size - 1
    # Under embedding the pair histograms equalise, so chi is small. The embedding
    # probability is the chi-square upper-tail (survival) probability: small chi gives a
    # value near one, the large chi of an untouched natural histogram gives near zero.
    return _chi2_sf(chi, dof)


def _chi2_sf(chi: float, dof: int) -> float:
    """Upper-tail probability of a chi-square variate, computed without SciPy."""
    return _gammaincc(dof / 2.0, chi / 2.0)


def _gammaincc(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x), stable for the ranges used here."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gammainc_series(a, x)
    return _gammainc_cf(a, x)


def _gammainc_series(a: float, x: float) -> float:
    term = 1.0 / a
    total = term
    for n in range(1, 1000):
        term *= x / (a + n)
        total += term
        if abs(term) < abs(total) * 1e-14:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gammainc_cf(a: float, x: float) -> float:
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi_square_attack(image_path: str | Path, blocks: int = 64) -> dict[str, float]:
    """Westfeld-Pfitzmann chi-square test over sequential blocks of the image.

    Returns the average and maximum embedding probability across ``blocks`` equal slices
    of the pixel stream, plus the fraction of blocks flagged above 0.5. For a clean
    cover these stay near zero; sequential LSB replacement drives the leading blocks
    towards one.
    """
    arr = _load_rgb(image_path).reshape(-1)
    if arr.size < blocks * 2:
        raise ValueError("image is too small for the requested number of blocks")

    slices = np.array_split(arr, blocks)
    probs = np.array([_chi_square_pair_statistic(s) for s in slices])
    return {
        "mean_embedding_probability": float(probs.mean()),
        "max_embedding_probability": float(probs.max()),
        "flagged_block_fraction": float(np.mean(probs > 0.5)),
    }


# --------------------------------------------------------------------------------------
# RS analysis (Fridrich, Goljan & Du, 2001)
# --------------------------------------------------------------------------------------

_MASK = np.array([0, 1, 1, 0], dtype=np.int64)


def _discrimination(groups: np.ndarray) -> np.ndarray:
    """Noise measure f: sum of absolute adjacent differences within each group."""
    return np.abs(np.diff(groups.astype(np.int64), axis=1)).sum(axis=1)


def _flip(groups: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Flipping function: F1 (LSB toggle) where mask=+1, F-1 (dual flip) where mask=-1."""
    out = groups.astype(np.int64).copy()
    pos = mask == 1
    neg = mask == -1
    out[:, pos] ^= 1
    # F-1 maps value v to F1(v+1)-1, i.e. the dual of the LSB toggle.
    out[:, neg] = ((out[:, neg] + 1) ^ 1) - 1
    return out


def _rs_groups(channel: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    """Return the regular and singular group fractions for one channel and mask."""
    usable = (channel.size // 4) * 4
    groups = channel.reshape(-1)[:usable].reshape(-1, 4)
    d_before = _discrimination(groups)
    d_after = _discrimination(_flip(groups, mask))
    regular = float(np.mean(d_after > d_before))
    singular = float(np.mean(d_after < d_before))
    return regular, singular


def _rs_curve_points(arr: np.ndarray) -> dict[str, float]:
    """Average R and S for mask m and -m, on the image and on its fully flipped LSBs."""
    flipped = arr ^ 1  # F1 applied to every pixel: the p=1 reference point
    acc = {"Rm": 0.0, "Sm": 0.0, "RM": 0.0, "SM": 0.0,
           "Rm1": 0.0, "Sm1": 0.0, "RM1": 0.0, "SM1": 0.0}
    for c in range(3):
        rm, sm = _rs_groups(arr[:, :, c], _MASK)
        rmm, smm = _rs_groups(arr[:, :, c], -_MASK)
        rm1, sm1 = _rs_groups(flipped[:, :, c], _MASK)
        rmm1, smm1 = _rs_groups(flipped[:, :, c], -_MASK)
        acc["Rm"] += rm; acc["Sm"] += sm; acc["RM"] += rmm; acc["SM"] += smm
        acc["Rm1"] += rm1; acc["Sm1"] += sm1; acc["RM1"] += rmm1; acc["SM1"] += smm1
    return {k: v / 3.0 for k, v in acc.items()}


def rs_analysis(image_path: str | Path) -> dict[str, float]:
    """Estimate the LSB-replacement embedding rate by the RS method.

    Measures the regular/singular group statistics for the mask [0,1,1,0] and its
    negation, both on the image and on the image with every LSB flipped, then solves the
    RS quadratic (Fridrich et al., 2001) for the fraction ``p`` of pixels whose LSB was
    modified. ``p`` near zero indicates a clean cover; near one indicates a fully
    embedded LSB plane. The absolute message length is ``p`` times the LSB capacity.
    """
    arr = _load_rgb(image_path)
    pts = _rs_curve_points(arr)

    d0 = pts["Rm"] - pts["Sm"]
    dm0 = pts["RM"] - pts["SM"]
    d1 = pts["Rm1"] - pts["Sm1"]
    dm1 = pts["RM1"] - pts["SM1"]

    p, reliable = _solve_rs_quadratic(d0, dm0, d1, dm1)
    return {
        "regular_groups": pts["Rm"],
        "singular_groups": pts["Sm"],
        "regular_groups_dual": pts["RM"],
        "singular_groups_dual": pts["SM"],
        "estimated_embedding_rate": p,
        "reliable": reliable,
    }


def _solve_rs_quadratic(d0: float, dm0: float, d1: float, dm1: float) -> tuple[float, bool]:
    """Solve the RS quadratic for the embedding rate p, with a reliability flag.

    Curve points: ``d0``/``dm0`` are R_m - S_m for masks m and -m on the image;
    ``d1``/``dm1`` are the same after flipping all LSBs. The RS model gives
    ``2(d1 + d0) z^2 + (dm0 - dm1 - d1 - 3 d0) z + (d0 - dm0) = 0`` with the embedding
    rate ``p = z / (z - 1/2)``.

    A negative discriminant means the measured point lies at the method's singular point,
    where ``d0`` collapses to zero: this only happens at a near-saturated LSB plane. The
    estimate is reported as 1.0 and flagged unreliable, matching the known behaviour of
    RS analysis as the embedding rate approaches one.
    """
    a = 2.0 * (d1 + d0)
    b = dm0 - dm1 - d1 - 3.0 * d0
    c = d0 - dm0

    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return 1.0, False
        z = -c / b
    else:
        disc = b * b - 4.0 * a * c
        if disc < 0:
            return 1.0, False
        root = math.sqrt(disc)
        z1 = (-b + root) / (2.0 * a)
        z2 = (-b - root) / (2.0 * a)
        z = z1 if abs(z1) <= abs(z2) else z2  # the root of smaller magnitude

    denom = z - 0.5
    if abs(denom) < 1e-12:
        return 1.0, True
    p = z / denom
    return float(min(1.0, max(0.0, p))), True


# --------------------------------------------------------------------------------------
# Calibrated HCF centre of mass (Harmsen & Pearlman, 2003; Ker, 2005)
# --------------------------------------------------------------------------------------

def _hcf_com(histogram: np.ndarray) -> float:
    """Centre of mass of the histogram characteristic function over frequencies 1..128."""
    hcf = np.abs(np.fft.fft(histogram.astype(np.float64)))[1:129]
    k = np.arange(1, 129, dtype=np.float64)
    total = hcf.sum()
    return float((k * hcf).sum() / total) if total > 0 else 0.0


def hcf_com_calibrated(image_path: str | Path) -> dict[str, float | list[float]]:
    """Ratio of the image's HCF centre of mass to that of its 2x2-downsampled copy.

    Downsampling averages away most of the embedding noise, so the copy approximates the
    cover. For a clean image the ratio sits at an image-dependent level; LSB matching
    lowers it. The ratio is a score, not a probability, and it varies more between
    natural images than embedding moves it at small payloads, so it is most informative
    when compared against the same image's cover.
    """
    arr = _load_rgb(image_path).astype(np.float64)
    h, w = (arr.shape[0] // 2) * 2, (arr.shape[1] // 2) * 2
    if h < 2 or w < 2:
        raise ValueError("image is too small for HCF analysis")
    ratios = []
    for c in range(3):
        channel = arr[:h, :w, c]
        small = (channel[0::2, 0::2] + channel[1::2, 0::2] + channel[0::2, 1::2]
                 + channel[1::2, 1::2]) / 4.0
        full = _hcf_com(np.bincount(channel.astype(np.int64).ravel(), minlength=256))
        down = _hcf_com(np.bincount(np.floor(small).astype(np.int64).ravel(), minlength=256))
        ratios.append(full / down if down > 0 else 1.0)
    return {"ratio": float(np.mean(ratios)), "per_channel": [float(r) for r in ratios]}
