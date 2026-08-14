# Evaluation Protocol — v0.2

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

## LSB diagnostics

The toolkit reports:

- proportion of ones in the grayscale LSB plane;
- binary entropy of that plane;
- adjacent-bit transition rate;
- deviation from a 50/50 bit balance.

These are **descriptive statistics**. They are not probabilities that an image contains hidden data and should not be presented as a validated steganalysis classifier.

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

## Planned v0.3 work

SSIM, dataset manifests, JSON/CSV experiment exports, payload-size sweeps, confidence intervals, and external baseline comparisons are tracked in `ROADMAP.md` and GitHub Issues.
