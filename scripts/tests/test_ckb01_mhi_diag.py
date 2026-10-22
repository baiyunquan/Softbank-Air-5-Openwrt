"""Contracts for the opt-in CKB01 event-consumption experiment."""
from pathlib import Path
import os
import json
import subprocess
import tempfile
import time
import signal
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'patches/tree/ckb01/0006-qualcommax-ckb01-mhi-diagnostics.patch'
TOOL = ROOT / 'packages/ckb01-modem/files/ckb01-mhi-debug'


def kernel_patch():
    if not PATCH.exists():
        return ''
    return '\n'.join(line[1:] for line in PATCH.read_text().splitlines()
                     if line.startswith('+') and not line.startswith('+++'))


class KernelDiagnostics(unittest.TestCase):
    def test_dwc_patch_applies_to_pinned_openwrt_backports(self):
        import shutil
        import re
        fixture = ROOT / 'scripts/tests/fixtures/ckb01-pinned-dwc'
        inner = ''.join(line[1:] + '\n' for line in PATCH.read_text().splitlines()[3:])
        sections = re.split(r'(?=^--- (?:a/|/dev/null))', inner, flags=re.M)
        patch = ''.join(section for section in sections
                        if '+++ b/drivers/pci/controller/dwc/' in section) + '\n'
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(fixture, tmp, dirs_exist_ok=True)
            result = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'],
                                    cwd=tmp, input=patch, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            source = (Path(tmp)/'drivers/pci/controller/dwc/pcie-designware-host.c').read_text()
            self.assertIn('generic_handle_demux_domain_irq', source)
            self.assertIn('.irq_pre_redirect', source)
            self.assertIn('irq_chip_redirect_set_affinity', source)
            self.assertNotIn('generic_handle_domain_irq(pp->irq_domain', source)

    def test_fault_gates_mmio_before_diagnostic_abort(self):
        section=kernel_patch().split('--- a/drivers/bus/mhi/host/pci_generic.c\n')[-1].split('--- a/')[0]
        gate=section.find('pm_state = MHI_PM_LD_ERR_FATAL_DETECT')
        abort=section.find('mhi_diag_abort')
        self.assertTrue(0 <= gate < abort, 'fatal PM gate must precede abort and the fault dump')

    def test_dwc_trace_uses_an_expiring_monotonic_deadline(self):
        self.assertTrue('ktime_get_ns() < READ_ONCE(diag->deadline_ns)' in kernel_patch(),
                        'zero/jiffies wrap must not enable early-boot or stopped logging')

    def test_poll_cannot_wait_behind_a_long_pm_operation(self):
        self.assertIn('mutex_trylock(&cntrl->pm_mutex)', kernel_patch())

    def test_bad_completion_is_reported_to_the_software_consumer(self):
        text = kernel_patch()
        self.assertIn('mhi_event->diag_polling && ret < 0', text)
        self.assertIn('ret = -EIO', text)

    def test_poll_is_bounded_and_default_off(self):
        text = kernel_patch()
        for item in ['CKB01_POLL_MS 20', 'CKB01_WINDOW_MS 30000',
                     'CKB01_POLL_BUDGET 64', 'CKB01_TOTAL_BUDGET 4096',
                     'ckb01_diag', 'ckb01_poll', 'cancel_delayed_work_sync',
                     'spin_lock_bh(&ev->lock)', 'pm_mutex', 'raw_budget']:
            self.assertIn(item, text)
        self.assertIn('static const u32 rings[] = { 1, 2, 4, 5 }', text)
        self.assertNotIn('mhi_soc_reset(cntrl)', text)

    def test_mapping_and_boundary_counters_are_instrumented(self):
        text = kernel_patch()
        for item in ['CKB01-MHI', 'msivec', 'parent_data', 'msi_msg',
                     'PCIE_MSI_INTR0_STATUS', 'PCIE_MSI_INTR0_MASK',
                     'PCIE_MSI_INTR0_ENABLE', 'generic_handle_demux_domain_irq',
                     'MHI_DIAG_IRQ', 'MHI_DIAG_TASK', 'MHI_DIAG_EVENT',
                     'MHI_DIAG_COMPLETE', 'MHI_DIAG_CH_DB', 'MHI_DIAG_ER_DB',
                     'MHI_DIAG_NET_RX', 'MHI_DIAG_REFILL', 'MHI_DIAG_QMI_RX',
                     'dma_rmb()', 'IS_ALIGNED', 'get_unaligned_le64']:
            self.assertIn(item, text)


class Collector(unittest.TestCase):
    def test_exit_terminates_probe_process_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env,_=self.fixture(root)
            program=root/'bin/fake'
            text=program.read_text()
            text=text.replace("else:\n  ok=poll or", "else:\n  import subprocess,time\n  child=subprocess.Popen(['sleep','25'])\n  (root/('probe-'+str(os.getpid()))).write_text(str(child.pid))\n  time.sleep(25)\n  ok=poll or")
            program.write_text(text)
            process=subprocess.Popen(['sh',str(TOOL),'compare',str(root/'out')],env=env,
                                     stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                until=time.monotonic()+8
                while not list(root.glob('probe-*')) and time.monotonic()<until:time.sleep(.05)
                self.assertTrue(list(root.glob('probe-*')), 'fixture did not launch a probe child')
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
                children=[int(p.read_text()) for p in root.glob('probe-*')]
                until=time.monotonic()+3
                def active(pid):
                    try:return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
                    except FileNotFoundError:return False
                while any(active(pid) for pid in children) and time.monotonic()<until:time.sleep(.05)
                self.assertFalse(any(active(pid) for pid in children), 'probe descendants survived collector exit')
            finally:
                if process.poll() is None:process.kill();process.wait()
                # Always clean up the deliberately failing fixture before returning.
                for p in root.glob('probe-*'):
                    try:os.kill(int(p.read_text()),signal.SIGKILL)
                    except ProcessLookupError:pass

    def fixture(self, root, enabled=0):
        board = root / 'sys/firmware/devicetree/base'
        board.mkdir(parents=True)
        (board/'compatible').write_bytes(b'oppo,ckb01\0qcom,ipq8074\0')
        pci = root/'sys/bus/pci/devices/0000:01:00.0'
        pci.mkdir(parents=True)
        for name, value in dict(vendor='0x17cb',device='0x0306',
                                subsystem_vendor='0x17cb',subsystem_device='0x010c').items():
            (pci/name).write_text(value+'\n')
        controller=root/'debug/mhi0';controller.mkdir(parents=True)
        (controller/'ckb01_diag').write_text(f'enabled={enabled} polling=0\npci=0000:01:00.0 alive=1\n')
        (controller/'ckb01_poll').write_text('untouched')
        proc=root/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
        (proc/'uptime').write_text('1000.1 3000.2\n')
        (proc/'interrupts').write_text('86: 79 0 0 0 mhi\n88: 0 0 0 0 mhi\n')
        (proc/'sys/kernel/random/boot_id').write_text('test-boot\n')
        binpath=root/'bin';binpath.mkdir()
        program=binpath/'fake'
        program.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
root=Path(os.environ['FIXTURE'])
args=sys.argv[1:]
with (root/'calls').open('a') as f:f.write(json.dumps([name,*args])+'\\n')
poll=(root/'debug/mhi0/ckb01_poll').read_text().strip()=='start'
if name=='ckb01-modem':
 if args==['discover']:
  print(json.dumps(dict(ok=True,pci='0000:01:00.0',management='mhi_swip0',control='/dev/wwan0qmi0')))
 else:
  ok=poll or 'qrtr' in args
  print(json.dumps(dict(ok=ok,revision=dict(ok=ok,revision='fixture-baseband'))))
  sys.exit(0 if ok else 1)
elif name=='jsonfilter':
 value=json.loads(Path(args[args.index('-i')+1]).read_text())
 print(value[args[args.index('-e')+1][2:]])
elif name=='ip':print('inet 169.254.10.1/24 dev mhi_swip0')
elif name=='ping':
 print('received='+str(int(poll)))
 sys.exit(0 if poll else 1)
elif name=='dmesg':print('CKB01-MHI stage=fixture')
''')
        program.chmod(0o755)
        for name in ['ckb01-modem','jsonfilter','ip','ping','dmesg']:
            (binpath/name).symlink_to(program)
        env=dict(os.environ,FIXTURE=str(root),PATH=str(binpath)+':'+os.environ['PATH'],
                 CKB01_MHI_SYS_ROOT=str(root/'sys'),CKB01_MHI_PROC_ROOT=str(proc),
                 CKB01_MHI_DEBUG_ROOT=str(root/'debug'),CKB01_MHI_PCIE_ROOT=str(root/'pcie'),
                 CKB01_MHI_TIMEOUT='/usr/bin/timeout',CKB01_MHI_LOCK=str(root/'lock'))
        return env, controller

    def test_compare_preserves_transport_failures_and_stops_polling(self):
        self.assertTrue(TOOL.exists(), 'stdout collector is missing')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env,controller=self.fixture(root)
            out=root/'out'
            result=subprocess.run(['sh',str(TOOL),'compare',str(out)],env=env,
                                  text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual((out/'baseline-qmi.rc').read_text().strip(),'1')
            self.assertEqual((out/'poll-qmi.rc').read_text().strip(),'0')
            self.assertEqual((out/'stopped-qmi.rc').read_text().strip(),'1')
            self.assertEqual((out/'baseline-qrtr.rc').read_text().strip(),'0')
            self.assertEqual((controller/'ckb01_poll').read_text().strip(),'stop')
            self.assertFalse((root/'lock').exists())
            self.assertEqual(result.stdout.count('stage=poll_start'),1)

    def test_snapshot_never_starts_polling_or_queries_the_modem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env,controller=self.fixture(root)
            result=subprocess.run(['sh',str(TOOL),'snapshot',str(root/'out')],env=env,
                                  text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual((controller/'ckb01_poll').read_text(),'untouched')
            calls=[json.loads(line) for line in (root/'calls').read_text().splitlines()]
            self.assertFalse(any('probe' in call for call in calls))

    def test_existing_window_is_not_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env,controller=self.fixture(root,enabled=1)
            result=subprocess.run(['sh',str(TOOL),'compare',str(root/'out')],env=env,
                                  text=True,capture_output=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('another diagnostic window',result.stderr)
            self.assertEqual((controller/'ckb01_poll').read_text(),'untouched')

    def test_tool_is_installed_and_not_a_boot_recovery(self):
        self.assertTrue(TOOL.exists(), 'stdout collector is missing')
        subprocess.run(['sh', '-n', str(TOOL)], check=True)
        package = (ROOT / 'packages/ckb01-modem/Makefile').read_text()
        self.assertIn('./files/ckb01-mhi-debug', package)
        bootstrap = (ROOT / 'packages/ckb01-modem/files/ckb01-modem-wait').read_text()
        self.assertNotIn('ckb01_poll', bootstrap)
        self.assertNotIn('ckb01-mhi-debug compare', bootstrap)

    def test_other_board_cannot_start_poll(self):
        self.assertTrue(TOOL.exists(), 'stdout collector is missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board = root / 'sys/firmware/devicetree/base'
            board.mkdir(parents=True)
            (board / 'compatible').write_bytes(b'other,board\0')
            debug = root / 'debug/mhi0'
            debug.mkdir(parents=True)
            poll = debug / 'ckb01_poll'
            poll.write_text('untouched')
            env = dict(os.environ, CKB01_MHI_SYS_ROOT=str(root/'sys'),
                       CKB01_MHI_DEBUG_ROOT=str(root/'debug'))
            result = subprocess.run(['sh', str(TOOL), 'compare', str(root/'out')],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(poll.read_text(), 'untouched')
            self.assertIn('board', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
