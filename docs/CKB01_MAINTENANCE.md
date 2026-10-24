# CKB01 PCIe EDL / EFS maintenance

This image is built for manual maintenance. Programmer authentication, EDL/FP
transition and actual NAND reads on CKB01 remain **pending hardware acceptance**.
No device was contacted during this build. USB PID 9008 is not a PCIe success criterion.

## Boot and access

Write the complete `air5-ckb01-usb.img` to a USB drive. Keep the boot FIT and
AIR5ROOT from the same build. The existing OEM boot filename remains
`uimage-initramfs.itb`. LAN2 and Wi-Fi provide management at `192.168.5.1`;
LAN1 remains wired WAN. APs remain Air5-2G/Air5-5G, key Air5-OpenWrt.
Normal USB-root expansion, per-unit ART calibration and heartbeat remain enabled.
Maintenance initializes IP_SW0 and PCIe DIAG, without cellular auto-dial.

## Manual commands

```sh
ckb01-edl status
ckb01-edl enter
ckb01-edl backup-efs --output /root/efs-backups
```

`enter` sends the OEM-compatible DIAG request once. Explicit alternative:
`ckb01-edl enter --method mhi` uses the mainline MHI EDL doorbell mechanism.
There is no automatic fallback between entry methods and no reset retry loop.
The kernel arm/attach/cancel ABI is described in the kernel patch. Attach loads
only the pinned RAM programmer via BHI and binds FP FIREHOSE channels 34/35.
A module already in EDL/FP waits for manual attachment; boot alone uploads nothing.

Backup never enters EDL implicitly. Its destination must be persistent storage;
when booted in RAM fallback, supply a mounted external storage directory.
Each run has a unique directory, programmer provenance, kernel and protocol logs,
MIBIB/geometry, and two reads. Incomplete reads retain `.partial` files. A short
read, timeout or NAK ends the pass without automatic sector resume. Only two
complete ACK-terminated reads with equal length/hash establish transport completion.

The CKB01 reference geometry is NAND 512 MiB, page 4096, eraseblock 262144;
`efs2` starts at 0x500000 and is 0xb00000 bytes (11 MiB). Actual storage information
and the MIBIB table must agree. This differs from the T99W175 partition layout.
The backup is programmer/ECC main data; OOB, bad-block semantics and restore
suitability require separate evidence. Unreported properties remain unknown.

After success or a failed EDL transition, retain logs and fully remove/reconnect
power to return the module to normal NAND boot. Do not repeatedly invoke reset.
An interrupted command may retain `/tmp/ckb01-edl-active` and locks intentionally;
inspect the cached kernel state before manual cleanup. No internal startup files
are changed by this maintenance package, and the reader exposes no NAND write command.

## Build and evidence

`Build CKB01 PCIe EDL maintenance` calls the pinned existing build with the
maintenance fragment. Toolchain/download/compiler caches are reused. Kernel changes
are compiled. Validation is advisory: failures warn and retain raw FIT, available
IMG and logs. Genuine compilation errors are reported separately. The package
preserves the signed ARM programmer byte-for-byte, including during AArch64 packaging.
See the installed `/usr/share/ckb01-edl/provenance.json` for hash and source.

Build success does not establish programmer authentication, EDL/FP or NAND-read
success. Those hardware items remain pending in the uploaded status reports.

## EDL kernel stage logs

The diagnostic maintenance build emits `CKB01-EDL` at info level to the kernel
log and, with the image's `loglevel=7`, UART. Logs start only after an explicit
`arm` on the exact CKB01 maintenance profile. Normal AMSS boot does not enable
these traces or upload a programmer.

Each record contains `seq`, `cpu`, `op`, `stage`, `edge`, `rc`, `a`, `b`, and the
cached host PM/EE values. Access pairs share the same nonzero `op`; high-level
stages use `op=0`. `begin` precedes the operation and `end` follows its return.
An `end` for a posted MMIO write means the CPU's write function returned; it
does not establish that the endpoint accepted the request. Likewise a queued
DIAG write does not prove EDL entry, and successful BHI transfer alone is not
proof of a working Firehose NAND reader.

| Stages | Operation / `a`, `b` fields |
| --- | --- |
| `arm`, `attach`, `attach-arm-timer` | Session setup; arm timeout/trace limit, IRQ count/BAR length, timer synchronization |
| `pci-vendor` | Existing PCI configuration read; config offset/vendor value |
| `sample-bhioff`, `sample-ee` | Existing direct BHI reads; BAR offset/read value |
| `mmio-read`, `mmio-write` | Existing generic PCI MMIO accesses; BAR-relative offset/read or written value |
| `wait-edl`, `wait-fp` | One-second progress from existing samples; sampled EE/remaining milliseconds or FP-ready flag |
| `freeze-*` | PM lock, diagnostic abort/stop, health timer, recovery/state work synchronization |
| `retire-sync-irq`, `retire-free-irqs`, `retire-tasklet` | Host teardown; event/IRQ index and Linux IRQ number where applicable |
| `free-event-irq`, `free-bhi-irq` | Individual `free_irq` calls, including shared-vector actions |
| `retire-clients`, `retire-dma`, `retire-unregister` | Client removal, old DMA/context release, MHI controller removal |
| `fp-register`, `fp-prepare`, `prepare-context`, `fp-power-up` | New FP controller registration, DMA allocation and startup |
| `programmer-request`, `programmer-load` | Firmware request and RAM load; returned length and load type |
| `bhi-submit`, `bhi-wait` | BHI submission and completion; DMA address/length, session ID, transfer status/wait result |
| `ready-transition`, `ready-reset-clear`, `ready-bit`, `ready-init-mmio`, `ready-request-m0` | READY/reset handshake, MMIO initialization and M0 request |
| `intvec-thread`, `intvec-state`, `state-worker`, `m0-transition` | Existing interrupt and state handling; IRQ number, EE/state, transition type |
| `fp-create-clients`, `fp-queue`, `firehose-bound` | FP device creation and confirmed driver binding of channels 34/35 |
| `arm-timer`, `attach` with `fail` | Expiry/failure; error code and last observed EE |
| `fault-pm-lock`, `fault-pci-vendor`, `fault-link-status`, `fault-snapshot` | Existing first-fault handling and its existing PCI config reads; no added reads |

Detailed PCI/MMIO/interrupt access pairs share a per-session budget, **256 by
default**, including across controller replacement. When exhausted, a single
`stage=io-budget edge=exhausted` is emitted; high-level phases and one-second
progress continue. An admitted pair still emits its end even if another CPU
exhausts the budget. For another diagnostic build, the module-load parameter
`ckb01_edl_trace_io_limit=N` selects 0..4096 pairs; values above 4096 are clamped,
and 0 disables detailed pairs while retaining stage logs. Put it on the existing
`mhi_pci_generic` line in `/etc/modules.d/29-ckb01-edl` before the next boot;
do not unload/reload the controller to change it during a maintenance session.

`ckb01-edl status` also appends cached `trace_seq`, `trace_io`, `trace_stage` and
`trace_edge`. Reading status adds no PCI/BAR accesses. These are concurrent
breadcrumbs, not an atomic history or a persistent crash record. After a hard
reset, use the host's timestamped UART capture for the previous session.

For example, a final `stage=sample-ee edge=begin op=...` with no matching end
places the missing return at the execution-environment read, unless the capture
itself was lost or the trace budget warning already appeared. A
`stage=retire-sync-irq edge=begin` without its end places it at IRQ synchronization.
This build adds no diagnostic register scans, reset retries or NAND writes;
it preserves the 120-second session deadline and existing access order. Console
logging changes timing, so a successful run with logs alone does not establish
that the underlying fault has been repaired.
