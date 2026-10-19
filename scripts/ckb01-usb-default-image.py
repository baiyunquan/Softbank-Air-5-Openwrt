#!/usr/bin/env python3
"""Repackage an existing CKB01 FIT for the verified OEM usb 0:0 path."""

import argparse
import ctypes
import ctypes.util
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


IMAGE_NAME = "air5-ckb01-usb-default-v2.img"
IMAGE_BYTES = 256 * 1024 * 1024
SECTOR_BYTES = 512
BOOT_FILE = "uImage-initramfs.itb"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(*args):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True)
    require(result.returncode == 0,
            f"{args[0]} failed: {result.stdout.strip()} {result.stderr.strip()}")
    return result.stdout


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_existing_fit(fit, expected_initramfs_sha256, work):
    """Recover the exact embedded zstd frame and reuse the existing FIT checks."""
    spec = importlib.util.spec_from_file_location(
        "ckb01_fit", Path(__file__).with_name("ckb01-fit.py"))
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    kernel = work / "kernel.gz"
    command("dumpimage", "-T", "flat_dt", "-p", "0", "-o", kernel, fit)
    image = gzip.decompress(kernel.read_bytes())
    library = ctypes.util.find_library("zstd")
    require(library is not None, "libzstd is required to recover the embedded initramfs")
    zstd = ctypes.CDLL(library)
    zstd.ZSTD_findFrameCompressedSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    zstd.ZSTD_findFrameCompressedSize.restype = ctypes.c_size_t
    zstd.ZSTD_isError.argtypes = [ctypes.c_size_t]
    zstd.ZSTD_isError.restype = ctypes.c_uint
    buffer = ctypes.create_string_buffer(image)
    offset = 0
    matches = []
    while True:
        offset = image.find(b"\x28\xb5\x2f\xfd", offset)
        if offset < 0:
            break
        length = zstd.ZSTD_findFrameCompressedSize(
            ctypes.byref(buffer, offset), len(image) - offset)
        if not zstd.ZSTD_isError(length) and 0 < length <= len(image) - offset:
            frame = image[offset:offset + length]
            if hashlib.sha256(frame).hexdigest() == expected_initramfs_sha256:
                matches.append(frame)
        offset += 1
    require(len(matches) == 1, "expected exactly one embedded initramfs matching the source build SHA256")
    initramfs = work / "initramfs_inc_data"
    initramfs.write_bytes(matches[0])
    _, paths, report = checker.verify_fit(fit, initramfs, work, wireless=True)
    report["initramfs_input"] = "recovered from the unchanged source FIT"
    return paths, report


def verify_volume(image, fit, work):
    require(image.stat().st_size == IMAGE_BYTES, "USB image must be exactly 256 MiB")
    with image.open("rb") as stream:
        header = stream.read(SECTOR_BYTES)
    require(header[510:512] == b"\x55\xaa", "missing FAT boot-sector signature")
    require(header[54:62] == b"FAT16   ", "LBA 0 must contain the FAT16 BPB")
    require(header[446:510] == bytes(64), "unexpected MBR partition entries")
    require(struct.unpack_from("<H", header, 11)[0] == SECTOR_BYTES,
            "FAT sector size must be 512 bytes")
    require(header[13] == 8 and header[16] == 2,
            "expected 4096-byte clusters and two FAT copies")
    require(struct.unpack_from("<I", header, 28)[0] == 0,
            "whole-device FAT must have zero hidden sectors")
    sectors = (struct.unpack_from("<H", header, 19)[0] or
               struct.unpack_from("<I", header, 32)[0])
    require(sectors * SECTOR_BYTES == IMAGE_BYTES, "FAT volume does not cover the disk image")
    reserved = struct.unpack_from("<H", header, 14)[0]
    fat_sectors = struct.unpack_from("<H", header, 22)[0]
    root_entries = struct.unpack_from("<H", header, 17)[0]
    root_sectors = (root_entries * 32 + SECTOR_BYTES - 1) // SECTOR_BYTES
    clusters = (sectors - reserved - 2 * fat_sectors - root_sectors) // header[13]
    require(4085 <= clusters < 65525, "BPB cluster count is not FAT16")
    check = command("fsck.fat", "-n", image)
    listing = command("mdir", "-b", "-i", image, "::/").splitlines()
    require(len(listing) == 1 and listing[0].lower() == f"::/{BOOT_FILE.lower()}",
            "FAT root must contain only the stock boot filename")
    readback = work / "readback.itb"
    command("mcopy", "-i", image, f"::/{BOOT_FILE}", readback)
    require(readback.read_bytes() == fit.read_bytes(), "FAT readback differs from the existing FIT")
    return check.strip(), clusters


def package(fit, provenance_path, output):
    provenance = json.loads(provenance_path.read_text())
    require(provenance["source_run_conclusion"] == "success", "source firmware run was not successful")
    require(sha256(fit) == provenance["fit_sha256"], "source FIT SHA256 mismatch")
    require(fit.stat().st_size < IMAGE_BYTES - 4 * 1024 * 1024, "FIT does not fit in the boot volume")
    with fit.open("rb") as stream:
        require(stream.read(4) == b"\xd0\x0d\xfe\xed", "source is not a FIT/FDT")
    for tool in ("mkfs.fat", "fsck.fat", "mcopy", "mdir", "dumpimage", "fdtget", "zstd"):
        require(shutil.which(tool), f"missing packaging dependency: {tool}")
    output.mkdir(parents=True, exist_ok=True)
    require(not (output / IMAGE_NAME).exists(), "refusing to overwrite an existing USB image")
    with tempfile.TemporaryDirectory(prefix=".ckb01-default-", dir=output) as temporary:
        work = Path(temporary)
        paths, fit_report = verify_existing_fit(fit, provenance["initramfs_sha256"], work)
        image = work / IMAGE_NAME
        with image.open("wb") as stream:
            stream.truncate(IMAGE_BYTES)
        command("mkfs.fat", "--mbr=n", "-h", "0", "-g", "16/32", "-F", "16",
                "-S", SECTOR_BYTES, "-s", "8", "-i", "434b4232", "-n", "AIR5BOOT",
                image, IMAGE_BYTES // 1024)
        command("mcopy", "-i", image, fit, f"::/{BOOT_FILE}")
        filesystem_check, clusters = verify_volume(image, fit, work)
        report = {
            "image": IMAGE_NAME,
            "image_bytes": IMAGE_BYTES,
            "image_sha256": sha256(image),
            "layout": "whole-device FAT16, BPB at LBA 0, no MBR partition entries",
            "sector_bytes": SECTOR_BYTES,
            "cluster_bytes": 4096,
            "data_clusters": clusters,
            "hidden_sectors": 0,
            "root_file": BOOT_FILE,
            "fit_sha256": sha256(fit),
            "fit_readback": "byte-for-byte identical to the existing compiled FIT",
            "filesystem_check": filesystem_check,
            "compiled_firmware_reused": True,
            "firmware_rebuilt": False,
            "uboot_contract": {
                "reference": "oldcat618/ckb01 SPI backup, U-Boot 2016.01 (Mar 06 2021)",
                "bootcmd": "bootipq_usb",
                "bootargs": "console=ttyMSM0,115200n8",
                "bootdelay": 2,
                "commands": ["usb start",
                             f"fatload usb 0:0 0x44000000 {BOOT_FILE}",
                             "bootm 0x44000000"],
                "environment_modified": False,
            },
            "source": provenance,
            "hardware_validation": "not performed; target-unit bootloader version not read",
            "persistence": "existing initramfs RAM root; configuration resets on reboot",
        }
        (output / "source-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        (output / "fit-validation.json").write_text(json.dumps(fit_report, indent=2) + "\n")
        (output / "initramfs-files.txt").write_text("\n".join(sorted(paths)) + "\n")
        (output / "usb-image-report.json").write_text(json.dumps(report, indent=2) + "\n")
        image.rename(output / IMAGE_NAME)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fit", type=Path)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package(args.fit.resolve(), args.provenance.resolve(), args.output.resolve())
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CKB01 default-boot packaging failed: {error}\n")


if __name__ == "__main__":
    main()
