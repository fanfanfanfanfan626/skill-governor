#!/usr/bin/env python3
"""Build or verify the deterministic repository-source checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SHA256SUMS"
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "dist"}
EXCLUDED_FILES = {"SHA256SUMS"}


def source_files() -> list[Path]:
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
            and path.name not in EXCLUDED_FILES
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def render() -> str:
    lines = []
    for path in source_files():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != expected:
            raise SystemExit("SHA256SUMS is stale; run tools/build_source_manifest.py")
        print(f"Verified {len(source_files())} source checksums.")
        return 0
    MANIFEST.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {len(source_files())} source checksums.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
