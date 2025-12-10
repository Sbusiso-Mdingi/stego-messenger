import streamlit as st
from PIL import Image
import tempfile
import os
import base64
import sys
import io
import zipfile
import cv2

# ----------------------------
# Fix Python path so /src works
# ----------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# ----------------------------
# Project Imports (after path fix)
# ----------------------------
from src.crypto_utils import (
    generate_salt,
    derive_key_from_password,
    encrypt_message,
    decrypt_message,
    DEFAULT_ITERATIONS
)

from src.lsb_stego import embed_data, extract_data
from src.metadata import save_metadata, load_metadata
from src.attacks import (
    jpeg_compress,
    add_gaussian_noise,
    crop_image,
    resize_image
)

from src.lsb_stego import embed_data, extract_data
from src.metadata import save_metadata, load_metadata

from src.steganalysis import lsb_anomaly_score

st.set_page_config(page_title="Secure Steganography System", layout="centered")

st.title("🔐 Secure Steganography System")
st.caption("Encrypt • Embed • Extract hidden messages inside images")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔒 Embed Message",
    "🔓 Extract Message",
    "⚔️ Attack Simulation",
    "🛡 Steganalysis"
])


# -------------------------------
# EMBED TAB
# -------------------------------
with tab1:
    st.subheader("Hide an Encrypted Message in an Image")

    uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

    password = st.text_input("Password", type="password")
    message = st.text_area("Secret Message")

    if st.button("Encrypt & Embed"):
        if not uploaded_image or not password or not message:
            st.error("Please upload an image, enter a password, and write a message.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input.png")
                output_path = os.path.join(tmpdir, "stego.png")
                meta_path = os.path.join(tmpdir, "stego_meta.json")

                # Save uploaded image
                with open(input_path, "wb") as f:
                    f.write(uploaded_image.getbuffer())

                # Generate salt and key
                salt = generate_salt()
                key = derive_key_from_password(password, salt)

                salt_b64 = base64.urlsafe_b64encode(salt).decode()

                # Save metadata
                save_metadata(meta_path, salt_b64, DEFAULT_ITERATIONS)

                # Encrypt and embed
                ciphertext = encrypt_message(message, key)
                embed_data(input_path, ciphertext, output_path)

                # Display result
                st.success("✅ Message successfully hidden in image!")
                st.image(output_path, caption="Stego Image", use_column_width=True)

                # Download files
                

                # ----------------------------
                # Create ZIP in memory
                # ----------------------------
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w") as z:
                    z.write(output_path, arcname="stego_image.png")
                    z.write(meta_path, arcname="stego_meta.json")

                zip_buffer.seek(0)

                # ----------------------------
                # Single Download Button
                # ----------------------------
                st.download_button(
                    label="📦 Download Stego Package",
                    data=zip_buffer,
                    file_name="stego_package.zip",
                mime="application/zip"
                )


# -------------------------------
# EXTRACT TAB
# -------------------------------
with tab2:
    st.subheader("Extract a Hidden Message")

    stego_image = st.file_uploader("Upload a stego image", type=["png", "jpg", "jpeg"], key="stego")
    meta_file = st.file_uploader("Upload metadata file", type=["json"], key="meta")
    password_extract = st.text_input("Password to decrypt", type="password", key="pwd")

    if st.button("Extract & Decrypt"):
        if not stego_image or not meta_file or not password_extract:
            st.error("Please upload stego image, metadata file, and password.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                stego_path = os.path.join(tmpdir, "stego.png")
                meta_path = os.path.join(tmpdir, "stego_meta.json")

                # Save files
                with open(stego_path, "wb") as f:
                    f.write(stego_image.getbuffer())

                with open(meta_path, "wb") as f:
                    f.write(meta_file.getbuffer())

                # Load metadata
                meta = load_metadata(meta_path)
                salt = base64.urlsafe_b64decode(meta["salt"])
                iterations = meta["iterations"]

                # Derive key
                key = derive_key_from_password(password_extract, salt, iterations)

                # Extract + decrypt
                try:
                    hidden_data = extract_data(stego_path)
                    plaintext = decrypt_message(hidden_data, key)
                    st.success("✅ Message successfully recovered!")
                    st.text_area("Recovered Message:", plaintext)
                except Exception as e:
                    st.error(f"❌ Failed to extract/decrypt: {str(e)}")

# -------------------------------
# ATTACK SIMULATION TAB
# -------------------------------
with tab3:
    st.subheader("⚔️ Steganography Attack Simulator")

    attack_image = st.file_uploader(
        "Upload a stego image to attack",
        type=["png", "jpg", "jpeg"],
        key="attack_img"
    )

    attack_type = st.selectbox(
        "Choose attack type",
        ["JPEG Compression", "Gaussian Noise", "Cropping", "Resize"]
    )

    run_attack = st.button("Run Attack")

    if run_attack and attack_image:
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "input.png")
            out_path = os.path.join(tmpdir, "attacked.png")

            # Save uploaded image
            with open(img_path, "wb") as f:
                f.write(attack_image.getbuffer())

            img = cv2.imread(img_path)

            # Apply selected attack
            if attack_type == "JPEG Compression":
                attacked = jpeg_compress(img_path)
            elif attack_type == "Gaussian Noise":
                attacked = add_gaussian_noise(img)
            elif attack_type == "Cropping":
                attacked = crop_image(img)
            else:
                attacked = resize_image(img)

            # Save attacked image
            cv2.imwrite(out_path, attacked)

            st.image(out_path, caption=f"{attack_type} Applied", use_column_width=True)

            # Allow download
            with open(out_path, "rb") as f:
                st.download_button(
                    "📥 Download Attacked Image",
                    data=f,
                    file_name="attacked_image.png"
                )
                
# -------------------------------
# STEGANALYSIS TAB
# -------------------------------
with tab4:
    st.subheader("🛡 Steganography Detection")

    analysis_img = st.file_uploader(
        "Upload an image to analyze",
        type=["png", "jpg", "jpeg"],
        key="analysis"
    )

    if st.button("Analyze Image"):
        if analysis_img:
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = os.path.join(tmpdir, "analysis.png")

                with open(img_path, "wb") as f:
                    f.write(analysis_img.getbuffer())

                score = lsb_anomaly_score(img_path)

                st.metric("Suspicion Score", f"{score:.4f}")

                if score > 0.8:
                    st.error("⚠️ High likelihood of hidden data detected")
                elif score > 0.5:
                    st.warning("⚠️ Possible hidden data detected")
                else:
                    st.success("✅ Image appears clean")

