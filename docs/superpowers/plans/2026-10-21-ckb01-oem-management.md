# CKB01 OEM management integration plan

> Execute inline on the existing adaptation branch, as required by AGENTS.md.

**Goal:** Ship the original command/file client with its complete private runtime, and a repeatable SDX55 ADB enable/restore path in the CKB01 firmware.

**Architecture:** Keep the IPQ AArch64 vendor client, loader and dependencies under `/usr/lib/ckb01-oem/runtime`. Use IP_SW0 discovery independently of QMI/data readiness. Upload a previously exercised ARMv7 property shim and a reversible controller into SDX55 `/tmp/ckb01-adb`; run the unchanged OEM adbd with TCP port5555, then restore its original service and GPIO92 state on disable.

**Constraints:** No automatic EDL, reboot, MHI reset, NV or flash writes. No automatic ADB enable at boot. Private runtime must not replace system libraries. Verification remains advisory and cannot block raw firmware upload. Record build/static evidence and leave new-firmware hardware acceptance explicit.

## Tasks

- [x] Generate a deterministic vendor runtime archive and provenance, resolving every DT_NEEDED dependency and retaining the original musl loader.
- [x] Add `ckb01-oem-tools` package with isolated `oatprsync`, bounded command execution with stdout/stderr/exit status, file operations and management interface setup.
- [x] Add the ARMv7 TCP property payload and a module-side controller with idempotent start, process ownership checks, captured service/GPIO state and restore.
- [x] Add `ckb01-adb` enable/connect/shell/pull/push/status/disable commands and local dependency on the existing OpenWrt adb package.
- [x] Integrate package preparation/configuration, advisory image checks and existing fixtures, diagnostics and documentation.
- [x] Produce a deployable management overlay and build-ready repository changes; record exactly what was built and what remains to be exercised on new OpenWrt.

## Delivery evidence and remaining acceptance

- The initial local backup did not match the current OEM runtime. Replaced it with a read-only capture of all 13 files from the current IPQ system; each captured file matches the device-side SHA256. Provenance records this source explicitly.
- Generated the management overlay under `action_result/oem-management-20261021/` in the parent project. Native OpenWrt adb/timeout and the existing modem package remain installation prerequisites; the firmware package declares those dependencies.
- Shell/Python syntax and whitespace checks are separate from firmware compilation. No local firmware build or integrated hardware acceptance has been performed. Existing CI checks remain advisory and retain raw artifacts.
- New OpenWrt acceptance remains: command stdout/stderr/exit status, file transfer, repeated ADB enable/disable, original service/GPIO restoration and recovery after module reboot. Prior ARMv7 payload evidence is recorded separately from this package integration.

## Review focus

- Unavailable/delayed IP_SW0: fail with an actionable error, without MHI reset or requiring IP_HW0.
- Failed/ambiguous remote command: never replay it automatically; preserve remote output paths when no exit status is available.
- Repeated ADB enable: preserve the first snapshot; do not overwrite it with the temporary service's state.
- GPIO92: the OEM adbd launcher changes it, so restore the captured state after starting the original service.
- Recovery after link loss/module reboot: no persistent SDX55 startup edits, no stale host state assumed authoritative, and no unrelated process killed.
