#!/usr/bin/env python3
"""Inspect actual compiled payloads; caller reports failures as advisory warnings."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fit', ROOT / 'scripts/ckb01-fit.py')
fit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fit)
FILES = {
 'usr/sbin/ckb01-edl': ROOT / 'packages/ckb01-edl/files/ckb01-edl',
 'etc/ckb01-maintenance': ROOT / 'packages/ckb01-edl/files/maintenance',
 'etc/modprobe.d/ckb01-edl.conf': ROOT / 'packages/ckb01-edl/files/ckb01-edl.conf',
 'lib/firmware/qcom/ckb01/prog_firehose_sdx55.mbn': ROOT / 'packages/ckb01-edl/firmware/prog_firehose_sdx55.mbn',
 'usr/share/ckb01-edl/provenance.json': ROOT / 'packages/ckb01-edl/firmware/provenance.json',
}
BINARY = 'usr/libexec/ckb01-firehose-read'

def check(entries, label):
 for name, source in FILES.items():
  if entries.get(name) != source.read_bytes():
   raise ValueError(f'{label}: absent or changed {name}')
 if not entries.get(BINARY, b'').startswith(b'\x7fELF'):
  raise ValueError(f'{label}: missing compiled {BINARY}')
 for library in ('libxml2.so', 'libjson-c.so'):
  if not any(Path(p).name.startswith(library) for p in entries):
   raise ValueError(f'{label}: missing {library}')
 print(f'{label}: maintenance files, binary and dependencies present')

def main():
 ap = argparse.ArgumentParser()
 ap.add_argument('--openwrt', type=Path, required=True)
 ap.add_argument('--artifacts', type=Path, required=True)
 a = ap.parse_args()
 errors = []
 def run(label, fn):
  try: fn()
  except Exception as e: errors.append(f'{label}: {e}')
 def ram():
  paths = list(a.openwrt.glob('build_dir/**/linux-*/usr/initramfs_inc_data'))
  if len(paths) != 1: raise ValueError(f'found {len(paths)} embedded archives')
  data = paths[0].read_bytes()
  if data.startswith(b'\x28\xb5\x2f\xfd'): data = subprocess.check_output(['zstd','-qdc',str(paths[0])])
  elif data.startswith(b'\x1f\x8b'): data = gzip.decompress(data)
  check(fit.archive_entries(data), 'initramfs')
 def rootfs():
  paths = list(a.artifacts.glob('*rootfs.tar.gz'))
  if len(paths) != 1: raise ValueError(f'found {len(paths)} rootfs archives')
  with tarfile.open(paths[0]) as tf:
   entries = {m.name.removeprefix('./').lstrip('/'): tf.extractfile(m).read() for m in tf if m.isfile()}
  check(entries, 'rootfs tar')
 def disk():
  image = a.artifacts / 'air5-ckb01-usb.img'
  table = json.loads(subprocess.check_output(['sfdisk','--json',str(image)]))['partitiontable']
  part = table['partitions'][1]
  with tempfile.TemporaryDirectory() as td:
   fs = Path(td)/'root.ext4'
   with image.open('rb') as src, fs.open('wb') as dst:
    src.seek(part['start'] * table['sectorsize'])
    left = part['size'] * table['sectorsize']
    while left:
     b=src.read(min(left,1024*1024))
     if not b: raise ValueError('short ext4 partition')
     dst.write(b);left-=len(b)
   for name in (*FILES, BINARY):
    data = subprocess.check_output(['debugfs','-R',f'cat /{name}',str(fs)],stderr=subprocess.DEVNULL)
    expected = FILES[name].read_bytes() if name in FILES else None
    if expected is not None and data != expected: raise ValueError(f'ext4 changed or absent {name}')
    if name == BINARY and not data.startswith(b'\x7fELF'): raise ValueError('ext4 reader absent')
   print('ext4: installed maintenance payloads verified')
 run('initramfs', ram);run('rootfs', rootfs);run('USB ext4', disk)
 record={'hardware_acceptance':'pending','checks_ok':not errors,'errors':errors,'programmer_sha256':hashlib.sha256(FILES['lib/firmware/qcom/ckb01/prog_firehose_sdx55.mbn'].read_bytes()).hexdigest()}
 (a.artifacts/'maintenance-validation.json').write_text(json.dumps(record,indent=2)+'\n')
 for error in errors: print(error)
 return bool(errors)
if __name__ == '__main__': raise SystemExit(main())
