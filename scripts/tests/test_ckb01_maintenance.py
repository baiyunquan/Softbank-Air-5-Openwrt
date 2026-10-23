"""Maintenance image selection and advisory CI integration."""
from pathlib import Path
import hashlib
import importlib.util
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[2]

class Maintenance(unittest.TestCase):
 def test_firmware_provenance(self):
  data = (ROOT/'packages/ckb01-edl/firmware/prog_firehose_sdx55.mbn').read_bytes()
  self.assertEqual(len(data),275328)
  self.assertEqual(hashlib.sha256(data).hexdigest(),'d46bc860c73c0a09bbb72b70da8ea0b1a33000dca4189fba7bfb09deedac7070')
 def test_shell_syntax(self):
  for file in ['packages/ckb01-edl/files/ckb01-edl','packages/ckb01-modem/files/ckb01-modem-wait','packages/ckb01-modem/files/ckb01_qmi.sh','packages/ckb01-oem-tools/files/ckb01-diag-route-init']:
   subprocess.run(['sh','-n',str(ROOT/file)],check=True)
 def test_maintenance_is_opt_in(self):
  self.assertNotIn('CONFIG_PACKAGE_ckb01-edl=y',(ROOT/'devices/oppo_ckb01/config').read_text())
  self.assertIn('CONFIG_PACKAGE_ckb01-edl=y',(ROOT/'devices/oppo_ckb01/maintenance.config').read_text())
  self.assertIn('ckb01_edl_maintenance=1',(ROOT/'packages/ckb01-edl/files/ckb01-edl.modules').read_text())
 def test_no_implicit_backup_entry(self):
  script=(ROOT/'packages/ckb01-edl/files/ckb01-edl').read_text().split(' backup-efs)')[1]
  self.assertNotIn('echo arm',script)
  self.assertNotIn('trigger_edl',script)
 def test_diag_fd_remains_open_through_attach(self):
  text=(ROOT/"packages/ckb01-edl/files/ckb01-edl").read_text()
  self.assertLess(text.index('exec 3<>'), text.index('echo arm'))
  self.assertLess(text.index('echo attach'), text.index('exec 3>&-'))
 def test_payload_checker_accepts_actual_files_rejects_missing(self):
  spec=importlib.util.spec_from_file_location('maintenance',ROOT/'scripts/ckb01-maintenance-check.py')
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  entries={p:src.read_bytes() for p,src in m.FILES.items()}
  entries[m.BINARY]=b'\x7fELFbinary';entries['usr/lib/libxml2.so.16']=b'x';entries['usr/lib/libjson-c.so.5']=b'x'
  m.check(entries,'fixture')
  del entries['etc/ckb01-maintenance']
  with self.assertRaises(ValueError): m.check(entries,'fixture')
 def test_workflow_separate_trigger_and_raw_upload(self):
  child=(ROOT/'.github/workflows/build-ckb01-maintenance.yml').read_text()
  self.assertIn('branches: [ckb01-pcie-edl]',child)
  self.assertIn('maintenance: true',child)
  main=(ROOT/'.github/workflows/build-ckb01.yml').read_text()
  self.assertIn('workflow_call:',main)
  self.assertIn('if: always()',main)
  self.assertIn('--openwrt openwrt --artifacts artifacts',main)
