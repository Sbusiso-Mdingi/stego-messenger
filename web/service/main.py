# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""HTTP service for the Stego Messenger preview.

Hides a message with both embedding methods, runs the toolkit's detectors on each result
and returns everything the page needs to compare them. Nothing is stored: every request
works in a temporary directory that is deleted before the response is sent.
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
import threading
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from skimage import data

from src.evaluation import psnr_db, ssim
from src.package import max_message_bytes, open_package, seal
from src.steganalysis import chi_square_attack, hcf_com_calibrated, rs_analysis

ROOT = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[2]))
STATIC = ROOT / "web" / "dashboard" / "dist"
ALLOWED_ORIGINS = ["https://mdingi.co.za", "https://www.mdingi.co.za", "http://localhost:4321",
                   "http://localhost:5173"]
FRAME_ANCESTORS = "'self' https://mdingi.co.za https://www.mdingi.co.za http://localhost:*"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SIDE = 640  # uploads are scaled down to this, which keeps the free plan responsive
MAX_FILL = 0.9
RS_FLAG = 0.1  # clean natural images read about 0.02 to 0.04
INK, GOLD = (17, 22, 20), (224, 164, 73)

# Public-domain samples bundled with scikit-image.
SAMPLES = {
    "coffee": ("Coffee", data.coffee),
    "chelsea": ("Chelsea the cat", data.chelsea),
    "rocket": ("Rocket launch", data.rocket),
    "astronaut": ("Astronaut", data.astronaut),
}

# Each hide request runs two scrypt derivations per method and three detectors on three
# images, so a small cap on concurrent work protects the free App Service plan.
busy = threading.BoundedSemaphore(2)


def _fit(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return image


def _png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=False)
    return out.getvalue()


SAMPLE_PNG = {key: _png(_fit(Image.fromarray(np.asarray(load())[:, :, :3])))
              for key, (_, load) in SAMPLES.items()}


def _data_uri(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _changes_map(cover: Path, stego: Path) -> bytes:
    """Every pixel the embedding touched, in gold on ink."""
    a = np.asarray(Image.open(cover).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(stego).convert("RGB"), dtype=np.int16)
    changed = (a != b).any(axis=2).astype(np.uint8)
    image = Image.fromarray(changed, mode="P")
    image.putpalette([*INK, *GOLD])
    out = io.BytesIO()
    image.save(out, format="PNG", bits=1, optimize=True)
    return out.getvalue()


def _detect(path: Path) -> dict:
    rs = rs_analysis(path)
    return {
        "rs_rate": rs["estimated_embedding_rate"],
        "rs_reliable": bool(rs["reliable"]),
        "chi_square": chi_square_attack(path)["mean_embedding_probability"],
        "hcf_ratio": hcf_com_calibrated(path)["ratio"],
    }


async def _read_image(upload: UploadFile) -> Image.Image:
    raw = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Images must be 8 MB or smaller.")
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "That file is not an image this preview can read.") from None
    return image


app = FastAPI(title="Stego Messenger", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["*"])


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = f"frame-ancestors {FRAME_ANCESTORS}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/samples"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/samples")
def samples():
    out = []
    for key, (label, _) in SAMPLES.items():
        with Image.open(io.BytesIO(SAMPLE_PNG[key])) as image:
            width, height = image.size
        out.append({"id": key, "label": label, "width": width, "height": height,
                    "url": f"/api/samples/{key}.png"})
    return out


@app.get("/api/samples/{key}.png")
def sample_image(key: str):
    if key not in SAMPLE_PNG:
        raise HTTPException(404, "Unknown sample.")
    return Response(SAMPLE_PNG[key], media_type="image/png")


def _guarded(work, *args):
    """Run CPU-heavy work off the event loop, at most two jobs at a time."""
    def run():
        if not busy.acquire(timeout=20):
            raise HTTPException(503, "The preview is busy. Try again in a moment.")
        try:
            return work(*args)
        finally:
            busy.release()
    return run_in_threadpool(run)


@app.post("/api/hide")
async def hide(
    message: Annotated[str, Form(max_length=4000)],
    password: Annotated[str, Form(min_length=1, max_length=200)],
    fill: Annotated[float, Form()] = 0.25,
    sample: Annotated[str | None, Form()] = None,
    image: Annotated[UploadFile | None, File()] = None,
):
    """Hide the message with both methods and measure how detectable each result is."""
    if not message.strip():
        raise HTTPException(400, "Write a message to hide.")
    if not 0.0 <= fill <= MAX_FILL:
        raise HTTPException(400, f"Payload size must be between 0 and {MAX_FILL:.0%} of capacity.")
    if image is not None and image.filename:
        cover_image = _fit(await _read_image(image))
    elif sample in SAMPLE_PNG:
        cover_image = Image.open(io.BytesIO(SAMPLE_PNG[sample])).convert("RGB")
    else:
        raise HTTPException(400, "Choose a sample image or upload one.")
    return await _guarded(_hide, cover_image, message, password, fill)


def _hide(cover_image: Image.Image, message: str, password: str, fill: float) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.png"
        cover_image.save(cover, format="PNG")
        limit = max_message_bytes(cover)
        if len(message.encode("utf-8")) > limit:
            raise HTTPException(400, f"This image holds at most {limit:,} bytes of message.")
        clean = _detect(cover)
        results = {}
        for method in ("sequential", "keyed"):
            stego = Path(tmp) / f"{method}.png"
            info = seal(cover, message, password, stego, method=method, fill=fill)
            found = _detect(stego)
            results[method] = {
                **info,
                "psnr_db": psnr_db(cover, stego),
                "ssim": ssim(cover, stego),
                "detection": found,
                "hcf_shift": found["hcf_ratio"] - clean["hcf_ratio"],
                "rs_flagged": found["rs_rate"] > RS_FLAG,
                "image": _data_uri(stego.read_bytes()),
                "changes": _data_uri(_changes_map(cover, stego)),
            }
        width, height = cover_image.size
        return {
            "cover": {"width": width, "height": height, "detection": clean},
            "rs_threshold": RS_FLAG,
            "results": results,
        }


@app.post("/api/reveal")
async def reveal(
    password: Annotated[str, Form(min_length=1, max_length=200)],
    image: Annotated[UploadFile, File()],
):
    """Recover a message from a stego PNG made by this toolkit."""
    upload = await _read_image(image)
    if upload.format != "PNG":
        raise HTTPException(400, "Use the PNG this preview made. JPEG compression erases the message.")
    return await _guarded(_reveal, upload, password)


def _reveal(upload: Image.Image, password: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "stego.png"
        upload.convert("RGB").save(path, format="PNG")
        try:
            message, method = open_package(path, password)
        except ValueError:
            raise HTTPException(
                404, "No message found. Check the password, and that the image is the unaltered PNG."
            ) from None
        return {"message": message, "method": method}


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = STATIC / path
        return FileResponse(f if path and f.is_file() and STATIC in f.resolve().parents
                            else STATIC / "index.html")
