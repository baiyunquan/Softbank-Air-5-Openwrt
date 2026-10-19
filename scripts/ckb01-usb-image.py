#!/usr/bin/env python3
"""Package a CKB01 FIT in an MBR/FAT16 USB image and verify the disk layout."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


IMAGE_NAME = "air5-ckb01-usb.img"
SECTOR_SIZE = 512
PARTITION_START = 2048
PARTITION_SECTORS = 524288
VOLUME_BYTES = PARTITION_SECTORS * SECTOR_SIZE
IMAGE_BYTES = (PARTITION_START + PARTITION_SECTORS) * SECTOR_SIZE


def command(*args, input=None):
    result = subprocess.run([str(arg) for arg in args], input=input,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stdout.strip()} {result.stderr.strip()}")
    return result.stdout


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(image, fit, work):
    require(image.stat().st_size == IMAGE_BYTES, "USB image must be 257 MiB")
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
        require(mbr[510:512] == b"\x55\xaa", "missing MBR signature")
        boot, _, kind, _, start, sectors = struct.unpack("<B3sB3sII", mbr[446:462])
        require((boot, kind, start, sectors) ==
                (0x80, 0x06, PARTITION_START, PARTITION_SECTORS),
                "expected bootable FAT16 primary partition 1 at LBA 2048")
        require(mbr[462:510] == bytes(48), "unexpected additional partitions")
        stream.seek(start * SECTOR_SIZE)
        bpb = stream.read(SECTOR_SIZE)
        require(bpb[510:512] == b"\x55\xaa" and bpb[54:62] == b"FAT16   ",
                "partition 1 is not FAT16")
        require(struct.unpack_from("<H", bpb, 11)[0] == SECTOR_SIZE and bpb[13] == 8,
                "expected 512-byte sectors and 4096-byte clusters")
        require(struct.unpack_from("<I", bpb, 28)[0] == PARTITION_START,
                "FAT hidden-sector count differs from partition start")
        require(struct.unpack_from("<I", bpb, 32)[0] == PARTITION_SECTORS,
                "FAT volume size differs from partition size")
        # fsck.fat has no offset option. Check an exact copy of partition 1;
        # no loop device, mount or sudo is needed on the Actions runner.
        stream.seek(start * SECTOR_SIZE)
        partition = work / "partition-1.fat"
        with partition.open("wb") as destination:
            shutil.copyfileobj(stream, destination, 1024 * 1024)
    command("sfdisk", "--verify", image)
    filesystem_check = command("fsck.fat", "-n", partition)
    extracted = work / "readback.itb"
    command("mcopy", "-i", f"{image}@@{PARTITION_START * SECTOR_SIZE}",
            "::/uimage-initramfs.itb", extracted)
    require(extracted.read_bytes() == fit.read_bytes(),
            "USB partition FIT differs from validated source FIT")
    return {
        "image": image.name,
        "image_bytes": IMAGE_BYTES,
        "image_sha256": sha256(image),
        "partition_table": "MBR / DOS",
        "partition_1": {
            "bootable": True, "type": "0x06 FAT16",
            "start_sector": PARTITION_START, "sectors": PARTITION_SECTORS,
            "volume_bytes": VOLUME_BYTES, "sector_bytes": SECTOR_SIZE,
            "cluster_bytes": 4096, "label": "AIR5BOOT",
            "root_file": "uimage-initramfs.itb",
        },
        "fit_sha256": sha256(fit),
        "fit_readback": "byte-for-byte identical",
        "filesystem_check": filesystem_check.strip(),
        "boot_method": "OEM bootipq_usb automatic USB loading",
        "hardware_validation": "pending boot using the MBR partition-1 image",
        "persistence": "RAM root; settings reset on reboot",
    }


def package(fit, output):
    require(fit.is_file() and 0 < fit.stat().st_size < VOLUME_BYTES - 4 * 1024 * 1024,
            "source FIT is missing, empty or too large for the boot partition")
    with fit.open("rb") as stream:
        require(stream.read(4) == b"\xd0\x0d\xfe\xed", "source is not a FIT/FDT")
    for tool in ("sfdisk", "mkfs.fat", "fsck.fat", "mcopy"):
        require(shutil.which(tool), f"missing image build dependency: {tool}")
    output.mkdir(parents=True, exist_ok=True)
    image = output / IMAGE_NAME
    require(not image.exists(), f"refusing to overwrite {image}")
    # Build beside the destination and publish only after all checks pass.
    with tempfile.TemporaryDirectory(prefix=".ckb01-usb-", dir=output) as temporary:
        work = Path(temporary)
        candidate = work / IMAGE_NAME
        with candidate.open("wb") as stream:
            stream.truncate(IMAGE_BYTES)
        command("sfdisk", "--quiet", "--wipe", "never", "--wipe-partitions", "never",
                candidate, input="label: dos\nlabel-id: 0x434b4231\nunit: sectors\n\n"
                f"start={PARTITION_START}, size={PARTITION_SECTORS}, type=6, bootable\n")
        # Explicit geometry avoids mkfs.fat rounding the sector count down.
        command("mkfs.fat", f"--offset={PARTITION_START}", "--mbr=n",
                "-h", PARTITION_START, "-g", "16/32", "-F", "16", "-S", SECTOR_SIZE,
                "-s", "8", "-n", "AIR5BOOT", candidate, VOLUME_BYTES // 1024)
        command("mcopy", "-i", f"{candidate}@@{PARTITION_START * SECTOR_SIZE}",
                fit, "::/uimage-initramfs.itb")
        report = verify(candidate, fit, work)
        candidate.rename(image)
    (output / "usb-image-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fit", type=Path,
                        help="CKB01 FIT to include; the workflow may use raw FIT when validation fails")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package(args.fit.resolve(), args.output.resolve())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CKB01 USB image generation failed: {error}\n")


if __name__ == "__main__":
    main()
