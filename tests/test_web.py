import base64
import io

import pytest
from PIL import Image

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from web.service.main import app

client = TestClient(app)


def _png(data_uri: str) -> bytes:
    return base64.b64decode(data_uri.split(",", 1)[1])


def test_samples_are_listed_and_served():
    samples = client.get("/api/samples").json()
    assert {s["id"] for s in samples} >= {"coffee", "astronaut"}
    r = client.get(samples[0]["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_hide_compares_both_methods_and_reveal_reads_them_back():
    r = client.post("/api/hide", data={"message": "hello jozi", "password": "pw",
                                       "fill": "0.25", "sample": "coffee"})
    assert r.status_code == 200, r.text
    body = r.json()
    seq, keyed = body["results"]["sequential"], body["results"]["keyed"]
    assert seq["rs_flagged"] and not keyed["rs_flagged"]
    assert keyed["detection"]["rs_rate"] < seq["detection"]["rs_rate"]
    for method, result in (("sequential", seq), ("keyed", keyed)):
        files = {"image": ("s.png", _png(result["image"]), "image/png")}
        out = client.post("/api/reveal", data={"password": "pw"}, files=files)
        assert out.json() == {"message": "hello jozi", "method": method}
    wrong = client.post("/api/reveal", data={"password": "nope"},
                        files={"image": ("s.png", _png(keyed["image"]), "image/png")})
    assert wrong.status_code == 404


def test_uploads_are_scaled_and_jpeg_reveal_is_refused():
    big = io.BytesIO()
    Image.new("RGB", (1600, 900), (120, 90, 60)).save(big, format="JPEG")
    r = client.post("/api/hide", data={"message": "m", "password": "pw", "fill": "0"},
                    files={"image": ("big.jpg", big.getvalue(), "image/jpeg")})
    assert r.status_code == 200, r.text
    assert max(r.json()["cover"]["width"], r.json()["cover"]["height"]) == 640
    out = client.post("/api/reveal", data={"password": "pw"},
                      files={"image": ("big.jpg", big.getvalue(), "image/jpeg")})
    assert out.status_code == 400


def test_bad_input_is_rejected():
    assert client.post("/api/hide", data={"message": "m", "password": "pw"}).status_code == 400
    assert client.post("/api/hide", data={"message": "m", "password": "pw", "sample": "coffee",
                                          "fill": "0.95"}).status_code == 400
    assert client.get("/").status_code in (200, 404)
    assert "frame-ancestors" in client.get("/api/health").headers["content-security-policy"]
