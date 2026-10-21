#!/usr/bin/env python3
"""Unit tests for CKB01 prebuilt toolchain helper."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "ckb01-toolchain.py"
spec = importlib.util.spec_from_file_location("ckb01_toolchain", SCRIPT_PATH)
ckb01_toolchain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ckb01_toolchain)


class Ckb01ToolchainTests(unittest.TestCase):
    def test_find_toolchain_root_in_nested_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tc_dir = tmp_path / "toolchain-aarch64_cortex-a53_gcc-14.4.0_musl"
            (tc_dir / "bin").mkdir(parents=True)
            (tc_dir / "info.mk").write_text("TARGET_CROSS=aarch64-openwrt-linux-musl-\n")

            found = ckb01_toolchain.find_toolchain_root(tmp_path)
            self.assertIsNotNone(found)
            self.assertEqual(found, tc_dir.resolve())

    def test_find_toolchain_root_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = ckb01_toolchain.find_toolchain_root(Path(tmp) / "does_not_exist")
            self.assertIsNone(found)

    def test_parse_toolchain_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            tc_dir = Path(tmp)
            (tc_dir / "info.mk").write_text(
                "TARGET_CROSS=aarch64-openwrt-linux-musl-\n"
                "GCC_VERSION=14.4.0\n"
                "LIBC_TYPE=musl\n"
                "LIBC_VERSION=1.2.6\n"
            )
            info = ckb01_toolchain.parse_toolchain_info(tc_dir)
            self.assertEqual(info["TARGET_CROSS"], "aarch64-openwrt-linux-musl-")
            self.assertEqual(info["GCC_VERSION"], "14.4.0")
            self.assertEqual(info["LIBC_TYPE"], "musl")
            self.assertEqual(info["LIBC_VERSION"], "1.2.6")

    def test_generate_kconfig_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tc_dir = tmp_path / "tc"
            (tc_dir / "bin").mkdir(parents=True)
            (tc_dir / "info.mk").write_text(
                "TARGET_CROSS=aarch64-openwrt-linux-musl-\n"
                "GCC_VERSION=14.4.0\n"
                "LIBC_TYPE=musl\n"
            )

            openwrt_dir = tmp_path / "openwrt"
            (openwrt_dir / "scripts").mkdir(parents=True)
            fake_ext = openwrt_dir / "scripts" / "ext-toolchain.sh"
            fake_ext.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *\"--print-libs C\") echo \"$2/aarch64-openwrt-linux-musl/lib/libc.so\" ;;\n"
                "  *\"--print-libs GCC\") echo \"$2/aarch64-openwrt-linux-musl/lib/libgcc_s.so\" ;;\n"
                "  *) exit 0 ;;\n"
                "esac\n"
            )
            fake_ext.chmod(0o755)

            fragment = ckb01_toolchain.generate_kconfig_fragment(tc_dir, openwrt_dir)
            lines = set(fragment.splitlines())
            self.assertIn("CONFIG_DEVEL=y", lines)
            self.assertIn("CONFIG_EXTERNAL_TOOLCHAIN=y", lines)
            self.assertIn(f'CONFIG_TOOLCHAIN_ROOT="{tc_dir.resolve()}"', lines)
            self.assertIn('CONFIG_TOOLCHAIN_PREFIX="aarch64-openwrt-linux-musl-"', lines)
            self.assertIn('CONFIG_TARGET_NAME="aarch64-openwrt-linux-musl"', lines)
            self.assertIn('CONFIG_EXTERNAL_GCC_VERSION="14.4.0"', lines)
            self.assertIn("CONFIG_EXTERNAL_TOOLCHAIN_LIBC_USE_MUSL=y", lines)
            self.assertIn('CONFIG_LIBC_FILE_SPEC="./aarch64-openwrt-linux-musl/lib/libc.so"', lines)
            self.assertIn("CONFIG_PACKAGE_libc=y", lines)
            self.assertIn('CONFIG_LIBGCC_FILE_SPEC="./aarch64-openwrt-linux-musl/lib/libgcc_s.so"', lines)
            self.assertIn("CONFIG_PACKAGE_libgcc=y", lines)


if __name__ == "__main__":
    unittest.main()
