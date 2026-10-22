import numpy as np
import pytest
from PIL import Image

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


def test_keyed_roundtrip_and_wrong_key(tmp_path):
    cover = tmp_path / "cover.png"
    stego = tmp_path / "stego.png"
    make_cover(cover)
    payload = b"scattered payload"
    embed_data(cover, payload, stego, method="keyed", key=b"k1", seed=0)
    assert extract_data(stego, method="keyed", key=b"k1") == payload
    try:
        assert extract_data(stego, method="keyed", key=b"k2") != payload
    except ValueError:
        pass


def test_keyed_changes_each_value_by_at_most_one(tmp_path):
    cover = tmp_path / "cover.png"
    stego = tmp_path / "stego.png"
    make_cover(cover)
    embed_data(cover, b"x" * 300, stego, method="keyed", key=b"k", seed=1)
    a = np.asarray(Image.open(cover), dtype=np.int16)
    b = np.asarray(Image.open(stego), dtype=np.int16)
    diff = np.abs(a - b)
    assert diff.max() == 1
    # Changes are spread over the image rather than packed into the first rows.
    rows_touched = np.flatnonzero(diff.any(axis=(1, 2)))
    assert rows_touched.max() > 48


def test_keyed_needs_a_key(tmp_path):
    cover = tmp_path / "cover.png"
    make_cover(cover)
    with pytest.raises(ValueError, match="key"):
        embed_data(cover, b"x", tmp_path / "s.png", method="keyed")
