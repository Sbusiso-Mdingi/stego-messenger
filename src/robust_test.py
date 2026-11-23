# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""The one robust test (``docs/robust_protocol.md``, Test and Pass rule). Two steps::

    .venv/bin/python -m src.robust_test seal     # writes data/test_pool/run/send/t01.jpg ... t30.jpg
    .venv/bin/python -m src.robust_test score    # after the round trip, from data/test_pool/run/received/

Covers come from ``data/test_pool/draw.json`` in the order smooth then textured, each sorted by
SHA-1. One generator seeded 20261201 gives, cover by cover, a 16-character password then a
140-byte message. ``score`` matches each received file to its sent file by pixel distance (to know
which password belongs to it), decodes it blind (image, password, frozen config) and only then
compares the message.
"""

from __future__ import annotations

import hashlib
import json
import string
import sys
from pathlib import Path

import jpeglib
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from . import robust, steganalysis
from .package import OVERHEAD, make_blob, open_blob

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data/test_pool"
RUN = POOL / "run"
CFG = robust.Config(9, 6, 159)
SEED = 20261201
PSNR_MIN, SSIM_MIN, PASS_AT = 36.0, 0.97, 28


def plan() -> list[dict]:
    draw = json.loads((POOL / "draw.json").read_text())["draw"]
    rng = np.random.default_rng(SEED)
    rows = []
    for group in ("smooth", "textured"):
        for sha in sorted(draw[group]):
            pw = "".join(rng.choice(list(string.ascii_letters + string.digits), 16))
            msg = "".join(rng.choice(list(string.ascii_lowercase + " "), 140))
            rows.append({"cover": sha, "group": group, "password": pw, "message": msg})
    for i, r in enumerate(rows, 1):
        r["name"] = f"t{i:02d}"
    return rows


def luma(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(float) @ np.array([0.299, 0.587, 0.114])


def quality(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    ya, yb = luma(a), luma(b)
    return (float(peak_signal_noise_ratio(ya, yb, data_range=255)),
            float(structural_similarity(ya, yb, data_range=255)))


def draw_sha1() -> str:
    return hashlib.sha1((POOL / "draw.json").read_bytes()).hexdigest()


def seal() -> None:
    if (RUN / "sent.json").exists() or ((RUN / "send").exists() and any((RUN / "send").iterdir())):
        raise SystemExit("the test is sealed once: run/ already holds a sealing (clear it only if a crash left it partial)")
    for sub in ("send", "covers", "blobs"):
        (RUN / sub).mkdir(parents=True, exist_ok=True)
    sent = []
    for r in plan():
        shaped = robust.preshape(POOL / "prepared" / f"{r['cover']}.png")
        cover = RUN / "covers" / f"{r['name']}.jpg"
        robust.write_cover(shaped, cover)
        blob = make_blob(r["message"], r["password"])
        (RUN / "blobs" / f"{r['name']}.bin").write_bytes(blob)
        out = RUN / "send" / f"{r['name']}.jpg"
        cap = robust.capacity(len(jpeglib.read_dct(str(cover)).Y.reshape(-1, 64)), CFG)
        row = {"name": r["name"], "cover": r["cover"], "group": r["group"], "capacity_bytes": cap,
               "sealed": len(blob) <= cap}
        if row["sealed"]:
            robust.embed_blob(cover, blob, r["password"], out, CFG)
            row["sha1"] = hashlib.sha1(out.read_bytes()).hexdigest()
        sent.append(row)
    (RUN / "sent.json").write_text(json.dumps({"draw_sha1": draw_sha1(), "files": sent}, indent=1))
    print(sum(s["sealed"] for s in sent), "of", len(sent), "sealed")


MAX_RMSE = 12.0  # sent against received pixels; the real channel measured 1.2 to 3.6


def score(received_dir: Path) -> dict:
    rows = {r["name"]: r for r in plan()}
    record = json.loads((RUN / "sent.json").read_text())
    if record["draw_sha1"] != draw_sha1():
        raise SystemExit("draw.json changed after sealing")
    sent = {s["name"]: s for s in record["files"]}
    assert all(sent[n]["cover"] == rows[n]["cover"] for n in rows), "sealed covers do not match the plan"
    sent_px = {n: jpeglib.read_spatial(str(RUN / "send" / f"{n}.jpg")).spatial.astype(float)
               for n, s in sent.items() if s["sealed"]}
    results = {n: {"name": n, "group": rows[n]["group"], "capacity_bytes": sent[n]["capacity_bytes"],
                   "sealed": sent[n]["sealed"], "recovered": False, "received": None} for n in rows}
    files, matches, other = sorted(p for p in received_dir.iterdir() if not p.name.startswith(".")), {}, []
    for f in files:
        if f.suffix.lower() not in (".jpg", ".jpeg"):
            other.append({"file": f.name, "reason": "not a JPEG"})
            continue
        px = jpeglib.read_spatial(str(f)).spatial
        same = sorted((float(np.sqrt(np.mean((v - px) ** 2))), n) for n, v in sent_px.items() if v.shape == px.shape)
        if not same:
            other.append({"file": f.name, "reason": f"size {px.shape[1]}x{px.shape[0]} matches no sent file"})
        elif same[0][0] > MAX_RMSE:
            other.append({"file": f.name, "reason": f"nearest sent file {same[0][1]} is RMSE {same[0][0]:.1f} away"})
        else:
            matches.setdefault(same[0][1], []).append((f, same[0][0]))
    twice = {n: [f.name for f, _ in v] for n, v in matches.items() if len(v) > 1}
    if twice:
        raise SystemExit(f"more than one received file per sent file, resolve before scoring: {twice}")
    h = robust.HEADER_BITS * robust.HEADER_REPEAT
    for n, [(f, rmse)] in matches.items():
        res = results[n]
        res.update(received=f.name, pixel_rmse=rmse)
        # The decoder sees this image, this cover's password and the frozen config; the expected message
        # is compared only after it returns.
        try:
            res["recovered"] = open_robust_once(f, rows[n]["password"]) == rows[n]["message"]
        except Exception as e:  # any decode failure is a failure, recorded
            res["error"] = f"{type(e).__name__}: {e}"
        want = robust.frame((RUN / "blobs" / f"{n}.bin").read_bytes(), CFG)
        got = robust.read_bits(f, rows[n]["password"], CFG)[: want.size]
        res.update(bit_errors=int((got != want).sum()), coded_bits=int(want.size),
                   header_bit_errors=int((got[:h] != want[:h]).sum()))
    for n, res in results.items():
        if not res["sealed"]:
            continue
        cover = jpeglib.read_spatial(str(RUN / "covers" / f"{n}.jpg")).spatial
        shaped = robust.preshape(POOL / "prepared" / f"{rows[n]['cover']}.png")
        res["psnr"], res["ssim"] = quality(cover, sent_px[n])
        res["preshape_psnr"], res["preshape_ssim"] = quality(shaped, cover)
        res["plaintext_capacity_bytes"] = max(0, res["capacity_bytes"] - OVERHEAD)
        res["detectors"] = {kind: _detectors(RUN / kind / f"{n}.jpg") for kind in ("covers", "send")}
    rec = sum(r["recovered"] for r in results.values())
    budget = all(r["psnr"] >= PSNR_MIN and r["ssim"] >= SSIM_MIN for r in results.values() if r["recovered"])
    got = [r for r in results.values() if "coded_bits" in r]
    coded = sum(r["coded_bits"] for r in got)
    blob_bits = 8 * len((RUN / "blobs" / "t01.bin").read_bytes())
    return {"config": [CFG.Z, CFG.k, CFG.m], "received_dir": str(received_dir), "recovered": rec, "of": len(rows),
            "passes": rec >= PASS_AT and budget, "quality_budget_met": budget,
            # Over every coded bit of every received file, failed decodes included; covers not received or
            # not sealed have no bits read and are left out of the bit error rate.
            "ber": sum(r["bit_errors"] for r in got) / coded if coded else None,
            "header_bit_errors": sum(r["header_bit_errors"] for r in got),
            "header_bits": h * len(got),
            "overhead_share": 1 - blob_bits / got[0]["coded_bits"] if got else None,
            "not_received": [n for n, r in results.items() if r["received"] is None],
            "other_files": other, "results": results}


def open_robust_once(path: Path, password: str) -> str:
    return open_blob(robust.extract_blob(path, password, CFG), password)


def _detectors(path: Path) -> dict:
    out = {}
    for name, fn in (("chi_square", steganalysis.chi_square_attack), ("rs", steganalysis.rs_analysis),
                     ("hcf", steganalysis.hcf_com_calibrated)):
        try:
            out[name] = fn(path)
        except Exception as e:  # a detector that cannot read a JPEG is reported, not fatal
            out[name] = {"error": str(e)}
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["seal"]:
        seal()
    elif sys.argv[1:2] == ["score"]:
        folder = Path(sys.argv[2]) if len(sys.argv) > 2 else RUN / "received"
        report = score(folder)
        (RUN / f"scores_{folder.name}.json").write_text(json.dumps(report, indent=1, default=str))
        print({k: report[k] for k in ("recovered", "of", "passes", "quality_budget_met", "ber")})
    else:
        raise SystemExit("usage: python -m src.robust_test seal | score [received_dir]")
