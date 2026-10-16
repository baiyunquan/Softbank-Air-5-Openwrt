#!/usr/bin/env python3
"""Reproduce/check CKB01 board-2.bin with the pinned Qualcomm encoder."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "devices/oppo_ckb01/firmware"
DESTINATION = ROOT / "devices/oppo_ckb01/files/lib/firmware/ath11k/IPQ8074/hw2.0/board-2.bin"
RAW_SHA256 = "9fdaff50396c03e097f713067df149be3c9b1d36689e4d20eff455f00c886944"
ENCODER_SHA256 = "4a2181d16d6ff35d60773b75aaa1bbe349afea7f03d4d2d97a596b81636a9e87"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    raw = (SOURCE / "bdwlan.bin").read_bytes()
    encoder = ROOT / "tools/ath11k-bdencoder"
    if len(raw) != 131072 or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        parser.error("OEM BDF size/hash mismatch")
    if hashlib.sha256(encoder.read_bytes()).hexdigest() != ENCODER_SHA256:
        parser.error("pinned Qualcomm encoder hash mismatch")
    with tempfile.TemporaryDirectory(prefix="ckb01-bdf-") as temporary:
        generated = Path(temporary) / "board-2.bin"
        subprocess.run(["python3", str(encoder), "-c", "board-2.json", "-o", str(generated)],
                       cwd=SOURCE, check=True, capture_output=True)
        data = generated.read_bytes()
        if args.check:
            if not args.output.is_file() or args.output.read_bytes() != data:
                parser.error("board-2.bin differs from the pinned OEM BDF/encoder output")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(data)
    print(f"{hashlib.sha256(data).hexdigest()}  {args.output}")


if __name__ == "__main__":
    main()
