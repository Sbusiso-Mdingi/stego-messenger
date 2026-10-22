# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Reproducible steganography benchmark.

Sweeps payload size across a fixed public-domain image corpus for each embedding method
(sequential LSB replacement and keyed LSB matching), embeds random payloads
(indistinguishable from the AES-GCM ciphertext this toolkit actually hides), and records
distortion, recovery and detectability with confidence intervals over several seeds.
Results and the full environment are exported as JSON and CSV so a run can be compared or
reproduced later.

Run with::

    python -m src.benchmark --out benchmark-output
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import data

from .evaluation import bit_error_rate, psnr_db, ssim
from .lsb_stego import METHODS, capacity_bytes, embed_data, extract_data
from .steganalysis import chi_square_attack, hcf_com_calibrated, rs_analysis

# Public-domain RGB images shipped with scikit-image. Documented provenance, no download.
CORPUS = ("astronaut", "coffee", "rocket", "chelsea", "hubble_deep_field")
DEFAULT_FRACTIONS = (0.0, 0.05, 0.1, 0.25, 0.5, 0.9)
DEFAULT_SEEDS = (0, 1, 2, 3, 4)


@dataclass
class Measurement:
    """One (method, image, payload fraction, seed) observation."""

    method: str
    image: str
    fraction: float
    seed: int
    payload_bytes: int
    capacity_bytes: int
    roundtrip_success: bool
    bit_error_rate: float
    psnr_db: float
    ssim: float
    chi_square_probability: float
    rs_estimated_rate: float
    rs_reliable: bool
    hcf_com_ratio: float
    hcf_com_shift: float


@dataclass
class Aggregate:
    """Mean and 95% confidence interval of a metric over seeds."""

    mean: float
    ci_low: float
    ci_high: float
    n: int = field(default=0)


def build_corpus(output_dir: str | Path, names: tuple[str, ...] = CORPUS) -> list[Path]:
    """Write the sample images to lossless PNGs and return their paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        arr = np.asarray(getattr(data, name)())
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        arr = arr[:, :, :3].astype(np.uint8)
        path = out / f"{name}.png"
        Image.fromarray(arr, mode="RGB").save(path)
        paths.append(path)
    return paths


def _mean_ci(values: list[float], confidence: float = 0.95) -> Aggregate:
    """Mean and normal-approximation confidence interval; degenerate for n < 2."""
    arr = np.asarray(values, dtype=np.float64)
    n = arr.size
    mean = float(arr.mean()) if n else 0.0
    if n < 2:
        return Aggregate(mean, mean, mean, n)
    z = 1.959963984540054 if confidence == 0.95 else abs(_inv_normal((1 + confidence) / 2))
    half = z * float(arr.std(ddof=1)) / math.sqrt(n)
    return Aggregate(mean, mean - half, mean + half, n)


def _inv_normal(q: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.357751867269, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416]
    plow, phigh = 0.02425, 1 - 0.02425
    if q < plow:
        r = math.sqrt(-2 * math.log(q))
        return (((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]) / (
            (((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1)
    if q <= phigh:
        r = q - 0.5
        s = r * r
        return (((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * r / (
            ((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1)
    r = math.sqrt(-2 * math.log(1 - q))
    return -(((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]) / (
        (((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1)


def measure(
    cover_path: Path,
    fraction: float,
    seed: int,
    work_dir: Path,
    method: str = "sequential",
) -> Measurement:
    """Embed one random payload at the given fraction of capacity and measure it."""
    capacity = capacity_bytes(cover_path)
    n_bytes = round(capacity * fraction)
    rng = np.random.default_rng(seed)
    payload = rng.integers(0, 256, n_bytes, dtype=np.uint8).tobytes()
    # A fixed per-seed key keeps keyed runs reproducible without paying for scrypt.
    key = f"benchmark-seed-{seed}".encode() if method == "keyed" else None

    stego = work_dir / f"{method}_{cover_path.stem}_f{fraction}_s{seed}.png"
    if n_bytes == 0:
        # The zero-payload point is the clean-cover control for the detectors.
        Image.open(cover_path).convert("RGB").save(stego)
        roundtrip, ber = True, 0.0
    else:
        embed_data(cover_path, payload, stego, method=method, key=key, seed=seed)
        recovered = extract_data(stego, method=method, key=key)
        roundtrip = recovered == payload
        ber = bit_error_rate(payload, recovered)

    chi = chi_square_attack(stego)
    rs = rs_analysis(stego)
    hcf = hcf_com_calibrated(stego)["ratio"]
    return Measurement(
        method=method,
        image=cover_path.stem,
        fraction=fraction,
        seed=seed,
        payload_bytes=n_bytes,
        capacity_bytes=capacity,
        roundtrip_success=roundtrip,
        bit_error_rate=ber,
        psnr_db=psnr_db(cover_path, stego) if n_bytes else math.inf,
        ssim=ssim(cover_path, stego) if n_bytes else 1.0,
        chi_square_probability=chi["mean_embedding_probability"],
        rs_estimated_rate=rs["estimated_embedding_rate"],
        rs_reliable=bool(rs["reliable"]),
        hcf_com_ratio=hcf,
        # Paired with the image's own cover: how far embedding moved the score.
        hcf_com_shift=hcf - hcf_com_calibrated(cover_path)["ratio"],
    )


def run(
    fractions: tuple[float, ...] = DEFAULT_FRACTIONS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    names: tuple[str, ...] = CORPUS,
    out_dir: str | Path = "benchmark-output",
    methods: tuple[str, ...] = METHODS,
) -> dict:
    """Run the full sweep and return a results dictionary (also written to disk)."""
    out = Path(out_dir)
    corpus = build_corpus(out / "corpus", names)

    rows: list[Measurement] = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for method in methods:
            for cover in corpus:
                for fraction in fractions:
                    for seed in seeds:
                        rows.append(measure(cover, fraction, seed, work, method))

    summary = _summarise(rows, fractions, methods)
    results = {
        "environment": _environment(),
        "methods": list(methods),
        "corpus": [c.name for c in corpus],
        "fractions": list(fractions),
        "seeds": list(seeds),
        "summary": summary,
        "measurements": [vars(r) for r in rows],
    }

    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmark.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    _write_csv(out / "measurements.csv", rows)
    return results


def _summarise(
    rows: list[Measurement], fractions: tuple[float, ...], methods: tuple[str, ...]
) -> list[dict]:
    out = []
    for method in methods:
        for fraction in fractions:
            subset = [r for r in rows if r.method == method and r.fraction == fraction]
            if subset:
                out.append(_aggregate(method, fraction, subset))
    return out


def _aggregate(method: str, fraction: float, subset: list[Measurement]) -> dict:
    finite_psnr = [r.psnr_db for r in subset if math.isfinite(r.psnr_db)]
    return {
        "method": method,
        "fraction": fraction,
        "n": len(subset),
        "roundtrip_success_rate": float(np.mean([r.roundtrip_success for r in subset])),
        "psnr_db": vars(_mean_ci(finite_psnr)) if finite_psnr else None,
        "ssim": vars(_mean_ci([r.ssim for r in subset])),
        "chi_square_probability": vars(_mean_ci([r.chi_square_probability for r in subset])),
        "rs_estimated_rate": vars(_mean_ci([r.rs_estimated_rate for r in subset])),
        "hcf_com_ratio": vars(_mean_ci([r.hcf_com_ratio for r in subset])),
        "hcf_com_shift": vars(_mean_ci([r.hcf_com_shift for r in subset])),
    }


def _write_csv(path: Path, rows: list[Measurement]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(vars(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(vars(row))


def _environment() -> dict:
    packages = {}
    for name in ("numpy", "pillow", "opencv-python-headless", "scikit-image", "cryptography"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
        "git_commit": _git_commit(),
    }


def _git_commit() -> str | None:
    try:
        here = Path(__file__).resolve().parent
        out = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible steganography benchmark")
    parser.add_argument("--out", default="benchmark-output", help="output directory")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument("--fractions", type=float, nargs="+", default=list(DEFAULT_FRACTIONS))
    parser.add_argument("--images", nargs="+", default=list(CORPUS))
    parser.add_argument("--methods", nargs="+", default=list(METHODS), choices=METHODS)
    args = parser.parse_args(argv)

    results = run(
        fractions=tuple(args.fractions),
        seeds=tuple(args.seeds),
        names=tuple(args.images),
        out_dir=args.out,
        methods=tuple(args.methods),
    )
    print(f"Wrote {len(results['measurements'])} measurements to {args.out}/")
    for row in results["summary"]:
        psnr = row["psnr_db"]["mean"] if row["psnr_db"] else float("inf")
        print(
            f"  {row['method']:<10} fraction {row['fraction']:>4}: "
            f"PSNR {psnr:6.1f} dB  "
            f"SSIM {row['ssim']['mean']:.4f}  "
            f"RS rate {row['rs_estimated_rate']['mean']:.3f}  "
            f"chi {row['chi_square_probability']['mean']:.3f}  "
            f"HCF shift {row['hcf_com_shift']['mean']:+.4f}  "
            f"recovery {row['roundtrip_success_rate']*100:5.1f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
