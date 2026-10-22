import numpy as np
import pytest
from PIL import Image
from skimage import data

from src.package import OVERHEAD, max_message_bytes, open_package, seal
from src.steganalysis import rs_analysis


@pytest.fixture
def cover(tmp_path):
    path = tmp_path / "cover.png"
    Image.fromarray(data.astronaut()[:256, :256].astype(np.uint8), mode="RGB").save(path)
    return path


@pytest.mark.parametrize("method", ["keyed", "sequential"])
def test_seal_and_open_need_only_the_png_and_password(cover, tmp_path, method):
    stego = tmp_path / "stego.png"
    info = seal(cover, "meet at the station, 7pm", "correct horse", stego, method=method)
    assert info["payload_bytes"] == OVERHEAD + len("meet at the station, 7pm")
    assert open_package(stego, "correct horse") == ("meet at the station, 7pm", method)


def test_wrong_password_and_clean_image_fail(cover, tmp_path):
    stego = tmp_path / "stego.png"
    seal(cover, "secret", "right", stego)
    with pytest.raises(ValueError):
        open_package(stego, "wrong")
    with pytest.raises(ValueError):
        open_package(cover, "right")


def test_fill_pads_to_the_requested_share_of_capacity(cover, tmp_path):
    stego = tmp_path / "stego.png"
    info = seal(cover, "short", "pw", stego, fill=0.3)
    assert abs(info["capacity_utilization"] - 0.3) < 0.001
    assert open_package(stego, "pw")[0] == "short"


def test_unicode_and_capacity_limit(cover, tmp_path):
    stego = tmp_path / "stego.png"
    seal(cover, "Sawubona, umhlaba 🌍", "pw", stego)
    assert open_package(stego, "pw")[0] == "Sawubona, umhlaba 🌍"
    with pytest.raises(ValueError, match="at most"):
        seal(cover, "x" * (max_message_bytes(cover) + 1), "pw", stego)


def test_keyed_padding_is_harder_for_rs_than_sequential(cover, tmp_path):
    keyed, sequential = tmp_path / "k.png", tmp_path / "s.png"
    seal(cover, "m", "pw", keyed, method="keyed", fill=0.5)
    seal(cover, "m", "pw", sequential, method="sequential", fill=0.5)
    clean = rs_analysis(cover)["estimated_embedding_rate"]
    assert rs_analysis(sequential)["estimated_embedding_rate"] > clean + 0.3
    assert rs_analysis(keyed)["estimated_embedding_rate"] < clean + 0.1
