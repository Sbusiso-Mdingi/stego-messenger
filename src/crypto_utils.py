import os
import base64
from typing import Tuple
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

DEFAULT_ITERATIONS = 390_000 
SALT_SIZE = 16 

def generate_salt(length: int = SALT_SIZE) -> bytes:
    """Return cryptographically secure random salt."""
    return os.urandom(length)

def derive_key_from_password(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> bytes:
    """
    Derive a Fernet-compatible key from a password using PBKDF2-HMAC-SHA256.
    Returns the base64-url-safe-encoded 32-byte key usable by Fernet.
    """
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,          
        salt=salt,
        iterations=iterations,
    )
    key = kdf.derive(password_bytes)
    return base64.urlsafe_b64encode(key)

def encrypt_message(message: str, key: bytes) -> bytes:
    """
    Encrypt plaintext message (string) using provided Fernet key (bytes).
    key must be base64 urlsafe 32-byte key (Fernet format).
    """
    f = Fernet(key)
    return f.encrypt(message.encode('utf-8'))

def decrypt_message(token: bytes, key: bytes) -> str:
    """
    Decrypt ciphertext token using provided Fernet key.
    Returns the plaintext string.
    """
    f = Fernet(key)
    return f.decrypt(token).decode('utf-8')
