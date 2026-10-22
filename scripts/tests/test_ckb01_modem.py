"""Offline tests of the actual CKB01 modem code and package integration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages/ckb01-modem/src'

class ModemCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ckb01-modem-test-')
        cls.bin = Path(cls.tmp.name) / 'ckb01-modem'
        if (SRC / 'main.c').exists():
            flags = subprocess.check_output(['pkg-config','--cflags','--libs','qmi-glib','qrtr-glib','json-c'], text=True).split()
            result = subprocess.run(['cc','-std=c11','-D_GNU_SOURCE','-Wall','-Wextra','-Werror','-O1',
                *map(str, sorted(SRC.glob('*.c'))),'-o',str(cls.bin),*flags], text=True,capture_output=True)
            if result.returncode: raise AssertionError(result.stderr)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def run_cli(self,*args):
        self.assertTrue(self.bin.exists(), 'modem implementation is missing')
        return subprocess.run([str(self.bin),*args],text=True,capture_output=True)
    def decode(self,service,body):
        r=self.run_cli('decode',str(service),body)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout)
    def test_dms_capabilities_match_actual_oem_response(self):
        d=self.decode(2,'02010045003e0002040000000000010800000000000000000010080081000000000300001108000000000000000000120a0004000100080029002a00130600020003004d00')
        self.assertTrue(d['ok']); self.assertEqual(d['nr_bands'],[3,77]); self.assertEqual(d['lte_bands'],[1,8,41,42])
    def test_unsupported_query_is_a_protocol_error(self):
        d=self.decode(2,'0201004300070002040001005e00')
        self.assertFalse(d['ok']); self.assertEqual(d['protocol_error'],94)
    def test_truncated_message_is_rejected(self):
        r=self.run_cli('decode','2','0201004500100002040000000000')
        self.assertNotEqual(r.returncode,0)
    def test_truncated_tlv_is_rejected(self):
        r=self.run_cli('decode','2','0201004500040013080000')
        self.assertNotEqual(r.returncode,0)
    def test_pdc_response_is_not_an_activation_indication(self):
        d=self.decode(36,'0201002200070002040000000000')
        self.assertTrue(d['ok']);self.assertEqual(d['kind'],'response');self.assertNotIn('active_id',d)
    def test_pdc_selected_indication_decodes_active_id(self):
        d=self.decode(36,'04010022001d00010200000011150014bff8740b8ba4a579e5c21499b9e4f88d0773cd6f')
        self.assertEqual(d['kind'],'indication');self.assertTrue(d['ok']);self.assertEqual(d['active_id'],'bff8740b8ba4a579e5c21499b9e4f88d0773cd6f')
    def test_bad_command_does_not_touch_hardware(self):
        r=self.run_cli('profile','unknown')
        self.assertNotEqual(r.returncode,0)

class ModemIntegration(unittest.TestCase):
    def test_ckb01_kernel_patch_exists_and_is_board_scoped(self):
        p=ROOT/'patches/tree/ckb01/0003-qualcommax-ckb01-sdx55.patch'
        self.assertTrue(p.exists(), 'CKB01 MHI patch is missing')
        text=p.read_text()
        for part in ['oppo,ckb01','ckb01-sdx55','0x010c','"QMI1"','"IPCR"','"IP_SW0"','"IP_HW0"']:
            self.assertIn(part,text)
        self.assertIn('60000',text)
    def test_package_carries_qrtr_pdc_and_data_dependencies(self):
        p=ROOT/'packages/ckb01-modem/Makefile'
        self.assertTrue(p.exists(),'modem package is missing')
        t=p.read_text()
        for dependency in ['libqmi','libqrtr-glib','libjson-c','kmod-rmnet']: self.assertIn(dependency,t)
    def test_netifd_has_dedicated_protocol_and_no_usb_raw_ip_dependency(self):
        p=ROOT/'packages/ckb01-modem/files/ckb01_qmi.sh'
        self.assertTrue(p.exists(),'netifd protocol is missing')
        t=p.read_text();self.assertIn('ckb01_qmi',t);self.assertNotIn('/qmi/raw_ip',t)
        subprocess.run(['sh','-n',str(p)],check=True)

if __name__=='__main__': unittest.main()

class ModemRegression(unittest.TestCase):
    def test_radio_restores_extended_lte_with_correct_set_tlv(self):
        # libqmi NAS GET uses 0x23, SET uses 0x24 (not usage-preference 0x21).
        t=(SRC/'radio.c').read_text()
        self.assertIn('0x11, 0x12, 0x15, 0x24, 0x2f, 0x30',t)
    def test_pdc_matching_checks_cid_and_token(self):
        self.assertIn('pdc_matches', (SRC/'transport.c').read_text())
    def test_session_watches_both_ip_families(self):
        self.assertIn('connected(&v6)', (SRC/'session.c').read_text())
    def test_modem_shutdown_uses_numeric_netifd_signal(self):
        self.assertIn('proto_kill_command "$1" 15', (ROOT/'packages/ckb01-modem/files/ckb01_qmi.sh').read_text())
        self.assertIn('wait "$child"', (ROOT/'packages/ckb01-modem/files/ckb01-session').read_text())
    def test_backup_requires_complete_baseline(self):
        self.assertIn('baseline_complete', (SRC/'profile.c').read_text())

class ModemFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ckb01-fixture-')
        cls.exe=Path(cls.tmp.name)/'harness'
        flags=subprocess.check_output(['pkg-config','--cflags','--libs','qmi-glib','qrtr-glib','json-c'],text=True).split()
        subprocess.run(['cc','-std=c11','-D_GNU_SOURCE','-Wall','-Wextra','-Werror','-I'+str(SRC),str(ROOT/'scripts/tests/fixtures/ckb01_modem_harness.c'),*[str(p) for p in SRC.glob('*.c') if p.name!='main.c'],'-Wl,--wrap=request','-Wl,--wrap=execute','-o',str(cls.exe),*flags],check=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_pdc_wrong_token_cid_and_message_rejected(self):
        subprocess.run([str(self.exe),'pdc'],check=True)
    def test_transport_accepts_revision_even_when_sim_is_locked(self):
        r=subprocess.run([str(self.exe),'transport'],text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        d=json.loads(r.stdout);self.assertTrue(d['ok']);self.assertTrue(d['revision']['ok'])
        self.assertFalse(d['sim']['ok']);self.assertEqual(d['revision']['raw_hex'],'revision-response')
    def test_data_format_only_accepts_oem_raw_ip_endpoint(self):
        for mode in ['raw','qmap','wrong_endpoint']:
            r=subprocess.run([str(self.exe),'format',mode],text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def fixture(self,root,board='oppo,ckb01',subsystem='0x010c',data=True):
        base=root/'firmware/devicetree/base';base.mkdir(parents=True)
        (base/'compatible').write_bytes(board.encode()+b'\0qcom,ipq8074\0')
        pci=root/'bus/pci/devices/0000:01:00.0';pci.mkdir(parents=True)
        for name,value in dict(vendor='0x17cb',device='0x0306',subsystem_vendor='0x17cb',subsystem_device=subsystem).items():(pci/name).write_text(value+'\n')
        for parent,name,ch in [('wwan','wwan7qmi2','QMI'),('wwan','wwan7qmi3','QMI1'),('net','mhi_swip7','IP_SW0')]+([('net','mhi_hwip5','IP_HW0')] if data else []):
            target=pci/('mhi0_'+ch)/name;target.mkdir(parents=True)
            cls=root/'class'/parent;cls.mkdir(parents=True,exist_ok=True);(cls/name).symlink_to(target)
    def discover(self,root):return json.loads(subprocess.check_output([str(self.exe),'discover',str(root)],text=True))
    def test_roles_follow_pci_and_channel_not_interface_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);d=self.discover(root)
            self.assertTrue(d['ok']);self.assertEqual(d['control'],'/dev/wwan7qmi2');self.assertEqual(d['data'],'mhi_hwip5');self.assertEqual(d['management'],'mhi_swip7')
    def test_wrong_board_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root,board='tplink,deco-x80-5g');self.assertFalse(self.discover(root)['ok'])
    def test_wrong_subsystem_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root,subsystem='0x010b');self.assertFalse(self.discover(root)['ok'])
    def test_software_ready_before_delayed_data_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root,data=False);d=self.discover(root)
            self.assertTrue(d['ok']);self.assertFalse(d['data_present'])
            p=root/'bus/pci/devices/0000:01:00.0/mhi0_IP_HW0/mhi_hwip8';p.mkdir(parents=True);(root/'class/net/mhi_hwip8').symlink_to(p)
            self.assertTrue(self.discover(root)['ok']);self.assertTrue(self.discover(root)['data_present'])
    def test_wwan_qmi0_without_channel_prefix_matches_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/'firmware/devicetree/base';base.mkdir(parents=True)
            (base/'compatible').write_bytes(b'oppo,ckb01\0qcom,ipq8074\0')
            pci=root/'bus/pci/devices/0000:01:00.0';pci.mkdir(parents=True)
            for name,value in dict(vendor='0x17cb',device='0x0306',subsystem_vendor='0x17cb',subsystem_device='0x010c').items():(pci/name).write_text(value+'\n')
            wwan_target=pci/'mhi0/wwan/wwan0/wwan0qmi0';wwan_target.mkdir(parents=True)
            cls_wwan=root/'class/wwan';cls_wwan.mkdir(parents=True,exist_ok=True);(cls_wwan/'wwan0qmi0').symlink_to(wwan_target)
            for name,ch in [('mhi_swip0','IP_SW0'),('mhi_hwip0','IP_HW0')]:
                target=pci/('mhi0_'+ch)/name;target.mkdir(parents=True)
                cls_net=root/'class/net';cls_net.mkdir(parents=True,exist_ok=True);(cls_net/name).symlink_to(target)
            d=self.discover(root)
            self.assertTrue(d['ok'])
            self.assertEqual(d['control'],'/dev/wwan0qmi0')
            self.assertEqual(d['management'],'mhi_swip0')
            self.assertEqual(d['data'],'mhi_hwip0')


class NetifdRuntime(unittest.TestCase):
    def test_addresses_survive_proto_json_initialization(self):
        source=(ROOT/'packages/ckb01-modem/files/ckb01-update').read_text()
        stub=r'''
scope=
json_load() { scope=root; }
json_init() { scope=empty; }
json_select() { [ "$scope" != empty ] || return 1; case "$1" in ..) scope=root;; *) scope="$1";; esac; }
json_get_vars() {
 for key in "$@"; do
  value=
  case "$scope:$key" in
   root:ifname) value=mhi_hwip7;; root:up) value=1;;
   ipv4:address) value=10.1.2.3;; ipv4:gateway) value=10.1.2.1;;
   ipv4:netmask) value=255.255.255.0;; ipv4:dns1) value=8.8.8.8;;
   ipv6:address6) value=2001:db8::2;; ipv6:gateway6) value=2001:db8::1;;
   ipv6:prefix6) value=64;; ipv6:dns6_1) value=2001:4860:4860::8888;;
  esac
  eval "$key=\$value"
 done
}
proto_init_update() { json_init; echo "link $*"; }
proto_set_keep() { :; }
proto_add_ipv4_address() { echo "v4 $*"; }
proto_add_ipv6_address() { echo "v6 $*"; }
proto_add_ipv4_route() { echo "route4 $*"; }
proto_add_ipv6_route() { echo "route6 $*"; }
proto_add_dns_server() { echo "dns $*"; }
proto_send_update() { echo "publish $*"; }
uci() { echo 10; }
ip() { :; }
'''
        source=source.replace('. /lib/functions.sh','').replace('. /lib/netifd/netifd-proto.sh','')
        r=subprocess.run(['sh','-c',stub+source,'test','cellular','{}'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('v4 10.1.2.3 255.255.255.0',r.stdout)
        self.assertIn('v6 2001:db8::2 64',r.stdout)
        self.assertIn('dns 8.8.8.8',r.stdout)
        self.assertIn('route4 0.0.0.0 0 10.1.2.1',r.stdout)

class RecoveryTools(unittest.TestCase):
    def test_n78_restore_propagates_failure_and_keeps_snapshot(self):
        t=(ROOT/'packages/ckb01-modem/files/ckb01-n78-test').read_text()
        self.assertIn('if ckb01-modem radio auto; then',t)
        self.assertIn('exit 1',t)
        c=(SRC/'radio.c').read_text()
        self.assertIn('if (ok)\n      unlink(path);',c)
    def test_transport_can_cancel_and_bounds_cleanup(self):
        t=(SRC/'transport.c').read_text()
        self.assertIn('g_cancellable_cancel',t)
        self.assertIn('m->shutting_down ? 2 : (m->timeout_s',t)
        self.assertIn('30000000', (SRC/'main.c').read_text())
    def test_restore_checks_original_manual_plmn(self):
        t=(SRC/'radio.c').read_text()
        self.assertIn('addhex(q, 0x1a, plmn + 8)',t)
        self.assertIn('strcmp(plmn, jstr(now, "1b"))',t)
