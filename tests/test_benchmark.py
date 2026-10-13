import json

from src import benchmark


def test_build_corpus_writes_rgb_pngs(tmp_path):
    paths = benchmark.build_corpus(tmp_path, names=("astronaut", "coffee"))
    assert len(paths) == 2
    for path in paths:
        assert path.exists() and path.suffix == ".png"


def test_mean_ci_degenerate_and_normal():
    one = benchmark._mean_ci([5.0])
    assert one.mean == one.ci_low == one.ci_high == 5.0
    many = benchmark._mean_ci([1.0, 2.0, 3.0, 4.0, 5.0])
    assert many.ci_low < many.mean < many.ci_high


def test_run_small_sweep_exports_json_and_csv(tmp_path):
    results = benchmark.run(
        fractions=(0.0, 0.25),
        seeds=(0, 1),
        names=("astronaut",),
        out_dir=tmp_path,
    )
    assert (tmp_path / "benchmark.json").exists()
    assert (tmp_path / "measurements.csv").exists()
    assert len(results["measurements"]) == 4
    assert results["environment"]["python"]
    # Recovery from lossless PNG is exact at every embedded point.
    assert all(m["roundtrip_success"] for m in results["measurements"])
    # The detector separates the clean control from the embedded point.
    by_fraction = {s["fraction"]: s for s in results["summary_by_fraction"]}
    assert (
        by_fraction[0.25]["rs_estimated_rate"]["mean"]
        > by_fraction[0.0]["rs_estimated_rate"]["mean"]
    )


def test_json_is_serialisable(tmp_path):
    benchmark.run(fractions=(0.1,), seeds=(0,), names=("coffee",), out_dir=tmp_path)
    reloaded = json.loads((tmp_path / "benchmark.json").read_text())
    assert reloaded["corpus"] == ["coffee.png"]
