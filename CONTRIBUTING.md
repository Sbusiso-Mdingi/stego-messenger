# Contributing

Thanks for helping improve Stego Messenger. The project is an experimental research toolkit, so reproducibility and accurate security claims matter more than feature count.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment with Python 3.10+.
3. Install development dependencies with `pip install -e '.[dev]'`.
4. Run `ruff check src tests` and `pytest -q` before opening a pull request.

## Contribution workflow

- Open or reference an issue for non-trivial changes.
- Keep pull requests focused and include tests for behavioural changes.
- Report measured results with the image set, parameters, random seed, and environment needed to reproduce them.
- Do not describe a heuristic steganalysis metric as a probability or detection guarantee.
- Do not add covert-networking, persistence, credential theft, malware delivery, or evasion features. The project scope is offline image steganography research and evaluation.

## Security research

Responsible robustness and detection research is welcome. See `SECURITY.md` for private vulnerability reporting.

By contributing, you agree that your contribution is licensed under Apache-2.0.
