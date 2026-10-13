# Evaluation Protocol — v0.3

The project is evaluation-first: claims should be supported by reproducible measurements rather than inferred from the presence of cryptography or steganography primitives.

## Embedding metrics

| Metric | Meaning |
|---|---|
| Round-trip success | Exact payload equality immediately after embedding/extraction |
| BER | Fraction of payload bits that differ from the expected payload |
| Capacity bytes | Maximum payload size after the 4-byte length header |
| Capacity utilisation | Payload bytes divided by available capacity |
| MSE | Mean squared pixel error between cover and stego images |
| PSNR | Peak signal-to-noise ratio derived from MSE |
| SSIM | Structural similarity (scikit-image, default window); 1.0 is identical |

## LSB diagnostics (descriptive, not a detector)

The toolkit reports:

- proportion of ones in the grayscale LSB plane;
- binary entropy of that plane;
- adjacent-bit transition rate;
- deviation from a 50/50 bit balance.

These are **descriptive statistics**. They are not probabilities that an image contains hidden data and should not be presented as a validated steganalysis classifier.

## Steganalysis detectors (calibrated)

Unlike the diagnostics above, these estimate whether and how much sequential LSB
replacement has taken place. They are used to measure how detectable the toolkit's own
embedding is.

| Detector | Output | Notes |
|---|---|---|
| Chi-square (Westfeld & Pfitzmann, 2000) | Mean/maximum embedding probability over image blocks | Coarse screen; high and image-dependent baseline on untouched natural images |
| RS analysis (Fridrich, Goljan & Du, 2001) | Estimated embedding rate in [0, 1] | Quantitative; tracks the true rate to within a few points up to ~0.9, flags its singular point near full saturation as unreliable |

The absolute message length is the RS rate times the LSB capacity. These are the classical
structural detectors; a learned classifier is tracked for v0.4 in `ROADMAP.md`.

## Benchmark

`python -m src.benchmark` runs a payload-size sweep across a fixed public-domain image
corpus (scikit-image samples) over several seeds, and writes `benchmark.json` and
`measurements.csv`. The JSON records per-payload means with 95% confidence intervals plus
every individual measurement. Results and interpretation are in `docs/benchmarks/`.

## Transformation protocol

v0.2 defines deterministic defaults for:

- JPEG round-trip at quality 70;
- Gaussian noise with standard deviation 5 and random seed 0;
- centred 95% crop;
- resize to 75% of original dimensions.

Each transformed image is saved and extraction is attempted. Failure is recorded rather than suppressed. A failed extraction is reported with BER = 1.0 for summary purposes.

## Reproducibility requirements

Any benchmark result intended for comparison should report:

- Stego Messenger version/commit;
- image source and dimensions;
- payload size/content generation method;
- transformation parameters and random seed;
- Python/runtime environment;
- all metrics, including failures.

## Remaining work

A transform-domain embedding baseline, error-correcting codes, an external-library
comparison and a learned steganalysis classifier are tracked in `ROADMAP.md`.
