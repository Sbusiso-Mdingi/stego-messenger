# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Prepares the robust test pool and draws the 30 test covers (``docs/robust_protocol.md``, Test)::

    .venv/bin/python -m src.robust_pool

Checks ``data/test_pool/incoming`` against ``pool_received.sha1``, decodes every file with macOS
``sips`` to 8-bit sRGB PNG, then applies Exif orientation, applies the exclusions, splits smooth from textured at the median mean luma
gradient of the pre-shaped cover and draws 15 of each with seed 20261201. Only camera model,
capture date and pixel size are read from metadata. Writes ``data/test_pool/draw.json``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import jpeglib
import numpy as np
from PIL import Image, ImageOps

from . import robust

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data/test_pool"
SRGB = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"
SEED = 20261201
DHASH_MAX = 6


def sips_props(path: Path) -> dict:
    out = subprocess.run(["sips", "-g", "model", "-g", "creation", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                         capture_output=True, text=True, check=True).stdout
    props = {}
    for line in out.splitlines()[1:]:
        k, _, v = line.strip().partition(": ")
        props[k] = None if v in ("", "<nil>") else v  # sips prints <nil> for a missing field
    return props


def to_png(src: Path, dst: Path) -> None:
    """``sips`` to sRGB PNG; it copies the Exif orientation tag without rotating, so rotate here."""
    tmp = dst.with_suffix(".tmp.png")
    subprocess.run(["sips", "-s", "format", "png", "--matchTo", SRGB, str(src), "--out", str(tmp)],
                   capture_output=True, check=True)
    with Image.open(tmp) as im:
        ImageOps.exif_transpose(im).convert("RGB").save(dst.with_suffix(".part.png"))
    dst.with_suffix(".part.png").rename(dst)
    tmp.unlink()


def dhash(rgb: np.ndarray) -> int:
    g = Image.fromarray(rgb).convert("L").resize((9, 8), Image.LANCZOS)
    a = np.asarray(g, dtype=int)
    bits = (a[:, 1:] > a[:, :-1]).reshape(-1)
    return int("".join("1" if b else "0" for b in bits), 2)


def cover_pixels(png: Path) -> np.ndarray:
    """The pre-shaped cover as decoded pixels: pre-shape, write the quality-75 JPEG, decode it."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cover.jpg"
        robust.write_cover(robust.preshape(png), path)
        return jpeglib.read_spatial(str(path)).spatial


def gradient(rgb: np.ndarray) -> float:
    y = rgb.astype(float) @ np.array([0.299, 0.587, 0.114])
    gy, gx = np.gradient(y)
    return float(np.hypot(gx, gy).mean())


def main() -> dict:
    recorded = {}
    for line in (POOL / "pool_received.sha1").read_text().splitlines():
        if line and not line.startswith("#"):
            h, name = line.split(maxsplit=1)
            recorded[name] = h
    files = sorted((POOL / "incoming").iterdir())
    assert sorted(f.name for f in files) == sorted(recorded), "incoming does not match pool_received.sha1"
    for f in files:
        assert hashlib.sha1(f.read_bytes()).hexdigest() == recorded[f.name], f"changed since arrival: {f.name}"

    prepared = POOL / "prepared"
    prepared.mkdir(exist_ok=True)
    rows, excluded = [], []
    for f in files:
        sha, props = recorded[f.name], sips_props(f)
        png = prepared / f"{sha}.png"
        if not png.exists():
            to_png(f, png)
        with Image.open(png) as im:
            w, h = im.size
        row = {"sha1": sha, "model": props.get("model"), "creation": props.get("creation"), "size": [w, h]}
        if not props.get("model"):
            excluded.append({**row, "reason": "no camera model"})
        elif max(w, h) < robust.LONG_SIDE:
            excluded.append({**row, "reason": "long side under 1,280 px"})
        else:
            rows.append(row)

    # Near-duplicates: earliest capture kept (ties by SHA-1, undated last). Each photo is compared with the
    # photos already kept, so in a chain A~B~C where A and C differ by more than 6 bits, A and C are kept.
    rows.sort(key=lambda r: (r["creation"] is None, r["creation"] or "", r["sha1"]))
    kept = []
    for r in rows:
        r["dhash"] = dhash(robust.preshape(prepared / f"{r['sha1']}.png"))
        twin = next((k for k in kept if bin(k["dhash"] ^ r["dhash"]).count("1") <= DHASH_MAX), None)
        if twin:
            excluded.append({**r, "reason": f"near-duplicate of {twin['sha1']}"})
        else:
            kept.append(r)

    for r in kept:
        r["gradient"] = gradient(cover_pixels(prepared / f"{r['sha1']}.png"))
    median = float(np.median([r["gradient"] for r in kept]))
    smooth = sorted((r["sha1"] for r in kept if r["gradient"] < median))
    textured = sorted((r["sha1"] for r in kept if r["gradient"] >= median))
    rng = np.random.default_rng(SEED)
    draw = {"smooth": sorted(rng.choice(smooth, 15, replace=False).tolist()),
            "textured": sorted(rng.choice(textured, 15, replace=False).tolist())}
    for r in kept + excluded:
        r.pop("dhash", None)
    out = {"received": len(files), "eligible": len(kept), "excluded": excluded, "median_gradient": median,
           "smooth_pool": len(smooth), "textured_pool": len(textured), "draw": draw, "eligible_rows": kept}
    (POOL / "draw.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    o = main()
    print({k: o[k] for k in ("received", "eligible", "median_gradient", "smooth_pool", "textured_pool")})
    for e in o["excluded"]:
        print("excluded", e["sha1"][:10], e["reason"])
