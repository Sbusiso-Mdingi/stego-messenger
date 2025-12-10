import json

def save_metadata(path: str, salt_b64: str, iterations: int):
    data = {
        "salt": salt_b64,
        "iterations": iterations,
        "kdf": "PBKDF2-HMAC-SHA256"
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_metadata(path: str):
    with open(path, "r") as f:
        return json.load(f)
