"""Guard contracts for the separately selected PCIe programmer transport.

The optional CKB01_KERNEL_BASE fixture is a Linux 6.18.55 source tree after the
pinned OpenWrt patches and CKB01 patches 950/951. It enables a real zero-fuzz
application check; compilation is performed separately against that result.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'patches/tree/ckb01/0007-qualcommax-ckb01-pcie-edl.patch'


def inner_patch():
    return ''.join(line[1:] + '\n' for line in PATCH.read_text().splitlines()[3:])


def added():
    return '\n'.join(line[1:] for line in inner_patch().splitlines()
                     if line.startswith('+') and not line.startswith('+++'))


class MaintenanceKernel(unittest.TestCase):
    def test_nested_patch_is_well_formed(self):
        raw = PATCH.read_text()
        count = int(re.search(r'@@ -0,0 \+1,(\d+) @@', raw).group(1))
        self.assertEqual(count, len(raw.splitlines()) - 3)
        self.assertNotIn('TODO', added())

    def test_opt_in_and_exact_identity_remain_separate(self):
        source = added()
        self.assertIn('static bool ckb01_edl_maintenance;', source)
        self.assertIn('module_param(ckb01_edl_maintenance, bool, 0444)', source)
        self.assertIn('mhi_cntrl->ckb01_edl_maintenance = ckb01_edl_maintenance', source)
        self.assertIn('mhi_cntrl->edl_trigger = mhi_pci_ckb01_edl_trigger', source)
        # Existing exact board and subsystem selection is outside the new hunk.
        normal = (ROOT / 'patches/tree/ckb01/0003-qualcommax-ckb01-sdx55.patch').read_text()
        for identity in ('oppo,ckb01', 'pdev->vendor == 0x17cb',
                         'pdev->device == 0x0306', 'pdev->subsystem_device == 0x010c'):
            self.assertIn(identity, normal)

    def test_separate_firehose_layout(self):
        source = added()
        for value in ('MHI_CHANNEL_CONFIG_UL_FP(34, "FIREHOSE", 32, 0)',
                      'MHI_CHANNEL_CONFIG_DL_FP(35, "FIREHOSE", 32, 0)',
                      'MHI_EVENT_CONFIG_CTRL(0, 64)',
                      'cntrl->iova_stop = DMA_BIT_MASK(32)',
                      'qcom/ckb01/prog_firehose_sdx55.mbn'):
            self.assertIn(value, source)
        self.assertNotIn('CKB01_EVENT(', source)

    def test_status_is_cached_and_privileged_commands_are_serialized(self):
        source = added()
        show = source.split('static ssize_t ckb01_edl_show', 1)[1].split('static ssize_t ckb01_edl_store')[0]
        self.assertNotIn('readl(', show)
        self.assertNotIn('ckb01_edl_sample(', show)
        self.assertIn('"WAIT_USER", "ARMED", "FP", "FAILED"', show)
        self.assertIn('state=%s ee=%s error=%d triggered=%u attaching=%u', show)
        for value in ('capable(CAP_SYS_ADMIN)', 'mutex_trylock(&mhi_pdev->edl_lock)',
                      'sysfs_streq(buf, "arm")', 'sysfs_streq(buf, "attach")',
                      'sysfs_streq(buf, "cancel")'):
            self.assertIn(value, source)

    def test_arm_expiry_and_attach_share_one_deadline(self):
        source = added()
        self.assertIn('CKB01_EDL_ATTACH_MS 120000', source)
        self.assertEqual(source.count('edl_deadline = jiffies +'), 1)
        self.assertIn('timer_setup(&mhi_pdev->edl_arm_timer, ckb01_edl_arm_expired, 0)', source)
        self.assertIn('cmpxchg(&mhi_pdev->edl_state, CKB01_EDL_ARMED', source)
        self.assertIn('"EDL arm expired"', source)
        self.assertIn('time_before(jiffies, mhi_pdev->edl_deadline)', source)

    def test_attach_confirms_endpoint_before_retiring_host(self):
        source = added().split('static int ckb01_edl_attach', 1)[1]
        order = ['if (ee == MHI_EE_EDL || ee == MHI_EE_FP)',
                 'ckb01_edl_freeze(mhi_pdev)', 'cntrl->ckb01_reset_confirmed = true',
                 'mhi_ckb01_retire_reset_controller(cntrl)', 'memset(cntrl, 0, sizeof(*cntrl))',
                 'mhi_register_controller(cntrl, &ckb01_firehose_config)']
        positions = [source.index(item) for item in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('nr_irqs < 2', source)

    def test_retirement_frees_irq_actions_before_killing_tasklets(self):
        source = added().split('static void mhi_ckb01_retire_host', 1)[1].split('EXPORT_SYMBOL_GPL(mhi_ckb01_remove_controller);', 1)[0]
        order = ['pm_state = MHI_PM_LD_ERR_FATAL_DETECT',
                 'synchronize_irq(', 'mhi_deinit_free_irq(', 'tasklet_kill(',
                 'device_for_each_child(', 'mhi_unregister_controller(']
        positions = [source.index(item) for item in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('irq[j] == mhi_cntrl->irq[i]', source)
        self.assertIn('ckb01_reset_confirmed && mhi_cntrl->mhi_ctxt', source)
        for forbidden in ('mhi_power_down(', 'mhi_soc_reset(', 'pci_try_reset_function(', 'MHI_STATE_RESET'):
            self.assertNotIn(forbidden, source)

    def test_failed_close_retains_dma_and_skips_channel_reset(self):
        source = added()
        self.assertIn('if (!mhi_cntrl->ckb01_reset_confirmed)', source)
        self.assertIn('return; /* Endpoint may still DMA: retain channel contexts and buffers. */', source)
        self.assertIn('Retain potentially DMA-visible staging on failure', source)
        self.assertIn('mhi_cntrl->fbc_image = image;', source)

    def test_close_between_arm_and_attach_gates_before_channel_teardown(self):
        source = added()
        self.assertIn('WRITE_ONCE(cntrl->ckb01_edl_armed, true)', source)
        guard = source.split('Userspace may fail between arm and attach', 1)[1]
        order = ['READ_ONCE(mhi_cntrl->ckb01_edl_armed)',
                 'pm_state = MHI_PM_LD_ERR_FATAL_DETECT',
                 'mhi_diag_abort(mhi_cntrl)',
                 'return; /* Endpoint may still DMA']
        positions = [guard.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))

    def test_firmware_and_fp_startup_are_locally_guarded(self):
        source = added()
        for value in ('!mhi_cntrl->ckb01_edl_active || mhi_cntrl->ee != MHI_EE_EDL',
                      'request_firmware_direct(&firmware, fw_name, dev)',
                      'mhi_cntrl->ckb01_edl_active && current_ee == MHI_EE_FP',
                      'current_ee != MHI_EE_EDL && current_ee != MHI_EE_FP',
                      'waiting for explicit arm/attach'):
            self.assertIn(value, source)
        self.assertNotIn('#define MHI_POWER_UP_CAPABLE', source)

    def test_bhi_completion_requires_success_not_only_a_wakeup(self):
        source = added()
        helper = re.search(r'static int mhi_ckb01_bhi_result[^}]+}', source).group()
        harness = """#include <stdbool.h>
#include <errno.h>
typedef unsigned int u32;
#define BHI_STATUS_SUCCESS 2
""" + helper + """
int main(void) {
    /* Successful DMA alone releases staging. */
    if (mhi_ckb01_bhi_result(1, 0, 2, false) != 0) return 1;
    /* PCI read failure with unchanged or stale-success status must fail. */
    if (mhi_ckb01_bhi_result(1, -ENODEV, 0, false) != -ENODEV) return 2;
    if (mhi_ckb01_bhi_result(1, -ENODEV, 2, false) != -ENODEV) return 3;
    if (mhi_ckb01_bhi_result(0, 0, 0, false) != -ETIMEDOUT) return 4;
    if (mhi_ckb01_bhi_result(1, 0, 3, false) != -EIO) return 5;
    if (mhi_ckb01_bhi_result(1, 0, 2, true) != -EIO) return 6;
    if (mhi_ckb01_bhi_result(1, 0, 1, false) != -EIO) return 7;
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            cfile = Path(tmp) / 'bhi.c'
            binary = Path(tmp) / 'bhi'
            cfile.write_text(harness)
            result = subprocess.run(['cc', '-Wall', '-Werror', str(cfile), '-o', str(binary)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)]).returncode, 0)
        self.assertIn('(read_error = mhi_read_reg_field', source)
        self.assertIn('return mhi_ckb01_bhi_result(ret, read_error, tx_status,', source)

    def test_fp_success_waits_for_state_handler_and_driver_binding(self):
        source = added()
        self.assertIn('WRITE_ONCE(mhi_cntrl->ckb01_fp_ready, true)', source)
        self.assertIn('READ_ONCE(cntrl->ckb01_fp_ready)', source)
        self.assertIn('device_is_bound(&cntrl->mhi_chan[34].mhi_dev->dev)', source)

    def test_new_pci_dependencies_are_exported_by_core(self):
        source = added()
        for symbol in ('mhi_read_reg', 'mhi_write_reg', 'mhi_diag_stop',
                       'mhi_queue_state_transition'):
            self.assertIn('EXPORT_SYMBOL_GPL(' + symbol + ');', source)

    def test_compiled_pci_mhi_imports_have_core_exports(self):
        build = os.environ.get('CKB01_KERNEL_BUILD')
        if not build:
            self.skipTest('CKB01_KERNEL_BUILD not set; compiled module boundary check run separately')
        host = Path(build) / 'drivers/bus/mhi/host'
        nm = shutil.which('llvm-nm') or shutil.which('nm')
        imports = subprocess.run([nm, '-u', str(host / 'mhi_pci_generic.o')],
                                 check=True, text=True, capture_output=True).stdout
        symbols = subprocess.run([nm, str(host / 'mhi.o')],
                                 check=True, text=True, capture_output=True).stdout
        required = set(re.findall(r'\bU (mhi_\w+)$', imports, re.M))
        exports = set(re.findall(r'__export_symbol_(mhi_\w+)$', symbols, re.M))
        exports.update(re.findall(r'__ksymtab_(mhi_\w+)$', symbols, re.M))
        self.assertTrue(required, 'compiled PCI object has no MHI imports')
        self.assertFalse(required - exports, 'unexported MHI PCI dependencies: ' +
                         ', '.join(sorted(required - exports)))
        # Exercise the real kernel modpost parser too. This isolated pair has no
        # vmlinux symbol table, so unrelated kernel imports are warnings; every
        # MHI PCI dependency must still appear in modpost's actual export table.
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('mhi.o', 'mhi_pci_generic.o'):
                shutil.copyfile(host / name, Path(tmp) / name)
            result = subprocess.run([str(Path(build) / 'scripts/mod/modpost'), '-w', '-M',
                                     '-o', str(Path(tmp) / 'Module.symvers'),
                                     str(Path(tmp) / 'mhi.o'), str(Path(tmp) / 'mhi_pci_generic.o')],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            actual = (Path(tmp) / 'Module.symvers').read_text()
            modpost_exports = set(re.findall(r'^\S+\s+(mhi_\w+)\s+', actual, re.M))
            self.assertFalse(required - modpost_exports,
                             'MHI imports absent from modpost exports: ' +
                             ', '.join(sorted(required - modpost_exports)))

    def test_pinned_kernel_patch_application(self):
        base = os.environ.get('CKB01_KERNEL_BASE')
        if not base:
            self.skipTest('CKB01_KERNEL_BASE not set; pinned application/compile run separately')
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            files = re.findall(r'^--- a/(.+)$', inner_patch(), flags=re.M)
            for rel in files:
                dst = target / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(Path(base) / rel, dst)
            result = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'], cwd=tmp,
                                    input=inner_patch(), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
