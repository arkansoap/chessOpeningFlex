#!/usr/bin/env python3
"""Download the native Stockfish engine into `backend/.tools/stockfish/`.

The batch analysis of imported games runs on the server, where a native engine
is far faster than the WASM build the browser uses. Distribution packages are
often several major versions behind, so this fetches the official release from
the Stockfish GitHub repository and checks it against a pinned SHA-256.

Usage (from backend/):  python scripts/fetch_stockfish.py
Only Linux x86-64 is covered; elsewhere install Stockfish yourself (it is
found on PATH) or set STOCKFISH_PATH.
"""
from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

VERSION = "sf_19"
ASSET = "stockfish-linux-x86-64-universal.tar.gz"
SHA256 = "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f"
URL = f"https://github.com/official-stockfish/Stockfish/releases/download/{VERSION}/{ASSET}"
DEST = Path(__file__).resolve().parents[1] / ".tools" / "stockfish"


def main() -> int:
    if sys.platform != "linux" or platform.machine() not in ("x86_64", "AMD64"):
        print("Unsupported platform: install Stockfish manually and set STOCKFISH_PATH.")
        return 1
    target = DEST / "stockfish"
    if target.exists():
        print(f"Already present: {target}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / ASSET
        print(f"Downloading {URL} ...")
        with urllib.request.urlopen(URL, timeout=120) as resp, archive.open("wb") as out:
            shutil.copyfileobj(resp, out)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != SHA256:
            print(f"Checksum mismatch: expected {SHA256}, got {digest}")
            return 1
        extract_dir = Path(tmp) / "extracted"
        with tarfile.open(archive) as tar:
            tar.extractall(extract_dir, filter="data")
        binaries = [
            p
            for p in extract_dir.rglob("*")
            if p.is_file() and p.name.startswith("stockfish") and p.suffix == ""
        ]
        if not binaries:
            print("No engine binary found in the archive.")
            return 1
        DEST.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binaries[0], target)
        target.chmod(0o755)
        for licence in extract_dir.rglob("Copying.txt"):
            shutil.copy2(licence, DEST / "Copying.txt")
            break
    print(f"Stockfish installed: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
