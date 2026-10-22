import numpy as np
import pytest
from PIL import Image
from skimage import data

from src.lsb_stego import capacity_bytes, embed_data
from src.steganalysis import (
    chi_square_attack,
    lsb_diagnostics,
    rs_analysis,
)


def _cover(path):
    Image.fromarray(data.astronaut().astype(np.uint8), mode="RGB").save(path)


def _embed_fraction(cover, out, fraction, seed=0):
    """Sequential LSB replacement over the given fraction of capacity."""
    arr = np.asarray(Image.open(cover).convert("RGB"), dtype=np.uint8).copy()
    flat = arr.reshape(-1)
    n = int(flat.size * fraction)
    rng = np.random.default_rng(seed)
    flat[:n] = (flat[:n] & 0xFE) | rng.integers(0, 2, n, dtype=np.uint8)
    Image.fromarray(arr, mode="RGB").save(out)


def test_rs_estimates_track_embedding_rate(tmp_path):
    cover = tmp_path / "cover.png"
    _cover(cover)
    estimates = []
    for fraction in (0.0, 0.25, 0.5, 0.9):
        stego = tmp_path / f"s{fraction}.png"
        _embed_fraction(cover, stego, fraction)
        estimates.append(rs_analysis(stego)["estimated_embedding_rate"])
    # Clean cover reads near zero and the estimate increases with the true rate.
    assert estimates[0] < 0.1
    assert estimates == sorted(estimates)
    assert estimates[-1] > 0.5


def test_rs_absolute_error_is_small(tmp_path):
    cover = tmp_path / "cover.png"
    _cover(cover)
    for fraction in (0.1, 0.25, 0.5):
        stego = tmp_path / f"s{fraction}.png"
        _embed_fraction(cover, stego, fraction)
        est = rs_analysis(stego)["estimated_embedding_rate"]
        assert abs(est - fraction) < 0.2


def test_rs_flags_saturation_as_unreliable(tmp_path):
    cover = tmp_path / "cover.png"
    _cover(cover)
    stego = tmp_path / "full.png"
    _embed_fraction(cover, stego, 1.0)
    result = rs_analysis(stego)
    # A fully embedded LSB plane is the method's singular point.
    assert result["estimated_embedding_rate"] > 0.85


def test_chi_square_rises_with_embedding(tmp_path):
    cover = tmp_path / "cover.png"
    _cover(cover)
    clean = chi_square_attack(cover)["mean_embedding_probability"]
    stego = tmp_path / "full.png"
    _embed_fraction(cover, stego, 1.0)
    embedded = chi_square_attack(stego)["mean_embedding_probability"]
    assert embedded > clean
    assert embedded > 0.9


def test_real_payload_is_detectable_even_though_encrypted(tmp_path):
    """AES-GCM ciphertext is random, so embedding it still lifts the RS estimate."""
    cover = tmp_path / "cover.png"
    _cover(cover)
    stego = tmp_path / "stego.png"
    payload = np.random.default_rng(1).integers(
        0, 256, capacity_bytes(cover) // 4, dtype=np.uint8
    ).tobytes()
    embed_data(cover, payload, stego)
    assert rs_analysis(stego)["estimated_embedding_rate"] > rs_analysis(cover)[
        "estimated_embedding_rate"
    ]


def test_diagnostics_are_descriptive_only(tmp_path):
    cover = tmp_path / "cover.png"
    _cover(cover)
    diag = lsb_diagnostics(cover)
    assert set(diag) == {
        "lsb_one_ratio",
        "lsb_entropy_bits",
        "lsb_transition_rate",
        "balance_deviation",
    }
    assert 0.0 <= diag["lsb_one_ratio"] <= 1.0


def test_tiny_image_rejected():
    with pytest.raises(ValueError):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = f"{d}/t.png"
            Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8), mode="RGB").save(path)
            chi_square_attack(path)


def test_hcf_com_drops_with_lsb_matching(tmp_path):
    from src.lsb_stego import embed_data as embed
    from src.steganalysis import hcf_com_calibrated

    cover = tmp_path / "cover.png"
    _cover(cover)
    stego = tmp_path / "matched.png"
    payload = np.random.default_rng(0).integers(0, 256, 60000, dtype=np.uint8).tobytes()
    embed(cover, payload, stego, method="keyed", key=b"k", seed=0)
    assert hcf_com_calibrated(stego)["ratio"] < hcf_com_calibrated(cover)["ratio"]
