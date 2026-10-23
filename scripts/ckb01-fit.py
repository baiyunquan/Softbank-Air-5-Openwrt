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
WIRELESS_FILES = (
    "lib/functions/ckb01-wifi.sh", "etc/hotplug.d/firmware/10-ckb01-caldata",
    "etc/init.d/ckb01-caldata", "etc/rc.d/S09ckb01-caldata",
    "etc/init.d/ckb01-wifi", "etc/rc.d/S95ckb01-wifi", "usr/sbin/ckb01-wifi-setup",
    "usr/sbin/iw", "usr/bin/iwinfo", "usr/sbin/hostapd",
    "lib/firmware/IPQ8074/q6_fw.mdt", "lib/firmware/IPQ8074/m3_fw.mdt",
    "lib/firmware/regulatory.db",
)
WIRELESS_FILES += tuple(f"lib/firmware/IPQ8074/q6_fw.b{index:02d}" for index in (0, 1, 2, 3, 4, 5, 7, 8))
WIRELESS_FILES += tuple(f"lib/firmware/IPQ8074/m3_fw.b{index:02d}" for index in (0, 1, 2))
BDF_PATH = "lib/firmware/ath11k/IPQ8074/hw2.0/board-2.bin"
BDF_SHA256 = "d53ce59c18ccc20b83f485aa7328ab1b07e837f724642da7a2bd31c574c8de16"
OEM_PACKAGE = Path(__file__).resolve().parents[1] / "packages/ckb01-oem-tools"
OEM_FILES = (
    "usr/bin/oatprsync", "usr/bin/adb", "usr/libexec/timeout-coreutils",
    "usr/sbin/ckb01-oem", "usr/sbin/ckb01-adb", "lib/functions/ckb01-oem.sh",
    "usr/lib/ckb01-oem/adb-control.sh", "usr/share/ckb01-oem/adb-tcp-property.so",
    "usr/share/ckb01-oem/adb-payload.json", "usr/share/ckb01-oem/runtime-provenance.json",
)


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


def archive_entries(data):
    entries = {}
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
            return entries
        entries[name.removeprefix("./").lstrip("/")] = data[offset:offset + size]
        offset = (offset + size + 3) & ~3
    raise ValueError("initramfs archive has no TRAILER!!!")


def verify_oem_runtime(entries):
    for name in OEM_FILES:
        require(bool(entries.get(name)), f"OEM management initramfs is missing {name}")
    record = json.loads((OEM_PACKAGE / "vendor/provenance.json").read_text())
    for name, metadata in record["files"].items():
        installed = "usr/lib/ckb01-oem/runtime/" + name
        require(hashlib.sha256(entries.get(installed, b"")).hexdigest() == metadata["sha256"],
                f"OEM management runtime differs from provenance: {installed}")
    payload = json.loads((OEM_PACKAGE / "payload/provenance.json").read_text())
    require(hashlib.sha256(entries["usr/share/ckb01-oem/adb-tcp-property.so"]).hexdigest() == payload["sha256"],
            "SDX55 ARMv7 ADB payload differs from provenance")


def verify_initramfs(path, kernel, wireless=False, modem=False):
    compressed = path.read_bytes()
    require(bool(compressed) and compressed in kernel,
            "the supplied initramfs bytes are not embedded in the FIT kernel")
    if compressed.startswith(b"\x28\xb5\x2f\xfd"):
        data = command("zstd", "-q", "-d", "-c", path)
    elif compressed.startswith(b"\x1f\x8b"):
        data = gzip.decompress(compressed)
    else:
        data = compressed
    entries = archive_entries(data)
    paths = set(entries)
    for name in REQUIRED_FILES:
        require(name in paths, f"initramfs is missing {name}")
    modules = REQUIRED_MODULES
    if wireless:
        for name in WIRELESS_FILES:
            require(bool(entries.get(name)), f"wireless initramfs is missing or has empty {name}")
        require(hashlib.sha256(entries.get(BDF_PATH, b"")).hexdigest() == BDF_SHA256,
                "wireless initramfs BDF does not match the CKB01 OEM board data")
        require(not any("/cal-ahb-" in name or name.endswith("/caldata.bin") for name in paths),
                "wireless initramfs must obtain unit calibration from ART at runtime")
        modules += ("ath11k", "ath11k_ahb", "mac80211", "cfg80211")
    if modem:
        verify_oem_runtime(entries)
        for name in ("usr/sbin/ckb01-modem", "usr/bin/qmicli", "usr/libexec/qmi-proxy",
                     "lib/netifd/proto/ckb01_qmi.sh", "lib/netifd/ckb01-update",
                     "usr/sbin/ckb01-session", "usr/sbin/ckb01-modem-wait", "usr/sbin/ckb01-mhi-debug",
                     "etc/init.d/ckb01-modem", "etc/rc.d/S96ckb01-modem",
                     "etc/init.d/ckb01-heartbeat", "etc/rc.d/S14ckb01-heartbeat",
                     "usr/sbin/uhttpd", "usr/share/ckb01-modem/heartbeat/index.html",
                     "etc/uci-defaults/98-ckb01-heartbeat",
                     "usr/share/ckb01-modem/mbn-sha256.json",
                     "usr/share/ckb01-modem/endpoint-evidence.json"):
            require(bool(entries.get(name)), f"modem initramfs is missing {name}")
        modem_files = Path(__file__).resolve().parents[1] / "packages/ckb01-modem/files"
        for installed, source in (("usr/sbin/ckb01-modem-wait", "ckb01-modem-wait"),
                                  ("usr/sbin/ckb01-mhi-debug", "ckb01-mhi-debug"),
                                  ("lib/netifd/proto/ckb01_qmi.sh", "ckb01_qmi.sh"),
                                  ("usr/share/ckb01-modem/endpoint-evidence.json", "endpoint-evidence.json")):
            require(entries[installed] == (modem_files / source).read_bytes(),
                    f"modem initramfs has stale or changed {installed}")
        for lib in ("libqmi-glib.so", "libqrtr-glib.so", "libjson-c.so", "libglib-2.0.so", "libgio-2.0.so", "libgobject-2.0.so"):
            require(any(Path(name).name.startswith(lib) for name in paths),
                    f"modem initramfs is missing {lib}")
        modules += ("mhi_net", "qrtr_mhi", "qrtr", "rmnet")
    for module in modules:
        require(any(Path(name).name.replace("-", "_") in (f"{module}.ko", f"{module}.ko.zst", f"{module}.ko.gz")
                    for name in paths), f"initramfs is missing {module}")
    return paths


def verify_board(dtb, wireless=False):
    require("oppo,ckb01" in prop(dtb, "/", "compatible").split(),
            "embedded DT compatible is not oppo,ckb01")
    require(prop(dtb, "/", "qcom,board-id", "x") == [8, 0], "unexpected CKB01 board ID")
    require(prop(dtb, "/memory@40000000", "reg", "x") == [0, 0x40000000, 0, 0x20000000],
            "CKB01 DT does not describe 512 MiB RAM")
    frame = "/soc/interrupt-controller@b000000/v2m@0"
    try:
        require(prop(dtb, frame, "compatible") == "arm,gic-v2m-frame",
                "CKB01 MSI parent must be GICv2m")
        require(prop(dtb, "/soc/pcie@20000000", "msi-parent", "x") ==
                prop(dtb, frame, "phandle", "x"),
                "CKB01 PCIe must route MSI to GICv2m")
    except ValueError as error:
        raise ValueError("CKB01 PCIe is missing the verified GICv2m MSI route") from error
    for port, label, address in ((1, "wan", 8), (2, "lan", 9)):
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
    if wireless:
        node = "/soc/wifi@c0000000"
        require(prop(dtb, node, "status") == "okay", "wireless DT is disabled")
        require(prop(dtb, node, "qcom,ath11k-calibration-variant") == "OPPO-CKB01",
                "wireless DT has the wrong BDF variant")
        require(prop(dtb, node, "qcom,ath11k-fw-memory-mode", "x") == [1],
                "wireless DT must use firmware memory mode 1")
        regions = [prop(dtb, f"/reserved-memory/{name}", "reg", "x")
                   for name in children(dtb, "/reserved-memory")]
        for address, size in ((0x4B000000, 0x3700000), (0x4E700000, 0x100000), (0x4E800000, 0x100000)):
            require([0, address, 0, size] in regions,
                    f"wireless DT has the wrong 512MB reserved-memory region at {address:#x}")


def verify_fit(fit, initramfs, work, wireless=False, modem=False):
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
    verify_board(dtb, wireless)
    paths = verify_initramfs(initramfs, kernel, wireless, modem)
    return dtb, paths, {
        "board": "oppo,ckb01", "hardware_validation": "not performed",
        "kernel_load": "0x41000000", "kernel_entry": "0x41000000",
        "kernel_footprint_bytes": footprint, "fit_size_bytes": fit.stat().st_size,
        "initramfs_sha256": hashlib.sha256(initramfs.read_bytes()).hexdigest(),
        "initramfs_input": str(initramfs),
        "wireless": {"enabled": wireless, "bdf_sha256": BDF_SHA256 if wireless else None,
                     "calibration_source": "unit ART at boot" if wireless else None,
                     "hardware_validation": "not performed"},
        "modem": {"enabled": modem, "control_validation": "pending", "data_validation": "pending", "n78_validation": "pending"},
        "port_mapping": {"LAN1": "wan / switch port1 / PHY8 (hardware verified)",
                         "LAN2": "lan / switch port2 / PHY9 (hardware verified)"},
    }


def package(source, initramfs, output, wireless=False, modem=False):
    with tempfile.TemporaryDirectory(prefix="ckb01-package-") as temporary:
        work = Path(temporary)
        fit = work / IMAGE_NAME
        shutil.copyfile(source, fit)
        dtb, paths, report = verify_fit(fit, initramfs, work, wireless, modem)
        alias = "/configurations/config@hk09"
        if "config@hk09" not in children(fit, "/configurations"):
            command("fdtput", "-c", fit, alias)
        for name, value in (("description", "OpenWrt OPPO CKB01 HK09"),
                            ("kernel", "kernel@1"), ("fdt", "fdt@1")):
            command("fdtput", "-t", "s", fit, alias, name, value)
        # Tree growth must preserve payload bytes and their hashes.
        dtb, paths, report = verify_fit(fit, initramfs, work, wireless, modem)
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
                        help="kernel usr/initramfs_inc_data (must be embedded in the Image)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wireless", action="store_true", help="require CKB01 ath11k DT, BDF and runtime contents")
    parser.add_argument("--modem", action="store_true", help="require native MHI QMI/QRTR tools and dependencies")
    args = parser.parse_args()
    try:
        package(args.fit, args.initramfs, args.output, args.wireless, args.modem)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CKB01 FIT validation failed: {error}\n")


if __name__ == "__main__":
    main()
