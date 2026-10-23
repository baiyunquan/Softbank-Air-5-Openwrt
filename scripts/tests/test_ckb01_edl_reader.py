#!/usr/bin/env python3
"""Compile and exercise the actual C reader against a fragmented PTY programmer.

No modem/device access: the only character device opened is a newly-created PTY.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import pty
import resource
import select
import signal
import struct
import subprocess
import tempfile
import threading
import tty
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages/ckb01-edl/src'
PAGE, ERASE, EFS_LEN = 4096, 262144, 11534336
ACK = b'<data><response value="ACK"/></data>'
RAW_ACK = b'<data><log value="read ready"/><response value="ACK" rawmode="true"/></data>'
FINAL_ACK = b'<data><response value="ACK" rawmode="false"/></data>'
PATTERN = (bytes(range(256)) + b'\x00\n</data><response value="NAK"/>\xff') * 64
EFS = (b'\n \r\t' + PATTERN * (EFS_LEN // len(PATTERN) + 1))[:EFS_LEN]


def make_mibib():
    data = bytearray(b'\xff' * ERASE)
    struct.pack_into('<4I', data, 0, 0xFE569FAC, 0xCD7F127A, 4, 1)
    struct.pack_into('<4I', data, PAGE, 0x55EE73AA, 0xE35EBDDB, 4, 27)
    for i in range(27):
        name, start, length = f'part{i}'.encode(), 70 + i, 1
        if i == 0:
            name, start, length = b'sbl', 0, 10
        elif i == 1:
            name, start, length = b'mibib', 10, 10
        elif i == 2:
            name, start, length = b'efs2', 20, 44
        struct.pack_into('<16sII4B', data, PAGE + 16 + 28*i,
                         name, start, length, 255, 1, 255, 0)
    return data


class Programmer:
    def __init__(self, master, **options):
        self.master, self.options = master, options
        self.commands, self.errors = [], []
        self.pending = b''
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def send(self, data, fragmented=False):
        sizes = (1, 2, 5, 3, 17, 4099, 12001, 65536) if fragmented else (65536,)
        i = 0
        while data and not self.stopped.is_set():
            size = sizes[i % len(sizes)]
            n = os.write(self.master, data[:size])
            data = data[n:]
            i += 1

    def command(self):
        while b'</data>' not in self.pending:
            readable, _, _ = select.select([self.master], [], [], 0.1)
            if self.stopped.is_set():
                return None
            if not readable:
                continue
            self.pending += os.read(self.master, 65536)
        before, self.pending = self.pending.split(b'</data>', 1)
        root = ET.fromstring(before + b'</data>')
        self.commands.append(root[0])
        return root[0]

    def serve(self):
        try:
            configure = self.command()
            if configure is None:
                return
            assert configure.tag == 'configure', configure.tag
            assert configure.attrib['MemoryName'] == 'nand'
            assert configure.attrib['MaxPayloadSizeToTargetInBytes'] == '16384'
            if self.options.get('malformed'):
                self.send(b'<data><response value="ACK"></data>', True)
                return
            if self.options.get('configure_nak'):
                self.send(b'<data><response value="NAK"/></data>', True)
                return
            self.send(self.options.get('configure', b'<data><response value="ACK" MaxPayloadSizeToTargetInBytes="16384" MaxPayloadSizeToTargetInBytesSupported="16384"/></data>'), True)
            info = self.command()
            if info is None:
                return
            assert info.tag == 'getstorageinfo', info.tag
            geometry = self.options.get('geometry', {'page_size': PAGE, 'block_size': ERASE, 'total_blocks': 2048, 'mem_type': 'nand'})
            text = geometry if isinstance(geometry, str) else json.dumps(geometry)
            log = ET.Element('data')
            ET.SubElement(log, 'log', value='storage_info: ' + text)
            if self.options.get('separate_info'):
                self.send(ET.tostring(log) + ACK, True)
            else:
                ET.SubElement(log, 'response', value='ACK')
                self.send(ET.tostring(log), True)
            for index in range(3):
                cmd = self.command()
                if cmd is None:
                    return
                assert cmd.tag == 'read', cmd.tag
                assert cmd.attrib['SECTOR_SIZE_IN_BYTES'] == str(PAGE)
                assert cmd.attrib['PAGES_PER_BLOCK'] == '64'
                assert cmd.attrib['physical_partition_number'] == '0'
                assert int(cmd.attrib['start_sector']) == (640 if index == 0 else 1280)
                assert int(cmd.attrib['num_partition_sectors']) == (64 if index == 0 else 2816)
                if self.options.get('read_nak') == index:
                    self.send(b'<data><response value="NAK"/></data>', True)
                    return
                data = bytes(self.options.get('mibib', make_mibib())) if index == 0 else EFS
                if index == 2 and self.options.get('mismatch'):
                    data = bytes([data[0] ^ 1]) + data[1:]
                if self.options.get('short_read') == index:
                    self.send(RAW_ACK + data[:10000], True)
                    return  # leave PTY open to exercise the actual timeout
                final = FINAL_ACK
                if self.options.get('final_nak') == index:
                    final = b'<data><response value="NAK" rawmode="false"/></data>'
                if self.options.get('missing_final') == index:
                    final = b''
                # ACK + >4 KiB of binary are one stream, and tail ACK follows
                # the final raw byte with no separating driver read guaranteed.
                self.send(RAW_ACK + data + final, True)
        except OSError as exc:
            if exc.errno not in (errno.EIO, errno.EBADF):
                self.errors.append(exc)
        except Exception as exc:  # propagate mock assertions into unittest
            self.errors.append(exc)


class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='ckb01-reader-build-')
        cls.executable = Path(cls.build.name) / 'ckb01-firehose-read'
        flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'libxml-2.0', 'json-c'], text=True).split()
        fake_space = Path(cls.build.name) / 'fake-space.c'
        fake_space.write_text('#include <sys/statvfs.h>\n#include <string.h>\n'
                              'int fstatvfs(int fd, struct statvfs *s) { (void)fd; '
                              'memset(s, 0, sizeof(*s)); s->f_frsize=4096; s->f_bavail=1; return 0; }\n')
        cls.fake_space = Path(cls.build.name) / 'fake-space.so'
        subprocess.run(['cc', '-shared', '-fPIC', '-D_FILE_OFFSET_BITS=64', '-Wall', '-Wextra', '-Werror',
                        '-o', str(cls.fake_space), str(fake_space)], check=True)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-DCKB01_IO_TIMEOUT_MS=500', '-o', str(cls.executable),
                        *map(str, sorted(SRC.glob('*.c'))), *flags], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def run_reader(self, *, preexisting=None, disk_limit=False, space_limit=False, **options):
        self.temp = tempfile.TemporaryDirectory(prefix='ckb01-reader-test-')
        self.addCleanup(self.temp.cleanup)
        output = Path(self.temp.name)
        if preexisting:
            (output / preexisting).write_bytes(b'KEEP')
        master, slave = pty.openpty()
        tty.setraw(slave)
        mock = Programmer(master, **options)
        def limit():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024, 1024*1024))
        environment = os.environ.copy()
        if space_limit:
            environment['LD_PRELOAD'] = str(self.fake_space)
        child = subprocess.Popen([str(self.executable), '--device', os.ttyname(slave), '--output', str(output)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 preexec_fn=limit if disk_limit else None, env=environment)
        mock.thread.start()
        try:
            stdout, stderr = child.communicate(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            mock.stopped.set()
            mock.thread.join(timeout=2)
            os.close(master)
            os.close(slave)
        self.assertFalse(mock.errors, mock.errors)
        report = json.loads((output/'report.json').read_text()) if (output/'report.json').exists() and preexisting != 'report.json' else None
        return child.returncode, output, report, mock.commands, stdout, stderr

    def assert_failure(self, result, text=None):
        rc, output, report, _, _, stderr = result
        self.assertNotEqual(rc, 0, stderr)
        self.assertFalse(report['transport_complete'])
        self.assertFalse((output/'efs2-pass1.bin').exists())
        self.assertFalse((output/'efs2-pass2.bin').exists())
        if text:
            self.assertIn(text, report.get('error', ''))
        return output, report

    def test_full_fragmented_two_pass_stream_including_xml_like_binary(self):
        rc, output, report, commands, _, stderr = self.run_reader()
        self.assertEqual(rc, 0, stderr)
        self.assertTrue(report['transport_complete'])
        self.assertEqual(len(commands), 5)
        for name in ('efs2-pass1.bin', 'efs2-pass2.bin'):
            self.assertEqual((output/name).read_bytes(), EFS)
        self.assertEqual(report['pass1_sha256'], hashlib.sha256(EFS).hexdigest())
        self.assertEqual(report['pass1_sha256'], report['pass2_sha256'])
        self.assertEqual((output/'mibib.bin').read_bytes(), bytes(make_mibib()))
        self.assertEqual(report['storage']['total_bytes'], 536870912)
        self.assertIn('unreported', report['bad_block_policy'])
        self.assertFalse(report['restoration_verified'])
        self.assertIn(b'rawmode="false"', (output/'firehose.xml.log').read_bytes())
        self.assertFalse(list(output.glob('*.partial')))

    def test_key_value_geometry(self):
        rc, _, report, _, _, stderr = self.run_reader(geometry='page_size=4096 block_size=262144 total_blocks=2048', separate_info=True)
        self.assertEqual(rc, 0, stderr)
        self.assertTrue(report['transport_complete'])

    def test_storage_xml_over_four_kib_and_reported_bad_block_policy(self):
        result = self.run_reader(geometry={'page_size':PAGE, 'block_size':ERASE,
                                 'total_blocks':2048, 'padding':'x'*12000,
                                 'bad_block_policy':'skip-bad-blocks'})
        self.assertEqual(result[0], 0, result[-1])
        self.assertEqual(result[2]['bad_block_policy'], 'skip-bad-blocks')
        self.assertEqual(result[2]['bad_block_policy_source'], 'programmer getstorageinfo')

    def test_free_space_preflight_stops_before_device_command(self):
        result = self.run_reader(space_limit=True)
        self.assert_failure(result, 'Insufficient free')
        self.assertEqual(result[3], [])

    def test_malformed_xml(self):
        result = self.run_reader(malformed=True)
        output, _ = self.assert_failure(result, 'Malformed Firehose XML')
        self.assertIn(b'RX-INCOMPLETE', (output/'firehose.xml.log').read_bytes())

    def test_configure_nak(self):
        self.assert_failure(self.run_reader(configure_nak=True), 'NAK')

    def test_missing_payload_bound(self):
        self.assert_failure(self.run_reader(configure=ACK), 'Missing negotiated')

    def test_invalid_payload_bound(self):
        self.assert_failure(self.run_reader(configure=b'<data><response value="ACK" MaxPayloadSizeToTargetInBytes="4294967295"/></data>'), 'payload bound')

    def test_geometry_mismatch_and_missing(self):
        for geometry in ({'page_size':2048, 'block_size':ERASE, 'total_blocks':2048},
                         {'page_size':PAGE, 'block_size':ERASE},
                         {'page_size':PAGE, 'block_size':ERASE, 'total_blocks':2**63},
                         {'page_size':PAGE, 'block_size':ERASE, 'total_blocks':2048, 'mem_type':'emmc'},
                         {'page_size':PAGE, 'block_size':ERASE, 'total_blocks':2048, 'mem_type':None}):
            with self.subTest(geometry=geometry):
                result = self.run_reader(geometry=geometry)
                self.assert_failure(result)
                self.assertEqual(len(result[3]), 2)

    def test_contradictory_geometry(self):
        self.assert_failure(self.run_reader(geometry={'page_size':PAGE, 'SECTOR_SIZE_IN_BYTES':2048, 'block_size':ERASE, 'total_blocks':2048}), 'geometry')

    def test_mibib_header_table_version_and_count(self):
        for offset, value in ((0, 0), (PAGE, 0), (PAGE+8, 3), (PAGE+12, 128), (8, 3), (PAGE+12, 0xFFFFFFFF)):
            with self.subTest(offset=offset, value=value):
                data = make_mibib()
                struct.pack_into('<I', data, offset, value)
                result = self.run_reader(mibib=data)
                self.assert_failure(result, 'MIBIB')
                self.assertEqual(len(result[3]), 3)

    def test_mibib_bounds_and_efs_geometry(self):
        for offset, value in ((PAGE+16+28*2+16, 21),
                              (PAGE+16+28*2+20, 43),
                              (PAGE+16+28*3+16, 2048),
                              (PAGE+16+28*3+20, 0xFFFFFFFE),
                              (PAGE+16+28*3+16, 74)):
            with self.subTest(offset=offset, value=value):
                data = make_mibib()
                struct.pack_into('<I', data, offset, value)
                self.assert_failure(self.run_reader(mibib=data))

    def test_read_nak(self):
        output, _ = self.assert_failure(self.run_reader(read_nak=1), 'NAK')
        self.assertEqual((output/'efs2-pass1.bin.partial').stat().st_size, 0)

    def test_short_read_timeout_retains_exact_partial_without_retry(self):
        result = self.run_reader(short_read=1)
        output, _ = self.assert_failure(result, 'timeout')
        self.assertEqual((output/'efs2-pass1.bin.partial').read_bytes(), EFS[:10000])
        self.assertEqual(len(result[3]), 4)

    def test_missing_final_ack_retains_complete_partial(self):
        result = self.run_reader(missing_final=1)
        output, _ = self.assert_failure(result, 'timeout')
        self.assertEqual((output/'efs2-pass1.bin.partial').stat().st_size, EFS_LEN)
        self.assertEqual(len(result[3]), 4)

    def test_final_nak(self):
        output, _ = self.assert_failure(self.run_reader(final_nak=1), 'NAK')
        self.assertEqual((output/'efs2-pass1.bin.partial').stat().st_size, EFS_LEN)

    def test_double_hash_mismatch_keeps_both_partial(self):
        output, report = self.assert_failure(self.run_reader(mismatch=True), 'SHA256 mismatch')
        self.assertNotEqual(report['pass1_sha256'], report['pass2_sha256'])
        self.assertEqual((output/'efs2-pass1.bin.partial').stat().st_size, EFS_LEN)
        self.assertEqual((output/'efs2-pass2.bin.partial').stat().st_size, EFS_LEN)

    def test_disk_limit_retains_partial_and_stops(self):
        result = self.run_reader(disk_limit=True)
        output, _ = self.assert_failure(result, 'write failed')
        self.assertEqual((output/'efs2-pass1.bin.partial').stat().st_size, 1024*1024)
        self.assertEqual(len(result[3]), 4)

    def test_existing_output_never_overwritten_no_device_command(self):
        for name in ('report.json', 'efs2-pass1.bin', 'efs2-pass2.bin.partial', 'firehose.xml.log'):
            with self.subTest(name=name):
                result = self.run_reader(preexisting=name)
                self.assertNotEqual(result[0], 0)
                self.assertEqual((result[1]/name).read_bytes(), b'KEEP')
                self.assertEqual(result[3], [])


if __name__ == '__main__':
    unittest.main()
