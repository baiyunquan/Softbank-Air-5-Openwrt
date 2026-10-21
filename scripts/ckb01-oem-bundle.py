#!/usr/bin/env python3
"""Collect the original IPQ client and its private ELF dependency closure."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "packages/ckb01-oem-tools/vendor"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dependencies(path):
    data = path.read_bytes()
    if data[:5] != b"\x7fELF\x02" or struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError(f"not an AArch64 ELF: {path}")
    result = subprocess.run(["readelf", "-d", str(path)], check=True,
                            capture_output=True, text=True, env={"LC_ALL": "C"})
    return re.findall(r"Shared library: \[([^]]+)\]", result.stdout)


def generate(source, destination, label):
    # libconfigapi resolves libz with dlopen rather than a DT_NEEDED entry.
    queue = [source / "usr/bin/oatprsync", source / "lib/ld-musl-aarch64.so.1",
             source / "usr/lib/libz.so"]
    entries, files, found = {}, {}, set()
    while queue:
        path = queue.pop(0)
        if path.name in found:
            continue
        found.add(path.name)
        needed = dependencies(path)
        name = ("bin/" if path.name == "oatprsync" else "lib/") + path.name
        data = path.read_bytes()
        entries[name] = data
        files[name] = {"source": str(path.relative_to(source)), "size": len(data),
                       "sha256": sha(data), "needed": needed}
        for library in needed:
            matches = [source / "lib" / library, source / "usr/lib" / library]
            match = next((p for p in matches if p.is_file()), None)
            if match is None:
                raise ValueError(f"unresolved {library}, required by {path}")
            queue.append(match)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, data in sorted(entries.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o755, 0
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                archive.addfile(info, io.BytesIO(data))
    destination.mkdir(parents=True, exist_ok=True)
    data = output.getvalue()
    (destination / "runtime.tar.gz").write_bytes(data)
    provenance = {"source": label,
                  "selection": "oatprsync + OEM musl loader + recursive DT_NEEDED closure + libconfigapi dlopen(libz.so)",
                  "archive_sha256": sha(data), "files": files,
                  "unit_data": "No ART, passwords, SIM/IMEI/NV or unit configuration included"}
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


def check(destination):
    record = json.loads((destination / "provenance.json").read_text())
    data = (destination / "runtime.tar.gz").read_bytes()
    if sha(data) != record["archive_sha256"]:
        raise ValueError("OEM runtime archive hash mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        actual = {m.name: archive.extractfile(m).read() for m in archive.getmembers()
                  if m.isfile()}
    if set(actual) != set(record["files"]):
        raise ValueError("OEM runtime member list differs from provenance")
    if "lib/libz.so" not in actual:
        raise ValueError("OEM runtime missing the libconfigapi zlib plugin")
    for name, entry in record["files"].items():
        if sha(actual[name]) != entry["sha256"] or len(actual[name]) != entry["size"]:
            raise ValueError(f"OEM runtime member mismatch: {name}")
        for dep in entry["needed"]:
            if "lib/" + dep not in actual:
                raise ValueError(f"OEM runtime missing dependency {dep}")
    print(f"OEM runtime: {len(actual)} files, {sum(map(len, actual.values()))} bytes; hashes and dependency closure recorded")


def overlay(destination, output):
    """Build a userspace-only installer; native adb/timeout come from OpenWrt packages."""
    package = ROOT / "packages/ckb01-oem-tools"
    entries = {}
    with tarfile.open(destination / "runtime.tar.gz", "r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile():
                entries["root/usr/lib/ckb01-oem/runtime/" + member.name] = (archive.extractfile(member).read(), 0o755)
    mapping = {
        "files/oatprsync": ("usr/bin/oatprsync", 0o755),
        "files/ckb01-oem": ("usr/sbin/ckb01-oem", 0o755),
        "files/ckb01-adb": ("usr/sbin/ckb01-adb", 0o755),
        "files/ckb01-oem.sh": ("lib/functions/ckb01-oem.sh", 0o644),
        "files/adb-control.sh": ("usr/lib/ckb01-oem/adb-control.sh", 0o644),
        "payload/adb-tcp-property.so": ("usr/share/ckb01-oem/adb-tcp-property.so", 0o644),
        "payload/provenance.json": ("usr/share/ckb01-oem/adb-payload.json", 0o644),
    }
    for source, (target, mode) in mapping.items():
        entries["root/" + target] = ((package / source).read_bytes(), mode)
    entries["root/usr/share/ckb01-oem/runtime-provenance.json"] = ((destination / "provenance.json").read_bytes(), 0o644)
    entries["README.md"] = ((ROOT / "docs/CKB01_OEM_MANAGEMENT.md").read_bytes(), 0o644)
    checksums = "".join(f"{sha(data)}  {name[5:]}\n" for name, (data, mode) in sorted(entries.items()) if name.startswith("root/"))
    entries["SHA256SUMS"] = (checksums.encode(), 0o644)
    installer = '''#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo 'Run as root on CKB01 OpenWrt.' >&2; exit 77; }
[ -f /etc/openwrt_release ] || exit 69
tr '\\000' '\\n' </sys/firmware/devicetree/base/compatible | grep -qx 'oppo,ckb01' || exit 69
for tool in ckb01-modem adb jsonfilter ip; do
 command -v "$tool" >/dev/null || { echo "Missing $tool; install matching OpenWrt dependencies first (see README.md)." >&2; exit 69; }
done
[ -x /usr/libexec/timeout-coreutils ] || { echo 'Install coreutils-timeout first.' >&2; exit 69; }
(cd "$here/root" && sha256sum -c "$here/SHA256SUMS")
cp -a "$here/root/." /
echo "Installed. Run: ckb01-oem exec 'id; uname -a'"
echo 'ADB: ckb01-adb shell; restore: ckb01-adb disable'
'''
    entries["install.sh"] = (installer.encode(), 0o755)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name, (data, mode) in sorted(entries.items()):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), mode, 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    archive.addfile(info, io.BytesIO(data))
    print(f"Overlay: {output} ({output.stat().st_size} bytes), SHA256 {sha(output.read_bytes())}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-label", default="Local CKB01 OEM IPQ rootfs snapshot")
    parser.add_argument("--output", type=Path, default=VENDOR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--overlay", type=Path, help="build a management overlay for an existing CKB01 OpenWrt")
    args = parser.parse_args()
    if args.source_root:
        generate(args.source_root.resolve(), args.output, args.source_label)
    if args.check:
        check(args.output)
    if args.overlay:
        overlay(args.output, args.overlay)
    if not args.source_root and not args.check and not args.overlay:
        parser.error("use --source-root, --check or --overlay")


if __name__ == "__main__":
    main()
