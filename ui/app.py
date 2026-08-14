# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import zipfile

import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.crypto_utils import (  # noqa: E402
    DEFAULT_SCRYPT_N,
    DEFAULT_SCRYPT_P,
    DEFAULT_SCRYPT_R,
    decrypt_message,
    derive_key_from_password,
    encrypt_message,
    generate_salt,
)
from src.evaluation import evaluate_attacks, evaluate_embedding  # noqa: E402
from src.lsb_stego import capacity_bytes, embed_data, extract_data  # noqa: E402
from src.metadata import load_metadata, save_metadata  # noqa: E402
from src.steganalysis import lsb_diagnostics, lsb_randomness_score  # noqa: E402

st.set_page_config(page_title="Stego Messenger", layout="wide")
st.title("Stego Messenger")
st.caption("Experimental encrypted image steganography with evaluation-first reporting")
st.info("Research software: metrics are measurements or heuristics, not guarantees of undetectability or robustness.")

embed_tab, extract_tab, evaluation_tab, diagnostics_tab = st.tabs(
    ["Embed", "Extract", "Evaluate", "LSB diagnostics"]
)

with embed_tab:
    image = st.file_uploader("Cover image", type=["png", "jpg", "jpeg"], key="cover")
    password = st.text_input("Password", type="password", key="embed_password")
    message = st.text_area("Message")
    if image:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(image.getbuffer())
            cover_path = handle.name
        st.metric("Approximate payload capacity", f"{capacity_bytes(cover_path):,} bytes")
        os.unlink(cover_path)

    if st.button("Encrypt and embed", type="primary"):
        if not image or not password or not message:
            st.error("Provide a cover image, password, and message.")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                cover = os.path.join(tmp, "cover.png")
                stego = os.path.join(tmp, "stego.png")
                metadata = os.path.join(tmp, "metadata.json")
                with open(cover, "wb") as handle:
                    handle.write(image.getbuffer())

                salt = generate_salt()
                key = derive_key_from_password(password, salt)
                payload = encrypt_message(message, key)
                embed_data(cover, payload, stego)
                save_metadata(
                    metadata,
                    base64.urlsafe_b64encode(salt).decode("ascii"),
                    n=DEFAULT_SCRYPT_N,
                    r=DEFAULT_SCRYPT_R,
                    p=DEFAULT_SCRYPT_P,
                )

                bundle = io.BytesIO()
                with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.write(stego, "stego.png")
                    archive.write(metadata, "metadata.json")
                bundle.seek(0)
                st.success("Payload embedded in lossless PNG output.")
                st.image(stego)
                st.download_button(
                    "Download stego package", bundle, "stego-package.zip", "application/zip"
                )

with extract_tab:
    stego_upload = st.file_uploader("Stego PNG", type=["png"], key="extract_stego")
    metadata_upload = st.file_uploader("Metadata JSON", type=["json"], key="extract_metadata")
    password = st.text_input("Password", type="password", key="extract_password")
    if st.button("Extract and decrypt"):
        if not stego_upload or not metadata_upload or not password:
            st.error("Provide the stego PNG, metadata JSON, and password.")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                stego = os.path.join(tmp, "stego.png")
                metadata = os.path.join(tmp, "metadata.json")
                with open(stego, "wb") as handle:
                    handle.write(stego_upload.getbuffer())
                with open(metadata, "wb") as handle:
                    handle.write(metadata_upload.getbuffer())
                try:
                    meta = load_metadata(metadata)
                    salt = base64.urlsafe_b64decode(meta["salt"])
                    params = meta["scrypt"]
                    key = derive_key_from_password(password, salt, **params)
                    plaintext = decrypt_message(extract_data(stego), key)
                    st.success("Authenticated payload recovered.")
                    st.text_area("Recovered message", plaintext)
                except Exception as exc:
                    st.error(f"Recovery failed: {exc}")

with evaluation_tab:
    cover_upload = st.file_uploader(
        "Cover image", type=["png", "jpg", "jpeg"], key="eval_cover"
    )
    payload_text = st.text_input("Benchmark payload", value="reproducible benchmark payload")
    if st.button("Run benchmark") and cover_upload:
        with tempfile.TemporaryDirectory() as tmp:
            cover = os.path.join(tmp, "cover.png")
            stego = os.path.join(tmp, "stego.png")
            with open(cover, "wb") as handle:
                handle.write(cover_upload.getbuffer())
            payload = payload_text.encode("utf-8")
            metrics = evaluate_embedding(cover, payload, stego)
            attacks = evaluate_attacks(stego, payload, os.path.join(tmp, "attacks"))
            cols = st.columns(4)
            cols[0].metric("PSNR", f"{metrics['psnr_db']:.2f} dB")
            cols[1].metric("MSE", f"{metrics['mse']:.4f}")
            cols[2].metric("BER", f"{metrics['bit_error_rate']:.4f}")
            cols[3].metric("Capacity used", f"{metrics['capacity_utilization']:.2%}")
            st.subheader("Transformation recovery")
            st.dataframe(attacks, use_container_width=True)
            st.download_button(
                "Download metrics JSON",
                json.dumps({"embedding": metrics, "attacks": attacks}, indent=2),
                "benchmark.json",
                "application/json",
            )

with diagnostics_tab:
    image = st.file_uploader("Image", type=["png", "jpg", "jpeg"], key="diagnostic_image")
    if st.button("Compute diagnostics") and image:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(image.getbuffer())
            path = handle.name
        try:
            metrics = lsb_diagnostics(path)
            st.json(metrics)
            st.metric("LSB randomness heuristic", f"{lsb_randomness_score(path):.3f}")
            st.caption(
                "This score describes LSB-plane randomness. It is not a probability that steganography is present."
            )
        finally:
            os.unlink(path)
