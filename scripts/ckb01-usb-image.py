#!/usr/bin/env python3
"""Package a CKB01 FIT and optional persistent rootfs in an MBR USB image and verify the disk layout."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import re


IMAGE_NAME = "air5-ckb01-usb.img"
IMAGE_GZ_NAME = "air5-ckb01-usb.img.gz"
SECTOR_SIZE = 512

PARTITION_1_START = 2048
PARTITION_1_SECTORS = 524288  # 256 MiB
PARTITION_1_BYTES = PARTITION_1_SECTORS * SECTOR_SIZE

PARTITION_2_START = PARTITION_1_START + PARTITION_1_SECTORS  # 526336
PARTITION_2_SECTORS = 2097152  # 1024 MiB
PARTITION_2_BYTES = PARTITION_2_SECTORS * SECTOR_SIZE

TOTAL_SECTORS_DUAL = PARTITION_2_START + PARTITION_2_SECTORS  # 2623488
IMAGE_BYTES_DUAL = TOTAL_SECTORS_DUAL * SECTOR_SIZE

IMAGE_BYTES_SINGLE = (PARTITION_1_START + PARTITION_1_SECTORS) * SECTOR_SIZE


def command(*args, input=None):
    result = subprocess.run([str(arg) for arg in args], input=input,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stdout.strip()} {result.stderr.strip()}")
    return result.stdout


def require(condition, message):
    if not condition:
        raise ValueError(message)


def copy_extent(source, destination, length):
    """Copy exactly one partition, without reading the following partition."""
    while length:
        data = source.read(min(length, 1024 * 1024))
        require(bool(data), "USB image ended before the partition boundary")
        destination.write(data)
        length -= len(data)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(image, fit, work, has_rootfs=False):
    expected_bytes = IMAGE_BYTES_DUAL if has_rootfs else IMAGE_BYTES_SINGLE
    require(image.stat().st_size == expected_bytes,
            f"USB image size must be {expected_bytes} bytes, got {image.stat().st_size}")

    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
        require(mbr[510:512] == b"\x55\xaa", "missing MBR signature")
        
        # Partition 1 verification
        boot, _, kind, _, start, sectors = struct.unpack("<B3sB3sII", mbr[446:462])
        require((boot, kind, start, sectors) ==
                (0x80, 0x06, PARTITION_1_START, PARTITION_1_SECTORS),
                "expected bootable FAT16 primary partition 1 at LBA 2048")

        if has_rootfs:
            # Partition 2 verification
            boot2, _, kind2, _, start2, sectors2 = struct.unpack("<B3sB3sII", mbr[462:478])
            require((boot2, kind2, start2, sectors2) ==
                    (0x00, 0x83, PARTITION_2_START, PARTITION_2_SECTORS),
                    "expected Linux native partition 2 at LBA 526336")
            require(mbr[478:510] == bytes(32), "unexpected additional partitions (slots 3 and 4)")
        else:
            require(mbr[462:510] == bytes(48), "unexpected additional partitions")

        # Check Partition 1 BPB
        stream.seek(start * SECTOR_SIZE)
        bpb = stream.read(SECTOR_SIZE)
        require(bpb[510:512] == b"\x55\xaa" and bpb[54:62] == b"FAT16   ",
                "partition 1 is not FAT16")
        require(struct.unpack_from("<H", bpb, 11)[0] == SECTOR_SIZE and bpb[13] == 8,
                "expected 512-byte sectors and 4096-byte clusters in partition 1")
        require(struct.unpack_from("<I", bpb, 28)[0] == PARTITION_1_START,
                "FAT hidden-sector count differs from partition 1 start")
        require(struct.unpack_from("<I", bpb, 32)[0] == PARTITION_1_SECTORS,
                "FAT volume size differs from partition 1 size")

        # Copy partition 1 slice for fsck.fat
        stream.seek(start * SECTOR_SIZE)
        partition1 = work / "partition-1.fat"
        with partition1.open("wb") as destination:
            copy_extent(stream, destination, PARTITION_1_BYTES)

    command("sfdisk", "--verify", image)
    filesystem_check = command("fsck.fat", "-n", partition1)
    extracted = work / "readback.itb"
    command("mcopy", "-i", f"{image}@@{PARTITION_1_START * SECTOR_SIZE}",
            "::/uimage-initramfs.itb", extracted)
    require(extracted.read_bytes() == fit.read_bytes(),
            "USB partition 1 FIT differs from validated source FIT")

    e2fsck_check = "none (single partition image)"
    if has_rootfs:
        part2_file = work / "partition-2.ext4"
        if not part2_file.exists():
            with image.open("rb") as stream, part2_file.open("wb") as destination:
                stream.seek(PARTITION_2_START * SECTOR_SIZE)
                copy_extent(stream, destination, PARTITION_2_BYTES)
        e2fsck_check = command("e2fsck", "-f", "-n", part2_file).strip()
        acl_stat = command("debugfs", "-R", "stat /usr/share/acl.d/wpad_acl.json", part2_file)
        owner = re.search(r"User:\s*(\d+)\s+Group:\s*(\d+)", acl_stat)
        require(owner is not None and owner.groups() == ("0", "0"),
                "ext4 wpad ACL must be root:root; non-root archive extraction breaks ubus")

    report = {
        "image": image.name,
        "image_bytes": expected_bytes,
        "image_sha256": sha256(image),
        "partition_table": "MBR / DOS",
        "partition_1": {
            "bootable": True, "type": "0x06 FAT16",
            "start_sector": PARTITION_1_START, "sectors": PARTITION_1_SECTORS,
            "volume_bytes": PARTITION_1_BYTES, "sector_bytes": SECTOR_SIZE,
            "cluster_bytes": 4096, "label": "AIR5BOOT",
            "root_file": "uimage-initramfs.itb",
            "filesystem_check": filesystem_check.strip(),
        },
        "fit_sha256": sha256(fit),
        "fit_readback": "byte-for-byte identical",
        "boot_method": "OEM bootipq_usb automatic USB loading",
        "hardware_validation": "pending boot using the MBR image",
    }

    if has_rootfs:
        report["partition_2"] = {
            "bootable": False, "type": "0x83 Linux native",
            "start_sector": PARTITION_2_START, "sectors": PARTITION_2_SECTORS,
            "volume_bytes": PARTITION_2_BYTES, "label": "AIR5ROOT",
            "filesystem": "ext4",
            "filesystem_check": e2fsck_check,
        }
        report["persistence"] = "USB partition 2 labeled AIR5ROOT becomes writable /; auto-expands on first boot; same-disk AIR5BOOT mounts read-only at /boot"
    else:
        report["persistence"] = "RAM root; settings reset on reboot"

    return report


def package(fit, output, rootfs=None):
    require(fit.is_file() and 0 < fit.stat().st_size < PARTITION_1_BYTES - 4 * 1024 * 1024,
            "source FIT is missing, empty or too large for the boot partition")
    with fit.open("rb") as stream:
        require(stream.read(4) == b"\xd0\x0d\xfe\xed", "source is not a FIT/FDT")
    if rootfs:
        require(rootfs.is_file() and rootfs.stat().st_size > 0,
                f"rootfs tarball {rootfs} is missing or empty")

    required_tools = ["sfdisk", "mkfs.fat", "fsck.fat", "mcopy", "gzip"]
    if rootfs:
        required_tools.extend(["mkfs.ext4", "e2fsck", "debugfs", "tar", "fakeroot"])
    for tool in required_tools:
        require(shutil.which(tool), f"missing image build dependency: {tool}")

    output.mkdir(parents=True, exist_ok=True)
    image = output / IMAGE_NAME
    image_gz = output / IMAGE_GZ_NAME
    require(not image.exists(), f"refusing to overwrite {image}")
    require(not image_gz.exists(), f"refusing to overwrite {image_gz}")

    has_rootfs = bool(rootfs)
    total_bytes = IMAGE_BYTES_DUAL if has_rootfs else IMAGE_BYTES_SINGLE

    with tempfile.TemporaryDirectory(prefix=".ckb01-usb-", dir=output) as temporary:
        work = Path(temporary)
        candidate = work / IMAGE_NAME
        with candidate.open("wb") as stream:
            stream.truncate(total_bytes)

        if has_rootfs:
            sfdisk_spec = (
                "label: dos\n"
                "label-id: 0x434b4231\n"
                "unit: sectors\n\n"
                f"start={PARTITION_1_START}, size={PARTITION_1_SECTORS}, type=6, bootable\n"
                f"start={PARTITION_2_START}, size={PARTITION_2_SECTORS}, type=83\n"
            )
        else:
            sfdisk_spec = (
                "label: dos\n"
                "label-id: 0x434b4231\n"
                "unit: sectors\n\n"
                f"start={PARTITION_1_START}, size={PARTITION_1_SECTORS}, type=6, bootable\n"
            )

        command("sfdisk", "--quiet", "--wipe", "never", "--wipe-partitions", "never",
                candidate, input=sfdisk_spec)

        # Format Partition 1 (FAT16)
        command("mkfs.fat", f"--offset={PARTITION_1_START}", "--mbr=n",
                "-h", PARTITION_1_START, "-g", "16/32", "-F", "16", "-S", SECTOR_SIZE,
                "-s", "8", "-n", "AIR5BOOT", candidate, PARTITION_1_BYTES // 1024)
        command("mcopy", "-i", f"{candidate}@@{PARTITION_1_START * SECTOR_SIZE}",
                fit, "::/uimage-initramfs.itb")

        if has_rootfs:
            rootfs_tree = work / "rootfs_tree"
            rootfs_tree.mkdir()

            part2_file = work / "partition-2.ext4"
            with part2_file.open("wb") as stream:
                stream.truncate(PARTITION_2_BYTES)
            # Both processes must share the same fakeroot metadata database.
            # Plain non-root tar + mkfs -d stamps the CI UID onto every inode,
            # and ubusd refuses ACL JSON not owned by uid/gid 0.
            command("fakeroot", "--", "sh", "-ec",
                    'tar --numeric-owner --same-owner -xzf "$1" -C "$2"; '
                    'exec mkfs.ext4 -F -L AIR5ROOT -d "$2" "$3"',
                    "ckb01-rootfs", rootfs, rootfs_tree, part2_file)

            with part2_file.open("rb") as src, candidate.open("r+b") as dst:
                dst.seek(PARTITION_2_START * SECTOR_SIZE)
                shutil.copyfileobj(src, dst, 1024 * 1024)

        try:
            report = verify(candidate, fit, work, has_rootfs=has_rootfs)
            report["validation"] = "passed"
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            # A diagnostic mismatch must not discard an already-built image.
            report = {"image": IMAGE_NAME, "image_bytes": candidate.stat().st_size,
                      "image_sha256": sha256(candidate), "fit_sha256": sha256(fit),
                      "validation": "failed", "validation_error": str(error),
                      "hardware_validation": "not performed"}
            print(f"::warning title=CKB01 USB validation::{error}; retaining raw IMG")

        candidate_gz = work / IMAGE_GZ_NAME
        with candidate.open("rb") as f_in, gzip.open(candidate_gz, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out, 1024 * 1024)

        report["compressed_image"] = IMAGE_GZ_NAME
        report["compressed_bytes"] = candidate_gz.stat().st_size
        report["compressed_sha256"] = sha256(candidate_gz)

        candidate.rename(image)
        candidate_gz.rename(image_gz)

    (output / "usb-image-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fit", type=Path,
                        help="CKB01 FIT to include in boot partition")
    parser.add_argument("--rootfs", type=Path, default=None,
                        help="Optional OpenWrt rootfs tarball to populate ext4 partition 2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = package(args.fit.resolve(), args.output.resolve(),
                         rootfs=args.rootfs.resolve() if args.rootfs else None)
        if report.get("validation") == "failed":
            parser.exit(1, "CKB01 USB verification failed; raw IMG/GZ and report retained for upload\n")
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CKB01 USB image generation failed: {error}\n")


if __name__ == "__main__":
    main()
