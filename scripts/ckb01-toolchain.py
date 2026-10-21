#!/usr/bin/env python3
"""Prebuilt OpenWrt toolchain helper for OPPO CKB01 (IPQ807x).

This script manages the official OpenWrt snapshot prebuilt toolchain:
  - Downloads and unpacks the qualcommax-ipq807x toolchain tarball
  - Probes toolchain specs (target triple, GCC version, libc, library files)
  - Generates the CONFIG_EXTERNAL_TOOLCHAIN Kconfig fragment for OpenWrt
  - Validates cross-compiler execution and ELF output
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

DEFAULT_TOOLCHAIN_URL = (
    "https://downloads.openwrt.org/snapshots/targets/qualcommax/ipq807x/"
    "openwrt-toolchain-qualcommax-ipq807x_gcc-14.4.0_musl.Linux-x86_64.tar.zst"
)

DEFAULT_DEST_DIR = "toolchain-prebuilt"

LIBS_TO_PROBE = (
    "C",
    "RT",
    "PTHREAD",
    "GCC",
    "STDCPP",
    "SSP",
    "GFORTRAN",
    "GOMP",
    "ATOMIC",
    "QUADMATH",
    "ASAN",
    "TSAN",
    "LSAN",
    "UBSAN",
)

BINS_TO_PROBE = (
    "LDD",
    "LDCONFIG",
)


def find_toolchain_root(search_dir: Path | str) -> Path | None:
    """Find the directory containing info.mk and bin within search_dir."""
    base = Path(search_dir).resolve()
    if not base.exists():
        return None

    # Check if base itself is the toolchain root
    if (base / "info.mk").is_file() and (base / "bin").is_dir():
        return base

    # Check direct children or subdirectories (e.g. toolchain-aarch64_*)
    for candidate in sorted(base.glob("**/info.mk")):
        tc_dir = candidate.parent
        if (tc_dir / "bin").is_dir():
            return tc_dir

    return None


def download_and_extract(
    url: str = DEFAULT_TOOLCHAIN_URL,
    dest_dir: Path | str = DEFAULT_DEST_DIR,
    verbose: bool = True,
) -> Path:
    """Download and extract prebuilt toolchain if not already present."""
    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    existing = find_toolchain_root(dest)
    if existing:
        if verbose:
            print(f"[toolchain] Using existing toolchain at {existing}", file=sys.stderr)
        return existing

    archive_path = dest / "toolchain.tar.zst"
    if verbose:
        print(f"[toolchain] Downloading prebuilt toolchain from {url} ...", file=sys.stderr)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OpenWrt-CKB01-Toolchain-Downloader"},
    )
    with urllib.request.urlopen(req) as resp, open(archive_path, "wb") as out_file:
        shutil.copyfileobj(resp, out_file)

    if verbose:
        print(f"[toolchain] Unpacking {archive_path.name} with tar --zstd ...", file=sys.stderr)

    subprocess.run(
        ["tar", "--zstd", "-xf", str(archive_path), "-C", str(dest)],
        check=True,
    )
    archive_path.unlink(missing_ok=True)

    root = find_toolchain_root(dest)
    if not root:
        raise RuntimeError(f"Could not locate extracted toolchain in {dest}")

    if verbose:
        print(f"[toolchain] Toolchain successfully unpacked at {root}", file=sys.stderr)
    return root


def parse_toolchain_info(toolchain_root: Path) -> dict[str, str]:
    """Parse info.mk in toolchain root."""
    info_file = toolchain_root / "info.mk"
    info: dict[str, str] = {}
    if info_file.is_file():
        for line in info_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                info[key.strip()] = val.strip()

    info.setdefault("TARGET_CROSS", "aarch64-openwrt-linux-musl-")
    info.setdefault("GCC_VERSION", "14.4.0")
    info.setdefault("LIBC_TYPE", "musl")
    return info


def generate_kconfig_fragment(
    toolchain_root: Path | str,
    openwrt_dir: Path | str,
) -> str:
    """Generate CONFIG_EXTERNAL_TOOLCHAIN fragment for OpenWrt .config."""
    root = Path(toolchain_root).resolve()
    openwrt = Path(openwrt_dir).resolve()
    ext_script = openwrt / "scripts" / "ext-toolchain.sh"

    if not root.is_dir():
        raise FileNotFoundError(f"Toolchain directory {root} not found")
    if not ext_script.is_file():
        raise FileNotFoundError(f"OpenWrt ext-toolchain script {ext_script} not found")

    info = parse_toolchain_info(root)
    prefix = info["TARGET_CROSS"]
    target_name = prefix.rstrip("-")
    gcc_version = info["GCC_VERSION"]
    libc_type = info["LIBC_TYPE"].lower()

    lines = [
        "# Prebuilt external toolchain configuration for CKB01",
        "CONFIG_DEVEL=y",
        "CONFIG_EXTERNAL_TOOLCHAIN=y",
        f'CONFIG_TOOLCHAIN_ROOT="{root}"',
        f'CONFIG_TOOLCHAIN_PREFIX="{prefix}"',
        f'CONFIG_TARGET_NAME="{target_name}"',
        f'CONFIG_EXTERNAL_GCC_VERSION="{gcc_version}"',
        f'CONFIG_TOOLCHAIN_LIBC="{libc_type}"',
        f"CONFIG_EXTERNAL_TOOLCHAIN_LIBC_USE_{libc_type.upper()}=y",
        'CONFIG_TOOLCHAIN_BIN_PATH="./usr/bin ./bin"',
        'CONFIG_TOOLCHAIN_INC_PATH="./usr/include ./include/fortify ./include"',
        'CONFIG_TOOLCHAIN_LIB_PATH="./usr/lib ./lib"',
    ]

    # Probe libraries using ext-toolchain.sh
    root_str = str(root)
    for lib in LIBS_TO_PROBE:
        res = subprocess.run(
            [str(ext_script), "--toolchain", root_str, "--print-libs", lib],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        files = res.stdout.strip().split()
        if files:
            specs = [f.replace(root_str, ".") for f in files]
            lines.append(f'CONFIG_LIB{lib}_FILE_SPEC="{" ".join(specs)}"')
            lines.append(f"CONFIG_PACKAGE_lib{lib.lower()}=y")
        else:
            lines.append(f"# CONFIG_PACKAGE_lib{lib.lower()} is not set")

    # Probe binaries using ext-toolchain.sh
    for bin_prog in BINS_TO_PROBE:
        res = subprocess.run(
            [str(ext_script), "--toolchain", root_str, "--print-bin", bin_prog],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        files = res.stdout.strip().split()
        if files:
            specs = [f.replace(root_str, ".") for f in files]
            lines.append(f'CONFIG_{bin_prog}_FILE_SPEC="{" ".join(specs)}"')
            lines.append(f"CONFIG_PACKAGE_{bin_prog.lower()}=y")
        else:
            lines.append(f"# CONFIG_PACKAGE_{bin_prog.lower()} is not set")

    return "\n".join(lines) + "\n"


def validate_toolchain(toolchain_root: Path | str) -> bool:
    """Validate that the toolchain cross-compiler can generate an aarch64 ELF."""
    root = Path(toolchain_root).resolve()
    info = parse_toolchain_info(root)
    prefix = info["TARGET_CROSS"]
    gcc_path = root / "bin" / f"{prefix}gcc"

    if not gcc_path.is_file():
        # Try generic gcc if prefix didn't match
        candidates = list((root / "bin").glob("*gcc*"))
        if not candidates:
            raise FileNotFoundError(f"No GCC binary found in {root / 'bin'}")
        gcc_path = candidates[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        c_file = tmp_path / "test.c"
        out_bin = tmp_path / "test.bin"
        c_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")

        env = dict(os.environ)
        env["STAGING_DIR"] = str(root)

        res = subprocess.run(
            [str(gcc_path), "-o", str(out_bin), str(c_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Toolchain validation compile failed:\n{res.stderr}")

        file_out = subprocess.run(
            ["file", str(out_bin)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout

        if "aarch64" not in file_out.lower() and "arm aarch64" not in file_out.lower():
            raise RuntimeError(f"Unexpected binary format for {out_bin}:\n{file_out}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenWrt prebuilt toolchain manager")
    parser.add_argument("--download", action="store_true", help="Download and extract toolchain")
    parser.add_argument("--url", default=DEFAULT_TOOLCHAIN_URL, help="Toolchain tarball URL")
    parser.add_argument("--dest-dir", default=DEFAULT_DEST_DIR, help="Download/extraction directory")
    parser.add_argument("--toolchain-dir", help="Path to unpacked toolchain root")
    parser.add_argument("--openwrt-dir", default="openwrt", help="Path to checked out OpenWrt tree")
    parser.add_argument("--generate-config", action="store_true", help="Output Kconfig fragment")
    parser.add_argument("--check", action="store_true", help="Validate cross-compiler execution")
    parser.add_argument("--output", help="Write Kconfig fragment to file instead of stdout")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Download (if needed), validate, and generate Kconfig fragment",
    )

    args = parser.parse_args()

    try:
        tc_root: Path | None = None
        if args.toolchain_dir:
            tc_root = Path(args.toolchain_dir).resolve()
        elif args.dest_dir:
            tc_root = find_toolchain_root(args.dest_dir)

        if args.download or (args.setup and not tc_root):
            tc_root = download_and_extract(url=args.url, dest_dir=args.dest_dir)

        if not tc_root or not tc_root.is_dir():
            print("Error: Toolchain root directory not found. Specify --toolchain-dir or --download.", file=sys.stderr)
            return 1

        if args.check or args.setup:
            validate_toolchain(tc_root)
            print(f"[toolchain] Validated aarch64 cross-compiler in {tc_root}", file=sys.stderr)

        if args.generate_config or args.setup:
            fragment = generate_kconfig_fragment(tc_root, args.openwrt_dir)
            if args.output:
                Path(args.output).write_text(fragment, encoding="utf-8")
                print(f"[toolchain] Wrote Kconfig fragment to {args.output}", file=sys.stderr)
            else:
                sys.stdout.write(fragment)

        return 0
    except Exception as exc:
        print(f"[toolchain] Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
