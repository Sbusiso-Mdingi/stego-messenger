# test_stego.py
from src.crypto_utils import (
    generate_salt,
    derive_key_from_password,
    encrypt_message,
    decrypt_message,
    DEFAULT_ITERATIONS
)
from src.lsb_stego import embed_data, extract_data
from src.metadata import save_metadata, load_metadata

from tkinter import Tk
from tkinter.filedialog import askopenfilename
import base64
import os

Tk().withdraw()

# Select image
print("Select an image...")
image_path = askopenfilename(
    title="Select Image",
    filetypes=[("Images", "*.png *.jpg *.jpeg")]
)
if not image_path:
    raise Exception("No image selected")

# Ask for password
password = input("Enter a password: ").strip()
if not password:
    raise Exception("Password cannot be empty")

# Generate salt + key
salt = generate_salt()
iterations = DEFAULT_ITERATIONS

key = derive_key_from_password(password, salt, iterations)

salt_b64 = base64.urlsafe_b64encode(salt).decode()

# Save metadata
meta_path = "stego_meta.json"
save_metadata(meta_path, salt_b64, iterations)

print(f"\n✅ Metadata saved to {meta_path}")

# Ask for message
message = input("Enter a secret message: ")

# Encrypt
ciphertext = encrypt_message(message, key)

# Embed
output_image = "secure_stego.png"
embed_data(image_path, ciphertext, output_image)

print(f"\n✅ Encrypted message embedded in {output_image}")

# -------------------------------
# Simulate later decryption
# -------------------------------
print("\n🔎 Simulating later extraction...")

meta = load_metadata(meta_path)
salt_loaded = base64.urlsafe_b64decode(meta["salt"])
iters_loaded = meta["iterations"]

# Re-derive key
key_loaded = derive_key_from_password(password, salt_loaded, iters_loaded)

# Extract and decrypt
secret_data = extract_data(output_image)
plaintext = decrypt_message(secret_data, key_loaded)

print("\n✅ Successfully decrypted message:")
print(plaintext)
