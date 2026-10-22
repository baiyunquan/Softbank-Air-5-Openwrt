"""Validate the OEM-derived MHI wire configuration in the shipped kernel patch."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

def added_kernel_source():
    outer = (ROOT / 'patches/tree/ckb01/0003-qualcommax-ckb01-sdx55.patch').read_text()
    inner = '\n'.join(line[1:] for line in outer.splitlines()
                      if line.startswith('+') and not line.startswith('+++'))
    return '\n'.join(line[1:] for line in inner.splitlines()
                     if line.startswith('+') and not line.startswith('+++'))

class OEMMhiConfiguration(unittest.TestCase):
    def test_second_startup_syserr_sample_cannot_reset_ckb01(self):
        # Check the hunk guarding the existing direct RESET write, not merely
        # mhi_soc_reset(): a state transition between the two reads is possible.
        outer=(ROOT/'patches/tree/ckb01/0003-qualcommax-ckb01-sdx55.patch').read_text()
        inner='\n'.join(x[1:] for x in outer.splitlines() if x.startswith('+'))
        self.assertRegex(inner,r'(?s)if \(state == MHI_STATE_SYS_ERR\) \{.*?no_auto_recovery.*?startup SYS_ERR.*?goto error_exit;.*?mhi_set_mhi_state\(mhi_cntrl, MHI_STATE_RESET\)')

    def test_required_channels_reference_oem_event_slots(self):
        src = added_kernel_source()
        block = re.search(r'ckb01_sdx55_channels\[\].*?\n\};', src, re.S).group()
        got = {int(c): (name, int(size), int(event)) for c, name, size, event in
               re.findall(r'MHI_CHANNEL_CONFIG_(?:HW_)?(?:UL|DL)\((\d+),\s*"([^"]+)",\s*(\d+),\s*(\d+)\)', block)}
        expected = {4: ('DIAG',64,1),5: ('DIAG',64,3),14: ('QMI',64,1),15: ('QMI',64,2),
                    16: ('QMI1',64,3),17: ('QMI1',64,3),20: ('IPCR',64,2),21: ('IPCR',64,2),
                    46: ('IP_SW0',64,4),47: ('IP_SW0',64,5),100: ('IP_HW0',512,6),101: ('IP_HW0',1024,7)}
        self.assertEqual(got, expected)

    def test_fourteen_slots_keep_shared_msi_and_skip_offload_buffers(self):
        src = added_kernel_source()
        block = re.search(r'ckb01_sdx55_events\[\].*?\n\};', src, re.S)
        self.assertIsNotNone(block, 'dedicated OEM event table is absent')
        # Columns: size, moderation, MSI, channel, burst, hardware, offload.
        rows = [tuple(x.strip() for x in row.split(',')) for row in
                re.findall(r'CKB01_EVENT\(([^)]+)\)', block.group())]
        expected = [
            ('32','1','1','U32_MAX','DISABLE','false','false'),
            ('256','1','2','U32_MAX','DISABLE','false','false'),
            ('256','1','3','U32_MAX','DISABLE','false','false'),
            ('256','1','4','U32_MAX','DISABLE','false','false'),
            ('1024','5','5','46','DISABLE','false','false'),
            ('1024','5','6','47','DISABLE','false','false'),
            ('1024','5','5','100','ENABLE','true','false'),
            ('2048','5','6','101','ENABLE','true','false'),
            ('0','0','0','102','ENABLE','true','true'),
            ('1024','5','7','103','DISABLE','true','false'),
            ('1024','1','8','105','DISABLE','true','false'),
            ('1024','0','9','106','DISABLE','true','false'),
            ('0','0','0','107','ENABLE','true','true'),
            ('0','0','0','108','ENABLE','true','true')]
        self.assertEqual(rows, expected)

if __name__ == '__main__':
    unittest.main()
