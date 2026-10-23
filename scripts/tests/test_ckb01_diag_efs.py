"""DIAG integration regression checks; the shared reader is tested against a PTY."""
from pathlib import Path
import os, subprocess, tempfile, threading, unittest
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'packages/ckb01-oem-tools'

class Reader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.exe=Path(cls.tmp.name)/'reader'
        src=PKG/'src/diag_efs_read.c'
        if src.exists():subprocess.run(['cc','-Wall','-Wextra','-Werror','-pthread',str(src),'-o',str(cls.exe)],check=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_hello_checks_crc_and_decodes_real_reply(self):
        self.assertTrue(self.exe.exists(),'packaged DIAG reader is missing')
        master,slave=os.openpty();dev=os.ttyname(slave)
        def crc(data):
            c=0xffff
            for b in data:
                c^=b
                for _ in range(8):c=(c>>1)^((c&1)*0x8408)
            return (~c)&0xffff
        def modem():
            data=bytearray()
            while not data.endswith(b'\x7e'):data.extend(os.read(master,4096))
            b=bytearray.fromhex('4b130000'+'00001000'*6+'01000000'*3+'00000000')
            b.extend(crc(b).to_bytes(2,'little'))
            wire=bytearray()
            for v in b:wire.extend(bytes([0x7d,v^0x20]) if v in (0x7d,0x7e) else bytes([v]))
            os.write(master,wire+b'\x7e')
        t=threading.Thread(target=modem,daemon=True);t.start()
        try:r=subprocess.run([str(self.exe),'-t','hdlc','-d',dev,'--timeout','1','hello'],capture_output=True,text=True,timeout=4)
        finally:os.close(slave);os.close(master)
        t.join(1)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('EFS_HELLO version=1',r.stdout)
        self.assertIn('bad_crc=0',r.stderr)
    def test_write_command_is_rejected_before_open(self):
        self.assertTrue(self.exe.exists(),'packaged DIAG reader is missing')
        r=subprocess.run([str(self.exe),'-d','/does-not-exist','write','/nv/x','bad'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertNotIn('/does-not-exist:',r.stderr)

class Integration(unittest.TestCase):
    def test_passive_collector_reads_local_diag_state_only(self):
        text=(ROOT/'devices/oppo_ckb01/files/usr/sbin/ckb01-diag').read_text()
        self.assertIn('capture diag-route-local',text)
        self.assertNotIn('ckb01-diag-efs status',text)

    def test_auto_start_and_installed_paths(self):
        t=(PKG/'Makefile').read_text()
        for name in ['ckb01-diag-efs','ckb01-diag-route-init','diag-route-control.sh','diag_efs_read.c','S97ckb01-diag-route']:
            self.assertIn(name,t)
        for name in ['ckb01-diag-efs','diag-route-control.sh','ckb01-diag-route-init']:
            path=PKG/'files'/name
            self.assertTrue(path.exists(),name)
            subprocess.run(['sh','-n',str(path)],check=True)

class RouteOwner(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.module=self.root/'module';self.module.mkdir()
        self.bin=self.root/'bin';self.bin.mkdir()
        for name,body in [('id','echo 0'),('uname','echo armv7l'),('pidof','exit 1')]:
            p=self.bin/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
        (self.root/'machine').write_text('SDXPRAIRIE\n');(self.root/'transport').write_bytes(b'usb\0')
        src=self.root/'owner.c';src.write_text('#include <unistd.h>\nint main(void){for(;;) pause();}\n')
        self.program=self.root/'test_diag'
        subprocess.run(['cc',str(src),'-o',str(self.program)],check=True)
        control=PKG/'files/diag-route-control.sh';self.assertTrue(control.exists())
        text=control.read_text().replace('root=/tmp/ckb01-diag-route','root='+str(self.module)).replace('program=/usr/bin/test_diag','program='+str(self.program)).replace('/sys/devices/soc0/machine',str(self.root/'machine')).replace('/data/debug_transport.conf',str(self.root/'transport'))
        text=text.replace('9b97b570a7b1787c13e7438712f7911868666daab143e982ef9e1e9c1bd559d3',hashlib.sha256(self.program.read_bytes()).hexdigest())
        self.control=self.root/'control.sh';self.control.write_text(text)
        self.env=dict(os.environ,PATH=str(self.bin)+':'+os.environ['PATH'])
        def cleanup_owner():
            owner=self.module/'owner'
            pid=None
            if owner.exists():
                try:pid=int(owner.read_text().split()[0])
                except (ValueError,IndexError):pass
            self.call('stop')
            if pid:
                try:
                    args=Path(f'/proc/{pid}/cmdline').read_bytes()
                    if args.startswith(str(self.program).encode()+b'\0'):
                        import signal
                        os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
                except FileNotFoundError:pass
        self.addCleanup(cleanup_owner)
    def call(self,*args):return subprocess.run(['sh',str(self.control),*args],env=self.env,text=True,capture_output=True,timeout=9)
    def test_start_is_idempotent_and_stop_does_not_change_persistent_config(self):
        a=self.call('start');self.assertEqual(a.returncode,0,a.stderr)
        first=(self.module/'owner').read_text()
        b=self.call('start');self.assertEqual(b.returncode,0,b.stderr)
        self.assertEqual(first,(self.module/'owner').read_text())
        self.assertEqual(self.call('stop').returncode,0)
        self.assertIn('route_process=stopped',self.call('status').stdout)
        self.assertEqual((self.root/'transport').read_bytes(),b'usb\0')
    def test_proc_cmdline_without_final_nul_is_still_owned(self):
        # The actual OEM test_diag cmdline ends in byte '7', not a NUL.
        tr=self.bin/'tr';tr.write_text('#!/bin/sh\n/usr/bin/tr "$@" | sed "s/ *$//"\n');tr.chmod(0o755)
        r=self.call('start');self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('route_process=running',self.call('status').stdout)
        self.assertEqual(self.call('stop').returncode,0)

    def test_wrong_program_hash_cannot_start(self):
        self.program.write_bytes(b'changed')
        a=self.call('start');self.assertNotEqual(a.returncode,0)
        self.assertFalse((self.module/'owner').exists())
    def test_reused_pid_record_does_not_kill_unrelated_process(self):
        other=subprocess.Popen(['sleep','20'])
        def cleanup_other():
            if other.poll() is None:other.terminate()
            other.wait(timeout=3)
        self.addCleanup(cleanup_other)
        (self.module/'owner').write_text(f'{other.pid} 1\n')
        self.assertEqual(self.call('stop').returncode,0)
        self.assertIsNone(other.poll())

class BootPolicy(unittest.TestCase):
    def test_service_restart_preserves_manual_disable_in_same_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);disabled=p/'disabled';disabled.touch();board=p/'board';board.write_text('oppo,ckb01\n')
            text=(PKG/'files/ckb01-diag-route-init').read_text().replace('/tmp/sysinfo/board_name',str(board)).replace('/tmp/ckb01-diag-efs.disabled',str(disabled)).replace('/tmp/ckb01-diag-efs.stopping',str(p/'stopping'))
            init=p/'init.sh';init.write_text(text)
            command='procd_open_instance() { :; }; procd_close_instance() { :; }; procd_set_param() { :; }; . "$1"; start_service'
            r=subprocess.run(['sh','-c',command,'sh',str(init)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(disabled.exists(),'restart must not override manual disable')

    def test_stop_marks_stopping_before_module_call_and_start_clears_only_stopping(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);stopping=p/'stopping';disabled=p/'disabled';disabled.touch()
            board=p/'board';board.write_text('oppo,ckb01\n')
            fake=p/'ctl';fake.write_text('#!/bin/sh\n[ -e "'+str(stopping)+'" ]\n');fake.chmod(0o755)
            text=(PKG/'files/ckb01-diag-route-init').read_text().replace('/tmp/sysinfo/board_name',str(board)).replace('/tmp/ckb01-diag-efs.disabled',str(disabled)).replace('/tmp/ckb01-diag-efs.stopping',str(stopping)).replace('/usr/sbin/ckb01-diag-efs',str(fake))
            init=p/'init';init.write_text(text)
            cmd='procd_open_instance() { :; }; procd_close_instance() { :; }; procd_set_param() { :; }; . "$1"; stop_service; start_service'
            r=subprocess.run(['sh','-c',cmd,'sh',str(init)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertFalse(stopping.exists());self.assertTrue(disabled.exists())

class HostUpgrade(unittest.TestCase):
    def test_disable_deploys_matching_controller_before_stopping_old_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);b=p/'bin';b.mkdir();(p/'running').write_text('yes');controller=p/'controller';controller.write_text('#!/bin/sh\n')
            fake=b/'ckb01-oem';fake.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
p=Path(os.environ['MODULE_FIXTURE'])
if sys.argv[1]=='push':
 (p/'deployed').touch()
elif sys.argv[1]=='exec' and "'stop'" in sys.argv[2]:
 if not (p/'deployed').exists():sys.exit(66)
 (p/'running').write_text('no')
 print('route_process=stopped')
''');fake.chmod(0o755)
            text=(PKG/'files/ckb01-diag-efs').read_text().replace('. /lib/functions/ckb01-oem.sh','ckb01_oem_guard() { return 0; }')
            for old,new in [('/usr/lib/ckb01-oem/diag-route-control.sh',str(controller)),('/tmp/ckb01-diag-efs.status',str(p/'status')),('/tmp/ckb01-diag-efs.disabled',str(p/'disabled')),('/var/lock',str(p/'locks'))]:text=text.replace(old,new)
            script=p/'host.sh';script.write_text(text)
            env=dict(os.environ,PATH=str(b)+':'+os.environ['PATH'],MODULE_FIXTURE=str(p))
            r=subprocess.run(['sh',str(script),'disable'],env=env,text=True,capture_output=True,timeout=5)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual((p/'running').read_text(),'no','upgrade must not report disabled while old owner runs')

class Shutdown(unittest.TestCase):
    def test_stop_waits_for_inflight_step_then_stops_its_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);b=p/'bin';b.mkdir();controller=p/'controller';controller.write_text('#!/bin/sh\n');(p/'running').write_text('yes')
            fake=b/'ckb01-oem';fake.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
if sys.argv[1]=='exec' and "'stop'" in sys.argv[2]:
 Path(os.environ['RUNNING']).write_text('no')
 print('route_process=stopped')
''');fake.chmod(0o755)
            text=(PKG/'files/ckb01-diag-efs').read_text().replace('. /lib/functions/ckb01-oem.sh','ckb01_oem_guard() { return 0; }')
            for old,new in [('/usr/lib/ckb01-oem/diag-route-control.sh',str(controller)),('/tmp/ckb01-diag-efs.status',str(p/'status')),('/tmp/ckb01-diag-efs.disabled',str(p/'disabled')),('/var/lock',str(p/'locks'))]:text=text.replace(old,new)
            script=p/'host';script.write_text(text);lock=p/'locks/ckb01-diag-efs.lock';lock.mkdir(parents=True)
            owner=subprocess.Popen(['sleep','10']);(lock/'pid').write_text(str(owner.pid))
            def release():
                import time
                time.sleep(.25)
                (lock/'pid').unlink();lock.rmdir()
            t=threading.Thread(target=release);t.start()
            try:
                env=dict(os.environ,PATH=str(b)+':'+os.environ['PATH'],RUNNING=str(p/'running'))
                r=subprocess.run(['sh',str(script),'_stop'],env=env,text=True,capture_output=True,timeout=5)
            finally:t.join();owner.terminate();owner.wait(timeout=3)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual((p/'running').read_text(),'no')
