from cryptography.exceptions import InvalidTag
import pytest

from src.crypto_utils import decrypt_message, derive_key_from_password, encrypt_message, generate_salt


def test_encrypt_decrypt_roundtrip():
    salt = generate_salt()
    key = derive_key_from_password("correct horse battery staple", salt)
    token = encrypt_message("hello steganography", key)
    assert decrypt_message(token, key) == "hello steganography"


def test_wrong_password_fails_authentication():
    salt = generate_salt()
    token = encrypt_message("secret", derive_key_from_password("right", salt))
    wrong_key = derive_key_from_password("wrong", salt)
    with pytest.raises(InvalidTag):
        decrypt_message(token, wrong_key)
