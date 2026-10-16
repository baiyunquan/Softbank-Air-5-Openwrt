#!/usr/bin/env python3
"""Validate a CKB01 initramfs FIT and prepare the stock USB boot filename."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib


IMAGE_NAME = "openwrt-qualcommax-ipq807x-oppo_ckb01-initramfs-uImage.itb"
REQUIRED_FILES = (
    "sbin/init", "sbin/netifd", "usr/sbin/dropbear", "www/cgi-bin/luci",
    "usr/sbin/ckb01-diag", "usr/sbin/ckb01-art-backup",
    "etc/uci-defaults/99-ckb01-network",
)
REQUIRED_MODULES = ("mhi_pci_generic", "mhi_wwan_ctrl")


def command(*args):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stderr.decode(errors='replace').strip()[:400]}")
    return result.stdout


def prop(blob, node, name, kind="s"):
    value = command("fdtget", "-t", kind, blob, node, name).decode().strip()
    if kind == "x":
        return [int(word, 16) for word in value.split()]
    if kind == "bx":
        return bytes(int(word, 16) for word in value.split())
    return value


def children(blob, node):
    return command("fdtget", "-l", blob, node).decode().split()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def archive_paths(data):
    paths = set()
    offset = 0
    while offset + 110 <= len(data):
        header = data[offset:offset + 110]
        require(header[:6] in (b"070701", b"070702"), "invalid initramfs newc archive")
        fields = [int(header[6 + index * 8:14 + index * 8], 16) for index in range(13)]
        size, name_size = fields[6], fields[11]
        start = offset + 110
        require(name_size > 0 and start + name_size <= len(data), "truncated initramfs name")
        name = data[start:start + name_size - 1].decode()
        offset = (start + name_size + 3) & ~3
        require(offset + size <= len(data), "truncated initramfs data")
        if name == "TRAILER!!!":
            return paths
        paths.add(name.removeprefix("./").lstrip("/"))
        offset = (offset + size + 3) & ~3
    raise ValueError("initramfs archive has no TRAILER!!!")


def verify_initramfs(path, kernel):
    compressed = path.read_bytes()
    require(bool(compressed) and compressed in kernel,
            "the supplied initramfs bytes are not embedded in the FIT kernel")
    if compressed.startswith(b"\x28\xb5\x2f\xfd"):
        data = command("zstd", "-q", "-d", "-c", path)
    elif compressed.startswith(b"\x1f\x8b"):
        data = gzip.decompress(compressed)
    else:
        data = compressed
    paths = archive_paths(data)
    for name in REQUIRED_FILES:
        require(name in paths, f"initramfs is missing {name}")
    for module in REQUIRED_MODULES:
        require(any(Path(name).name in (f"{module}.ko", f"{module}.ko.zst", f"{module}.ko.gz")
                    for name in paths), f"initramfs is missing {module}")
    return paths


def verify_board(dtb):
    require("oppo,ckb01" in prop(dtb, "/", "compatible").split(),
            "embedded DT compatible is not oppo,ckb01")
    require(prop(dtb, "/", "qcom,board-id", "x") == [8, 0], "unexpected CKB01 board ID")
    require(prop(dtb, "/memory@40000000", "reg", "x") == [0, 0x40000000, 0, 0x20000000],
            "CKB01 DT does not describe 512 MiB RAM")
    for port, label, address in ((1, "lan", 8), (2, "wan", 9)):
        node = f"/soc/ppe@3a000000/ports/port@{port}"
        phy = f"/soc/mdio@90000/ethernet-phy-package@8/ethernet-phy@{address:x}"
        require(prop(dtb, node, "label") == label, f"port{port} has the wrong network role")
        require(prop(dtb, node, "phy-mode") == "psgmii", f"port{port} is not PSGMII")
        require(prop(dtb, phy, "reg", "x") == [address], f"port{port} PHY address is wrong")
        try:
            expected = prop(dtb, phy, "phandle", "x")
        except ValueError as error:
            raise ValueError(f"port{port} PHY is not referenced by the switch") from error
        require(prop(dtb, node, "phy-handle", "x") == expected,
                f"port{port} PHY binding is wrong")


def verify_fit(fit, initramfs, work):
    require(prop(fit, "/configurations", "default") == "config@1", "FIT default must be config@1")
    config = "/configurations/config@1"
    kernel_node = prop(fit, config, "kernel")
    fdt_node = prop(fit, config, "fdt")
    require(kernel_node == "kernel@1" and fdt_node == "fdt@1", "unexpected stock FIT image names")
    images = children(fit, "/images")
    require(set(images) == {kernel_node, fdt_node}, "expected one kernel and one DTB in the FIT")
    payloads = {}
    for node in images:
        output = work / f"{node}.bin"
        command("dumpimage", "-T", "flat_dt", "-p", images.index(node), "-o", output, fit)
        payload = output.read_bytes()
        hashes = {}
        for child in children(fit, f"/images/{node}"):
            if child.startswith("hash"):
                child_path = f"/images/{node}/{child}"
                algorithm = prop(fit, child_path, "algo")
                expected = prop(fit, child_path, "value", "bx")
                if algorithm == "crc32":
                    actual = struct.pack(">I", zlib.crc32(payload))
                elif algorithm in ("sha1", "sha256"):
                    actual = hashlib.new(algorithm, payload).digest()
                else:
                    raise ValueError(f"unsupported FIT hash {algorithm}")
                require(actual == expected, f"FIT hash mismatch in {node}/{child}")
                hashes[algorithm] = actual.hex()
        require("crc32" in hashes and "sha1" in hashes, f"{node} needs stock-compatible CRC32/SHA1 hashes")
        payloads[node] = payload
    kernel_path = f"/images/{kernel_node}"
    require(prop(fit, kernel_path, "arch") == "arm64", "kernel is not AArch64")
    require(prop(fit, kernel_path, "os") == "linux", "kernel OS is not Linux")
    require(prop(fit, kernel_path, "type") == "kernel", "FIT payload is not a kernel")
    require(prop(fit, kernel_path, "compression") == "gzip", "kernel must be gzip compressed")
    for name in ("load", "entry"):
        require(prop(fit, kernel_path, name, "x") == [0x41000000], f"unexpected kernel {name} address")
    kernel = gzip.decompress(payloads[kernel_node])
    require(kernel[56:60] == b"ARM\x64", "decompressed kernel is not an ARM64 Image")
    footprint = max(len(kernel), struct.unpack_from("<Q", kernel, 16)[0])
    require(0x41000000 + footprint < 0x44000000,
            "kernel footprint reaches the U-Boot FIT buffer at 0x44000000")
    require(0x44000000 + fit.stat().st_size < 0x4A400000,
            "FIT buffer reaches the stock reserved-memory area at 0x4a400000")
    dtb = work / "ckb01.dtb"
    dtb.write_bytes(payloads[fdt_node])
    verify_board(dtb)
    paths = verify_initramfs(initramfs, kernel)
    return dtb, paths, {
        "board": "oppo,ckb01", "hardware_validation": "not performed",
        "kernel_load": "0x41000000", "kernel_entry": "0x41000000",
        "kernel_footprint_bytes": footprint, "fit_size_bytes": fit.stat().st_size,
        "initramfs_sha256": hashlib.sha256(initramfs.read_bytes()).hexdigest(),
        "port_mapping": {"LAN1": "wan / switch port2 / PHY9 (pending hardware check)",
                         "LAN2": "lan / switch port1 / PHY8 (pending hardware check)"},
    }


def package(source, initramfs, output):
    with tempfile.TemporaryDirectory(prefix="ckb01-package-") as temporary:
        work = Path(temporary)
        fit = work / IMAGE_NAME
        shutil.copyfile(source, fit)
        dtb, paths, report = verify_fit(fit, initramfs, work)
        alias = "/configurations/config@hk09"
        command("fdtput", "-c", fit, alias)
        for name, value in (("description", "OpenWrt OPPO CKB01 HK09"),
                            ("kernel", "kernel@1"), ("fdt", "fdt@1")):
            command("fdtput", "-t", "s", fit, alias, name, value)
        # Tree growth must preserve payload bytes and their hashes.
        dtb, paths, report = verify_fit(fit, initramfs, work)
        command("dumpimage", "-l", fit)
        (work / "fit-report.json").write_text(json.dumps(report, indent=2) + "\n")
        (work / "initramfs-files.txt").write_text("\n".join(sorted(paths)) + "\n")
        command("dtc", "-q", "-I", "dtb", "-O", "dts", "-o", work / "ckb01.dts", dtb)
        output.mkdir(parents=True, exist_ok=True)
        names = (IMAGE_NAME, "ckb01.dtb", "ckb01.dts", "fit-report.json", "initramfs-files.txt")
        for name in names:
            shutil.copyfile(work / name, output / name)
        shutil.copyfile(fit, output / "uimage-initramfs.itb")
        (output / "sha256sums").write_text("".join(
            f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n"
            for name in (*names, "uimage-initramfs.itb")))
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fit", type=Path)
    parser.add_argument("--initramfs", type=Path, required=True,
                        help="kernel usr/initramfs_data.cpio.zst (must be embedded in the Image)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package(args.fit, args.initramfs, args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CKB01 FIT validation failed: {error}\n")


if __name__ == "__main__":
    main()
