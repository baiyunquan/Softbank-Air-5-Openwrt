"""Run the real startup supervisor with external hardware commands simulated."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'packages/ckb01-modem/files/ckb01-modem-wait'
FAKE = r'''#!/usr/bin/env python3
import fcntl,json,os,sys,subprocess
from pathlib import Path
name=Path(sys.argv[0]).name; args=sys.argv[1:]; root=Path(os.environ['FAKE_ROOT'])
with (root/'calls').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps([name,*args])+'\n')
case=os.environ.get('CASE','success')
if name=='cut':
 with (root/'clock').open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX); f.seek(0); n=int(f.read() or '0')+(1 if case=='success' else 5)
  f.seek(0); f.truncate(); f.write(str(n))
 print(n)
elif name=='jsonfilter':
 text=Path(args[args.index('-i')+1]).read_text() if '-i' in args else sys.stdin.read()
 try:
  value=json.loads(text)
  for part in args[args.index('-e')+1].replace('@.','').split('.'):value=value[part]
  print(str(value).lower() if isinstance(value,bool) else value)
 except (ValueError,KeyError):sys.exit(1)
elif name=='ckb01-modem':
 if args==['discover']:
  print(json.dumps({'ok':True,'control':'/dev/wwan7qmi2','management':'mhi_swip7','data':'mhi_hwip5','data_present':True}))
 else:
  good=not (case=='qmi_fail' and '--device' not in args)
  print(json.dumps({'ok':good,'revision':{'ok':good},'sim':{'ok':False,'error':'locked'}}))
  sys.exit(0 if good else 1)
elif name=='ping':sys.exit(1 if case=='ping_fail' else 0)
elif name=='ckb01-oem':
 print('4.14.206');sys.exit(1 if case=='rpc_fail' else 0)
elif name=='timeout':
 if args[0]=='-k':args=args[2:]
 os.execvp(args[1],args[1:])
elif name=='sleep':pass
elif name=='ip' and case=='ip_slow':
 child=subprocess.Popen(['/bin/sleep','10'])
 (root/'slow-child.pid').write_text(str(child.pid)); child.wait()
'''

class Startup(unittest.TestCase):
    def test_netifd_requires_three_transport_results_before_start(self):
        with tempfile.TemporaryDirectory(prefix='ckb01-gate-') as tmp:
            root=Path(tmp); bindir=root/'bin'; bindir.mkdir()
            fake=bindir/'fake'; fake.write_text(FAKE); fake.chmod(0o755)
            (bindir/'jsonfilter').symlink_to(fake)
            env=dict(os.environ, PATH=str(bindir)+':'+os.environ['PATH'], FAKE_ROOT=tmp,
                     CKB01_MODEM_STATE_DIR=tmp)
            shell='''
INCLUDE_ONLY=1
json_get_vars() { apn=3gnet; endpoint=; metric=10; }
proto_notify_error() { echo "error $*"; }
proto_block_restart() { echo block; }
proto_run_command() { echo "run $*"; }
logger() { :; }
. "$1"
proto_ckb01_qmi_setup cellular
'''
            script=ROOT/'packages/ckb01-modem/files/ckb01_qmi.sh'
            r=subprocess.run(['sh','-c',shell,'test',str(script)],env=env,text=True,capture_output=True)
            self.assertNotEqual(r.returncode,0);self.assertIn('TRANSPORT_NOT_READY',r.stdout)
            self.assertNotIn('run ',r.stdout)
            (root/'ckb01-modem-ready.json').write_text('{"ok":true,"management":true,"qmi":true,"qrtr":true,"endpoint_type":3,"endpoint":4}')
            r=subprocess.run(['sh','-c',shell,'test',str(script)],env=env,text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn('run cellular /usr/sbin/ckb01-session cellular 3gnet 4',r.stdout)

    def run_startup(self, case):
        tmp = tempfile.TemporaryDirectory(prefix='ckb01-startup-')
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name); bindir = root/'bin'; bindir.mkdir()
        fake = bindir/'fake'; fake.write_text(FAKE); fake.chmod(0o755)
        for command in ['cut','jsonfilter','ckb01-modem','ping','ckb01-oem','timeout','sleep','logger','ip','ifup']:
            (bindir/command).symlink_to(fake)
        env = dict(os.environ, PATH=str(bindir)+':'+os.environ['PATH'], FAKE_ROOT=str(root),
                   CASE=case, CKB01_MODEM_STATE_DIR=str(root/'state'), CKB01_MODEM_TIMEOUT='/usr/bin/timeout')
        begin=time.monotonic()
        result = subprocess.run(['sh',str(SCRIPT)],env=env,text=True,capture_output=True,timeout=25)
        result.elapsed=time.monotonic()-begin
        calls=[json.loads(x) for x in (root/'calls').read_text().splitlines()]
        return root,env,result,calls

    def test_management_failure_does_not_suppress_qmi_or_qrtr(self):
        for case in ['ping_fail','rpc_fail']:
            with self.subTest(case=case):
                root,env,r,calls=self.run_startup(case)
                probes=[x for x in calls if x[0]=='ckb01-modem' and 'probe' in x]
                self.assertTrue(any('--transport-only' in x and '--device' not in x for x in probes))
                self.assertTrue(any('qrtr' in x for x in probes))
                self.assertFalse(any(x[0]=='ifup' for x in calls))
                self.assertFalse((root/'state/ckb01-modem-ready.json').exists())

    def test_locked_sim_does_not_hide_working_transport_and_start_is_idempotent(self):
        root,env,r,calls=self.run_startup('success')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual([x for x in calls if x[0]=='ifup'],[['ifup','cellular']])
        ready=root/'state/ckb01-modem-ready.json'
        self.assertTrue(ready.exists(),'transport success did not publish the data gate')
        self.assertTrue(json.loads(ready.read_text())['ok'])
        again=subprocess.run(['sh',str(SCRIPT)],env=env,capture_output=True,timeout=12)
        self.assertEqual(again.returncode,0,again.stderr)
        calls=[json.loads(x) for x in (root/'calls').read_text().splitlines()]
        self.assertEqual(len([x for x in calls if x[0]=='ifup']),1)

    def test_qmi_failure_keeps_data_down_and_never_resets(self):
        root,env,r,calls=self.run_startup('qmi_fail')
        self.assertNotEqual(r.returncode,0)
        self.assertFalse(any(x[0]=='ifup' for x in calls))
        self.assertFalse(any('reset' in arg or 'rescan' in arg for x in calls if x[0]!='logger' for arg in x))

    def test_slow_management_open_cannot_escape_deadline_or_leave_descendants(self):
        root,env,r,calls=self.run_startup('ip_slow')
        self.assertLess(r.elapsed,4,'management ndo_open escaped the accelerated deadline')
        self.assertNotEqual(r.returncode,0)
        self.assertFalse((root/'state/ckb01-modem-ready.json').exists())
        pid=int((root/'slow-child.pid').read_text())
        stat=Path(f'/proc/{pid}/stat')
        self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z', 'probe descendant is still running')
