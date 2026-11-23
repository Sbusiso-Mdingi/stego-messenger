# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Development simulation for the robust method (``docs/robust_protocol.md``, Development).

Runs every candidate of the frozen grid on the ten development images with seeds 20261123 to
20261127, through the simulated quality-75 channel, and applies the selection rule::

    .venv/bin/python -m src.robust_dev

Writes ``docs/robust/dev_simulation.json``. Covers, blobs and stego files go to ``data/robust_dev/``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import string
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import jpeglib
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from . import robust
from .package import make_blob, open_blob

ROOT = Path(__file__).resolve().parents[1]
DEV = sorted((ROOT / "data/channel/whatsapp/sent").glob("*.png"))
WORK = ROOT / "data/robust_dev"
OUT = ROOT / "docs/robust/dev_simulation.json"
SEEDS = range(20261123, 20261128)
GRID = [robust.Config(Z, k, m) for Z, k, m in itertools.product((5, 9, 14, 20), (2, 4, 6), (223, 191, 159, 127))]
PSNR_MIN, SSIM_MIN = 36.0, 0.97


def secrets(seed: int) -> tuple[str, str]:
    """Password (16 characters) and 140-byte message for a seed."""
    rng = np.random.default_rng(seed)
    pw = "".join(rng.choice(list(string.ascii_letters + string.digits), 16))
    msg = "".join(rng.choice(list(string.ascii_lowercase + " "), 140))
    return pw, msg


def luma(path) -> np.ndarray:
    rgb = jpeglib.read_spatial(str(path)).spatial.astype(float)
    return rgb @ np.array([0.299, 0.587, 0.114])


def quality(cover, stego) -> tuple[float, float]:
    a, b = luma(cover), luma(stego)
    return (float(peak_signal_noise_ratio(a, b, data_range=255)),
            float(structural_similarity(a, b, data_range=255)))


def trial(args) -> dict:
    name, cfg = args
    cover = WORK / "covers" / f"{name}.jpg"
    out = {"image": name, "Z": cfg.Z, "k": cfg.k, "m": cfg.m, "seeds": []}
    for seed in SEEDS:
        pw, msg = secrets(seed)
        blob = (WORK / "blobs" / f"{seed}.bin").read_bytes()
        stego = WORK / "stego" / f"{name}_Z{cfg.Z}_k{cfg.k}_m{cfg.m}_{seed}.jpg"
        sent = robust.embed_blob(cover, blob, pw, stego, cfg)
        psnr, ssim = quality(cover, stego)
        recv = stego.with_suffix(".sim.jpg")
        robust.simulate_channel(stego, recv)
        want = robust.frame(blob, cfg)
        got = robust.read_bits(recv, pw, cfg)[: want.size]
        try:
            ok = open_blob(robust.extract_blob(recv, pw, cfg), pw) == msg
        except ValueError:
            ok = False
        out["seeds"].append({"seed": seed, "recovered": ok, "psnr": psnr, "ssim": ssim,
                             "bit_errors": int((got != want).sum()), "coded_bits": int(want.size),
                             "capacity_bytes": sent["capacity_bytes"]})
        stego.unlink(), recv.unlink()
    return out


def prepare() -> list[str]:
    for sub in ("covers", "blobs", "stego"):
        (WORK / sub).mkdir(parents=True, exist_ok=True)
    names = []
    for p in DEV:
        robust.write_cover(robust.preshape(p), WORK / "covers" / f"{p.stem}.jpg")
        names.append(p.stem)
    for seed in SEEDS:
        f = WORK / "blobs" / f"{seed}.bin"
        if not f.exists():  # the blob's salt and nonce are random, so it is made once and kept
            pw, msg = secrets(seed)
            f.write_bytes(make_blob(msg, pw))
    return names


def select(results: list[dict]) -> dict:
    by = {}
    for r in results:
        c = by.setdefault((r["Z"], r["k"], r["m"]), {"recovered": 0, "trials": 0, "psnr": 99.0, "ssim": 1.0,
                                                     "bit_errors": 0, "coded_bits": 0})
        for s in r["seeds"]:
            c["recovered"] += s["recovered"]
            c["trials"] += 1
            c["psnr"], c["ssim"] = min(c["psnr"], s["psnr"]), min(c["ssim"], s["ssim"])
            c["bit_errors"] += s["bit_errors"]
            c["coded_bits"] += s["coded_bits"]
    table = []
    for (Z, k, m), c in by.items():
        c.update(Z=Z, k=k, m=m, ber=c["bit_errors"] / c["coded_bits"],
                 qualifies=c["recovered"] == c["trials"] == 50 and c["psnr"] >= PSNR_MIN and c["ssim"] >= SSIM_MIN)
        table.append(c)
    order = sorted((c for c in table if c["qualifies"]), key=lambda c: (c["k"], c["Z"], -c["m"]))
    return {"candidates": sorted(table, key=lambda c: (c["k"], c["Z"], -c["m"])),
            "qualifying_in_order": [(c["Z"], c["k"], c["m"]) for c in order],
            "selected": order[0] if order else None}


if __name__ == "__main__":
    names = prepare()
    jobs = [(n, cfg) for cfg in GRID for n in names]
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        results = list(ex.map(trial, jobs, chunksize=4))
    report = {"protocol_sha1": hashlib.sha1((ROOT / "docs/robust_protocol.md").read_bytes()).hexdigest(),
              "jpeglib": jpeglib.__version__ if hasattr(jpeglib, "__version__") else None,
              "libjpeg": jpeglib.version.get(),
              "blobs_sha1": {s: hashlib.sha1((WORK / "blobs" / f"{s}.bin").read_bytes()).hexdigest() for s in SEEDS},
              **select(results), "trials": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1))
    print("selected:", report["selected"])
    print("qualifying in order:", report["qualifying_in_order"][:8])
