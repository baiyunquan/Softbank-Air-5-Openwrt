#!/usr/bin/env python3
"""Exercise the USB packager with real mkimage/dtc-generated FITs."""

import gzip
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import tarfile
import unittest


PACKAGER = Path(__file__).resolve().parents[1] / "ckb01-fit.py"
REQUIRED = [
    "sbin/init", "sbin/netifd", "usr/sbin/dropbear", "www/cgi-bin/luci",
    "usr/sbin/ckb01-diag", "usr/sbin/ckb01-art-backup",
    "etc/uci-defaults/99-ckb01-network",
    "lib/modules/6.18/mhi_pci_generic.ko",
    "lib/modules/6.18/mhi_wwan_ctrl.ko",
]
WIRELESS_FILES = [
    "lib/functions/ckb01-wifi.sh", "etc/hotplug.d/firmware/10-ckb01-caldata",
    "etc/init.d/ckb01-wifi", "etc/rc.d/S95ckb01-wifi", "usr/sbin/ckb01-wifi-setup",
    "usr/sbin/iw", "usr/bin/iwinfo", "usr/sbin/hostapd",
    "lib/firmware/IPQ8074/q6_fw.mdt", "lib/firmware/IPQ8074/m3_fw.mdt",
    "lib/firmware/regulatory.db",
    "lib/modules/6.18/ath11k.ko", "lib/modules/6.18/ath11k_ahb.ko",
    "lib/modules/6.18/mac80211.ko", "lib/modules/6.18/cfg80211.ko",
]
WIRELESS_FILES += [f"lib/firmware/IPQ8074/q6_fw.b{index:02d}" for index in (0, 1, 2, 3, 4, 5, 7, 8)]
WIRELESS_FILES += [f"lib/firmware/IPQ8074/m3_fw.b{index:02d}" for index in (0, 1, 2)]
BDF_PATH = "lib/firmware/ath11k/IPQ8074/hw2.0/board-2.bin"
BDF = PACKAGER.parents[1] / "devices/oppo_ckb01/files" / BDF_PATH


def cpio(paths, contents=None):
    """Build a small newc archive without depending on the packager."""
    archive = bytearray()
    for number, name in enumerate([*paths, "TRAILER!!!"], 1):
        encoded = name.encode() + b"\0"
        payload = (contents or {}).get(name, b"")
        fields = [number, 0o100755, 0, 0, 1, 0, len(payload), 0, 0, 0, 0, len(encoded), 0]
        archive += b"070701" + b"".join(f"{value:08x}".encode() for value in fields)
        archive += encoded
        archive += b"\0" * (-len(archive) % 4)
        archive += payload
        archive += b"\0" * (-len(archive) % 4)
    return bytes(archive)


class Ckb01FitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ckb01-fit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def make_fit(self, *, board="oppo,ckb01", missing_module=False,
                 oversized=False, swapped_phy=False, wireless=False, bad_bdf=False, missing_segment=False,
                 compressed_initramfs=False, modem=False):
        paths = [name for name in REQUIRED if not (missing_module and name.endswith("mhi_wwan_ctrl.ko"))]
        contents = {}
        if wireless:
            paths += [*WIRELESS_FILES, BDF_PATH]
            contents = {name: b"test payload" for name in WIRELESS_FILES}
            contents[BDF_PATH] = b"wrong BDF" if bad_bdf else BDF.read_bytes()
            if missing_segment:
                paths.remove("lib/firmware/IPQ8074/q6_fw.b08")
        if modem:
            modem_paths = ["usr/sbin/ckb01-modem", "usr/bin/qmicli", "usr/libexec/qmi-proxy",
                           "lib/netifd/proto/ckb01_qmi.sh", "lib/netifd/ckb01-update",
                           "usr/sbin/ckb01-session", "usr/sbin/ckb01-modem-wait",
                           "etc/init.d/ckb01-modem", "etc/rc.d/S96ckb01-modem",
                           "usr/share/ckb01-modem/mbn-sha256.json"]
            modem_paths += [f"usr/lib/{lib}.so.1" for lib in ("libqmi-glib", "libqrtr-glib", "libjson-c", "libglib-2.0", "libgio-2.0", "libgobject-2.0")]
            modem_paths += [f"lib/modules/6.18/{module}.ko" for module in ("mhi_net", "qrtr-mhi", "qrtr", "rmnet")]
            paths += modem_paths
            contents.update({name: b"test modem payload" for name in modem_paths})
            # Keep the existing modem fixture aligned with the actual installed
            # OEM paths and immutable vendor hashes; no guessed global libraries.
            oem = PACKAGER.parents[1] / "packages/ckb01-oem-tools"
            oem_paths = ["usr/bin/oatprsync", "usr/bin/adb", "usr/libexec/timeout-coreutils",
                         "usr/sbin/ckb01-oem", "usr/sbin/ckb01-adb", "lib/functions/ckb01-oem.sh",
                         "usr/lib/ckb01-oem/adb-control.sh", "usr/share/ckb01-oem/adb-tcp-property.so",
                         "usr/share/ckb01-oem/adb-payload.json", "usr/share/ckb01-oem/runtime-provenance.json"]
            paths += oem_paths
            contents.update({name: b"OEM fixture" for name in oem_paths})
            contents["usr/share/ckb01-oem/adb-tcp-property.so"] = (oem / "payload/adb-tcp-property.so").read_bytes()
            with tarfile.open(oem / "vendor/runtime.tar.gz") as runtime:
                for entry in runtime.getmembers():
                    if entry.isfile():
                        name = "usr/lib/ckb01-oem/runtime/" + entry.name
                        paths.append(name)
                        contents[name] = runtime.extractfile(entry).read()
        archive = cpio(paths, contents)
        if compressed_initramfs:
            archive = subprocess.run(["zstd", "-q", "-c"], input=archive, capture_output=True,
                                     check=True).stdout
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
    reserved-memory {{
        #address-cells = <2>; #size-cells = <2>; ranges;
        wcnss@4b000000 {{ reg = <0 0x4b000000 0 0x3700000>; no-map; }};
        q6-etr@4e700000 {{ reg = <0 0x4e700000 0 0x100000>; no-map; }};
        m3@4e800000 {{ reg = <0 0x4e800000 0 0x100000>; no-map; }};
    }};
    soc {{
        #address-cells = <1>; #size-cells = <1>; ranges;
        wifi@c0000000 {{
            compatible = "qcom,ipq8074-wifi"; reg = <0xc000000 0x2000000>;
            status = "{'okay' if wireless else 'disabled'}";
            qcom,ath11k-fw-memory-mode = <1>;
            qcom,ath11k-calibration-variant = "OPPO-CKB01";
        }};
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
                port@1 {{ reg = <1>; label = "wan"; phy-mode = "psgmii"; phy-handle = <&{phy}>; }};
                port@2 {{ reg = <2>; label = "lan"; phy-mode = "psgmii"; phy-handle = <&phy9>; }};
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

    def package(self, wireless=False):
        return subprocess.run([sys.executable, str(PACKAGER), str(self.source),
                               "--initramfs", str(self.initramfs), "--output", str(self.work / "out"),
                               *(["--wireless"] if wireless else [])],
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

    def test_wireless_image_has_matching_board_data_and_runtime(self):
        self.make_fit(wireless=True)
        result = self.package(wireless=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wireless_checks_reject_a_wired_image(self):
        self.make_fit()
        result = self.package(wireless=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wireless", result.stderr.lower())

    def test_other_board_data_is_never_published(self):
        self.make_fit(wireless=True, bad_bdf=True)
        result = self.package(wireless=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BDF", result.stderr)

    def test_missing_firmware_segment_is_never_published(self):
        self.make_fit(wireless=True, missing_segment=True)
        result = self.package(wireless=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("q6_fw.b08", result.stderr)

    def workflow_package(self, *, misplaced=False):
        """Execute the actual CI step with the Linux 6.18 Kbuild output name."""
        self.make_fit(wireless=True, compressed_initramfs=True, modem=True)
        workspace = self.work / "workspace"
        workspace.mkdir()
        repo = PACKAGER.parents[1]
        (workspace / "builder").symlink_to(repo, target_is_directory=True)
        target = workspace / "openwrt/bin/targets/qualcommax/ipq807x"
        target.mkdir(parents=True)
        (target / "openwrt-qualcommax-ipq807x-oppo_ckb01-initramfs-uImage.itb").write_bytes(self.source.read_bytes())
        usr = workspace / "openwrt/build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq807x/linux-6.18.55/usr"
        usr.mkdir(parents=True)
        (usr / "initramfs_inc_data").write_bytes(b"unrelated bytes" if misplaced else self.initramfs.read_bytes())
        # Linux also keeps an uncompressed input; it is not what .incbin embeds.
        (usr / "initramfs_data.cpio").write_bytes(b"not the compressed incbin input")
        (workspace / "logs").mkdir()
        (workspace / "artifacts").mkdir()
        for name in ("source-versions.txt", "config.buildinfo"):
            (workspace / "logs" / name).write_text("workflow fixture\n")
        workflow = (repo / ".github/workflows/build-ckb01.yml").read_text()
        section = workflow.split("      - name: Validate and package USB initramfs\n", 1)[1]
        section = section.split("\n      - name:", 1)[0]
        script = section.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] for line in script.splitlines())
        result = subprocess.run(["bash", "-c", script], cwd=workspace, text=True, capture_output=True,
                                env={**os.environ, "GITHUB_SHA": "test-builder-sha", "UPSTREAM_SHA": "test-source-sha",
                                     "GITHUB_STEP_SUMMARY": str(workspace / "summary.md")})
        return result, workspace

    def test_actual_workflow_accepts_linux_618_incbin_output(self):
        result, workspace = self.workflow_package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((workspace / "artifacts/uimage-initramfs.itb").is_file())

    def test_actual_modem_workflow_validates_libexec_proxy_location(self):
        result, workspace = self.workflow_package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((workspace / "artifacts/fit-report.json").exists(), result.stdout)
        self.assertFalse((workspace / "artifacts/UNVALIDATED-FIT.txt").exists())

    def test_actual_workflow_preserves_fit_when_embedded_archive_validation_fails(self):
        result, workspace = self.workflow_package(misplaced=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (workspace / "artifacts/uimage-initramfs.itb").read_bytes(),
            self.source.read_bytes(),
        )
        self.assertIn("not embedded", (workspace / "logs/fit-validation.log").read_text())
        self.assertTrue((workspace / "artifacts/UNVALIDATED-FIT.txt").is_file())


if __name__ == "__main__":
    unittest.main()
