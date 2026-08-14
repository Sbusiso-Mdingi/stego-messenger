# Copyright 2026 Sbusiso Mdingi
# SPDX-License-Identifier: Apache-2.0

"""Metadata serialization for v2 stego packages."""

from __future__ import annotations

import json
from pathlib import Path


def save_metadata(path: str | Path, salt_b64: str, *, n: int, r: int, p: int) -> None:
    data = {
        "format_version": 2,
        "cipher": "AES-256-GCM",
        "kdf": "scrypt",
        "salt": salt_b64,
        "scrypt": {"n": n, "r": r, "p": p},
    }
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_metadata(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format_version") != 2:
        raise ValueError("unsupported metadata format version")
    return data
