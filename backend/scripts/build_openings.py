#!/usr/bin/env python3
"""Build `app/data/openings.json` from the lichess-org/chess-openings dataset.

The dataset (CC0) names ~3,900 opening positions. Each line is resolved to the
position it reaches, so that a game can be named after the deepest named
position it passes through, whatever the move order.

Usage (from backend/):  python scripts/build_openings.py [dir-with-tsv-files]
Without an argument the five TSV files are downloaded from GitHub.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

import chess

BASE_URL = "https://raw.githubusercontent.com/lichess-org/chess-openings/master"
OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "openings.json"


def read_tsv(letter: str, local_dir: Path | None) -> str:
    if local_dir is not None:
        return (local_dir / f"{letter}.tsv").read_text(encoding="utf-8")
    with urllib.request.urlopen(f"{BASE_URL}/{letter}.tsv", timeout=30) as resp:
        return resp.read().decode("utf-8")


def main() -> None:
    local_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    openings: dict[str, list] = {}
    for letter in "abcde":
        reader = csv.DictReader(io.StringIO(read_tsv(letter, local_dir)), delimiter="\t")
        for row in reader:
            board = chess.Board()
            sans: list[str] = []
            for token in row["pgn"].split():
                if token.endswith("."):
                    continue
                board.push_san(token)
                sans.append(token)
            # epd -> [eco, name, ply, line]; the deepest line wins on collisions.
            key = board.epd()
            current = openings.get(key)
            if current is None or len(sans) > current[2]:
                openings[key] = [row["eco"], row["name"], len(sans), " ".join(sans)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(openings, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{len(openings)} named positions -> {OUT}")


if __name__ == "__main__":
    main()
