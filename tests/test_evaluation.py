import numpy as np
from PIL import Image

from src.evaluation import bit_error_rate, evaluate_embedding


def test_bit_error_rate():
    assert bit_error_rate(b"\x00", b"\x00") == 0.0
    assert bit_error_rate(b"\x00", b"\xff") == 1.0
    assert bit_error_rate(b"a", b"ab") == 1.0


def test_embedding_metrics(tmp_path):
    cover = tmp_path / "cover.png"
    stego = tmp_path / "stego.png"
    rng = np.random.default_rng(7)
    Image.fromarray(rng.integers(0, 256, (96, 96, 3), dtype=np.uint8)).save(cover)
    result = evaluate_embedding(cover, b"benchmark payload", stego)
    assert result["roundtrip_success"] is True
    assert result["bit_error_rate"] == 0.0
    assert result["mse"] >= 0.0
    assert result["psnr_db"] > 40.0
