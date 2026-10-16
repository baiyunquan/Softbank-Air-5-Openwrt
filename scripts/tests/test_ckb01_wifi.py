"""Run the real shell helpers against files and simulated hardware readiness."""

import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "devices/oppo_ckb01/files/lib/functions/ckb01-wifi.sh"


class WifiHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ckb01-wifi-test-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    def shell(self, script):
        self.assertTrue(LIBRARY.is_file(), "CKB01 wireless helpers have not been implemented")
        return subprocess.run(["sh", "-c", f'. {shlex.quote(str(LIBRARY))}\n{script}'],
                              cwd=self.work, text=True, capture_output=True,
                              env={**os.environ, "LC_ALL": "C"})

    def art(self, *, corrupt=False, short=False):
        # Independent little-endian XOR fixture: only word 0 is 0xffff.
        cal = bytearray(131072)
        cal[:2] = b"\xff\xff"
        if corrupt:
            cal[100] = 1
        data = bytearray(262144)
        data[4096:4096 + len(cal)] = cal
        (self.work / "art").write_bytes(data[:10000] if short else data)
        return bytes(cal)

    def test_extracts_exact_oem_slice_without_modifying_art(self):
        cal = self.art()
        before = (self.work / "art").read_bytes()
        result = self.shell('ckb01_caldata_extract art 262144 cal.bin state')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.work / "cal.bin").read_bytes(), cal)
        self.assertEqual((self.work / "art").read_bytes(), before)
        self.assertIn(hashlib.sha256(cal).hexdigest(), (self.work / "state").read_text())

    def test_missing_art_never_publishes_calibration(self):
        result = self.shell('ckb01_caldata_extract absent 262144 cal.bin state')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "cal.bin").exists())

    def test_short_read_never_publishes_calibration(self):
        self.art(short=True)
        result = self.shell('ckb01_caldata_extract art 262144 cal.bin state')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "cal.bin").exists())

    def test_bad_xor_never_publishes_calibration(self):
        self.art(corrupt=True)
        result = self.shell('ckb01_caldata_extract art 262144 cal.bin state')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "cal.bin").exists())
        self.assertIn("checksum", (self.work / "state").read_text())

    def test_wrong_partition_size_is_rejected(self):
        self.art()
        result = self.shell('ckb01_caldata_extract art 524288 cal.bin state')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "cal.bin").exists())

    def test_disagreeing_reads_are_rejected(self):
        self.art()
        # dd is the hardware read boundary; emulate a changing flash read.
        result = self.shell('''
dd() { command dd "$@"; printf '\\001' | command dd of=art bs=1 seek=4200 conv=notrunc 2>/dev/null; }
ckb01_caldata_extract art 262144 cal.bin state
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "cal.bin").exists())

    def test_valid_mac_is_preserved_and_examples_are_replaced_stably(self):
        result = self.shell('''
ckb01_wifi_mac 24:12:34:56:78:90 unit 2g ''
ckb01_wifi_mac 00:03:7f:12:34:56 unit 2g ''
ckb01_wifi_mac 00:03:7f:12:34:56 unit 2g ''
ckb01_wifi_mac 00:03:7f:12:34:56 unit 5g ''
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        macs = result.stdout.splitlines()
        self.assertEqual(macs[0], "24:12:34:56:78:90")
        self.assertEqual(macs[1], macs[2])
        self.assertNotEqual(macs[1], macs[3])
        self.assertEqual(int(macs[1][:2], 16) & 3, 2)

    def test_duplicate_mac_gets_a_distinct_address(self):
        result = self.shell("ckb01_wifi_mac 24:12:34:56:78:90 unit 2g '24:12:34:56:78:90'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(result.stdout.strip(), "24:12:34:56:78:90")

    def test_preferred_channels_and_complete_80mhz_block_are_checked(self):
        (self.work / "info").write_text('''
 * 2412 MHz [1] (20.0 dBm)
 * 5180 MHz [36] (20.0 dBm)
 * 5200 MHz [40] (20.0 dBm)
 * 5220 MHz [44] (20.0 dBm)
 * 5240 MHz [48] (20.0 dBm)
''')
        result = self.shell('ckb01_wifi_channel 2g info; ckb01_wifi_channel 5g info')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["1", "36"])
        (self.work / "info").write_text(' * 5180 MHz [36] (20.0 dBm)\n * 5200 MHz [40] (disabled)\n')
        result = self.shell('ckb01_wifi_channel 5g info')
        self.assertNotEqual(result.returncode, 0)

    def test_delayed_wireless_readiness_is_retried(self):
        result = self.shell('''
attempt=0
sleep() { :; }
ckb01_wifi_try() { attempt=$((attempt + 1)); [ "$attempt" -eq 3 ]; }
ckb01_wifi_wait 4
echo "$attempt"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "3")

    def test_no_80mhz_block_falls_back_to_149(self):
        (self.work / "info").write_text('''
 * 5180 MHz [36] (20.0 dBm) (no 80MHz)
 * 5200 MHz [40] (20.0 dBm)
 * 5220 MHz [44] (20.0 dBm)
 * 5240 MHz [48] (20.0 dBm)
 * 5745 MHz [149] (20.0 dBm)
 * 5765 MHz [153] (20.0 dBm)
 * 5785 MHz [157] (20.0 dBm)
 * 5805 MHz [161] (20.0 dBm)
''')
        result = self.shell('ckb01_wifi_channel 5g info')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "149")

    def test_single_band_does_not_report_dual_band_success(self):
        result = self.shell('''
attempt=0
sleep() { :; }
ckb01_wifi_try() { attempt=$((attempt + 1)); return 1; }
ckb01_wifi_wait 3
result=$?
echo "$attempt"
exit "$result"
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "3")

    def test_radio_initialization_configures_ap_once(self):
        (self.work / "info").write_text(' HE Iftypes: managed, AP\n * 2412 MHz [1] (20.0 dBm)\n')
        result = self.shell('''
uci() {
    [ "$1" != -q ] || shift
    case "$1" in
        get) [ -e initialized ] && echo 1 ;;
        batch) cat >> batch; touch initialized ;;
        *) return 1 ;;
    esac
}
ckb01_wifi_configure_radio radio0 phy1 2g info 24:12:34:56:78:90 unit '' || exit 1
cp batch initial-batch
ckb01_wifi_configure_radio radio0 phy1 2g info 24:12:34:56:78:90 unit '' || exit 1
cmp -s initial-batch batch
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        batch = (self.work / "batch").read_text()
        self.assertIn(".ssid='Air5-2G'", batch)
        self.assertIn(".country='CN'", batch)
        self.assertIn(".htmode='HE20'", batch)
        self.assertIn(".channel='1'", batch)
        self.assertIn(".key='Air5-OpenWrt'", batch)
        self.assertIn(".macaddr='24:12:34:56:78:90'", batch)
        self.assertIn(".network='lan'", batch)

    def test_bdf_is_reproducible_and_contains_the_oem_payload(self):
        script = ROOT / "scripts/ckb01-bdf.py"
        self.assertTrue(script.is_file(), "BDF reproducibility helper is missing")
        output = self.work / "board-2.bin"
        result = subprocess.run([sys.executable, str(script), "--output", str(output)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output.read_bytes()
        self.assertTrue(data.startswith(b"QCA-ATH11K-BOARD\0"))
        self.assertIn(b"bus=ahb,qmi-chip-id=0,qmi-board-id=255,variant=OPPO-CKB01", data)
        raw = (ROOT / "devices/oppo_ckb01/firmware/bdwlan.bin").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "9fdaff50396c03e097f713067df149be3c9b1d36689e4d20eff455f00c886944")
        self.assertIn(raw, data)
        output.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        result = subprocess.run([sys.executable, str(script), "--check", "--output", str(output)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
