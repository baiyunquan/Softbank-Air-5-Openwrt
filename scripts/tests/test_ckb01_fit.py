#!/usr/bin/env python3
"""Exercise the USB packager with real mkimage/dtc-generated FITs."""

import gzip
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


PACKAGER = Path(__file__).resolve().parents[1] / "ckb01-fit.py"
REQUIRED = [
    "sbin/init", "sbin/netifd", "usr/sbin/dropbear", "www/cgi-bin/luci",
    "usr/sbin/ckb01-diag", "usr/sbin/ckb01-art-backup",
    "etc/uci-defaults/99-ckb01-network",
    "lib/modules/6.18/mhi_pci_generic.ko",
    "lib/modules/6.18/mhi_wwan_ctrl.ko",
]


def cpio(paths):
    """Build a small newc archive without depending on the packager."""
    archive = bytearray()
    for number, name in enumerate([*paths, "TRAILER!!!"], 1):
        encoded = name.encode() + b"\0"
        fields = [number, 0o100755, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(encoded), 0]
        archive += b"070701" + b"".join(f"{value:08x}".encode() for value in fields)
        archive += encoded
        archive += b"\0" * (-len(archive) % 4)
    return bytes(archive)


class Ckb01FitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ckb01-fit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def make_fit(self, *, board="oppo,ckb01", missing_module=False,
                 oversized=False, swapped_phy=False):
        paths = [name for name in REQUIRED if not (missing_module and name.endswith("mhi_wwan_ctrl.ko"))]
        archive = cpio(paths)
        self.initramfs = self.work / "initramfs_data.cpio"
        self.initramfs.write_bytes(archive)
        image = bytearray(64)
        image[56:60] = b"ARM\x64"
        image += archive
        if oversized:
            image += b"\0" * (0x3000000 - len(image))
        struct.pack_into("<Q", image, 16, len(image))
        self.payload = gzip.compress(image, mtime=0)
        (self.work / "kernel.gz").write_bytes(self.payload)
        phy = "phy9" if swapped_phy else "phy8"
        (self.work / "board.dts").write_text(f'''/dts-v1/;
/ {{
    model = "OPPO CKB01 (SoftBank Air 5)";
    compatible = "{board}", "qcom,ipq8074";
    #address-cells = <2>; #size-cells = <2>;
    qcom,board-id = <8 0>;
    memory@40000000 {{ device_type = "memory"; reg = <0 0x40000000 0 0x20000000>; }};
    soc {{
        #address-cells = <1>; #size-cells = <1>; ranges;
        mdio@90000 {{
            reg = <0x90000 0x64>;
            #address-cells = <1>; #size-cells = <0>;
            ethernet-phy-package@8 {{
                reg = <8>; #address-cells = <1>; #size-cells = <0>;
                compatible = "qcom,qca8075-package";
                phy8: ethernet-phy@8 {{ reg = <8>; }};
                phy9: ethernet-phy@9 {{ reg = <9>; }};
            }};
        }};
        ppe@3a000000 {{
            reg = <0x3a000000 0x900000>;
            ports {{
                #address-cells = <1>; #size-cells = <0>;
                port@1 {{ reg = <1>; label = "lan"; phy-mode = "psgmii"; phy-handle = <&{phy}>; }};
                port@2 {{ reg = <2>; label = "wan"; phy-mode = "psgmii"; phy-handle = <&phy9>; }};
            }};
        }};
    }};
}};
''')
        subprocess.run(["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", str(self.work / "board.dtb"),
                        str(self.work / "board.dts")], check=True, capture_output=True)
        (self.work / "image.its").write_text('''/dts-v1/;
/ {
    description = "CKB01 test fixture"; #address-cells = <1>;
    images {
        kernel@1 {
            data = /incbin/("kernel.gz"); type = "kernel"; arch = "arm64"; os = "linux";
            compression = "gzip"; load = <0x41000000>; entry = <0x41000000>;
            hash@1 { algo = "crc32"; }; hash@2 { algo = "sha1"; };
        };
        fdt@1 {
            data = /incbin/("board.dtb"); type = "flat_dt"; arch = "arm64"; compression = "none";
            hash@1 { algo = "crc32"; }; hash@2 { algo = "sha1"; };
        };
    };
    configurations {
        default = "config@1";
        config@1 { description = "CKB01"; kernel = "kernel@1"; fdt = "fdt@1"; };
    };
};
''')
        self.source = self.work / "source.itb"
        subprocess.run(["mkimage", "-f", str(self.work / "image.its"), str(self.source)],
                       cwd=self.work, check=True, capture_output=True)

    def package(self):
        return subprocess.run([sys.executable, str(PACKAGER), str(self.source),
                               "--initramfs", str(self.initramfs), "--output", str(self.work / "out")],
                              text=True, capture_output=True)

    def test_valid_image_has_identical_usb_alias_and_boot_configurations(self):
        self.make_fit()
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.work / "out"
        image = output / "openwrt-qualcommax-ipq807x-oppo_ckb01-initramfs-uImage.itb"
        self.assertEqual(image.read_bytes(), (output / "uimage-initramfs.itb").read_bytes())
        self.assertIn(hashlib.sha256(image.read_bytes()).hexdigest(), (output / "sha256sums").read_text())
        alias = subprocess.check_output(["fdtget", "-t", "s", str(image),
                                         "/configurations/config@hk09", "kernel"], text=True).strip()
        self.assertEqual(alias, "kernel@1")

    def test_other_board_cannot_be_relabelled_as_ckb01(self):
        self.make_fit(board="prpl,haze")
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("compatible", result.stderr)

    def test_missing_mhi_module_is_not_published(self):
        self.make_fit(missing_module=True)
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mhi_wwan_ctrl", result.stderr)
        self.assertFalse((self.work / "out" / "uimage-initramfs.itb").exists())

    def test_corrupted_payload_fails_hash_verification(self):
        self.make_fit()
        contents = self.source.read_bytes()
        position = contents.index(self.payload)
        damaged = bytearray(contents)
        damaged[position + 10] ^= 1
        self.source.write_bytes(damaged)
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", result.stderr.lower())

    def test_kernel_cannot_overlap_the_uboot_fit_buffer(self):
        self.make_fit(oversized=True)
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("0x44000000", result.stderr)

    def test_swapped_or_duplicate_phy_binding_is_rejected(self):
        self.make_fit(swapped_phy=True)
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PHY", result.stderr)


if __name__ == "__main__":
    unittest.main()
