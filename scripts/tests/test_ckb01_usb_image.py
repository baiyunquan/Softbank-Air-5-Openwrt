#!/usr/bin/env python3
"""Tests for CKB01 USB image generation and partitioning."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class Ckb01UsbImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_path = Path(__file__).resolve().parents[1] / "ckb01-usb-image.py"
        spec = importlib.util.spec_from_file_location("ckb01_usb_image", cls.script_path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_dual_partition_generation(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            # Create a mock FIT file with correct magic
            fit_file = work / "mock.itb"
            with fit_file.open("wb") as f:
                f.write(b"\xd0\x0d\xfe\xed" + b"\x00" * 1024)

            # Create a mock rootfs tarball
            rootfs_tree = work / "rootfs_tree"
            etc_dir = rootfs_tree / "etc"
            etc_dir.mkdir(parents=True)
            (etc_dir / "openwrt_version").write_text("TEST-BUILD\n")
            acl_dir = rootfs_tree / "usr/share/acl.d"
            acl_dir.mkdir(parents=True)
            (acl_dir / "wpad_acl.json").write_text("{}\n")
            rootfs_tar = work / "rootfs.tar.gz"
            subprocess.run(["tar", "--owner=0", "--group=0", "-czf", str(rootfs_tar), "-C", str(rootfs_tree), "."], check=True)

            out_dir = work / "out"
            self.module.package(fit_file, out_dir, rootfs=rootfs_tar)

            img_file = out_dir / "air5-ckb01-usb.img"
            img_gz_file = out_dir / "air5-ckb01-usb.img.gz"
            report_file = out_dir / "usb-image-report.json"

            self.assertTrue(img_file.is_file())
            self.assertTrue(img_gz_file.is_file())
            self.assertTrue(report_file.is_file())

            self.assertEqual(img_file.stat().st_size, self.module.IMAGE_BYTES_DUAL)
            self.assertGreater(img_gz_file.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
