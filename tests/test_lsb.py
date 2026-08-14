import numpy as np
from PIL import Image
import pytest

from src.lsb_stego import capacity_bytes, embed_data, extract_data


def make_cover(path, size=(64, 64)):
    rng = np.random.default_rng(42)
    Image.fromarray(rng.integers(0, 256, (*size, 3), dtype=np.uint8)).save(path)


def test_lsb_roundtrip(tmp_path):
    cover = tmp_path / "cover.png"
    stego = tmp_path / "stego.png"
    make_cover(cover)
    payload = b"authenticated payload"
    embed_data(cover, payload, stego)
    assert extract_data(stego) == payload


def test_capacity_rejects_oversized_payload(tmp_path):
    cover = tmp_path / "cover.png"
    stego = tmp_path / "stego.png"
    make_cover(cover, (8, 8))
    with pytest.raises(ValueError, match="capacity"):
        embed_data(cover, b"x" * (capacity_bytes(cover) + 1), stego)
