# Repository workflow guidance

- Treat this repository as an independent device-adaptation project. Continue on the existing adaptation branch and merge upstream updates there; do not create a new branch for each sync or open pull requests to the upstream repository.
- Treat build verification as a diagnostic stage, not a gate on compilation or artifact upload. A failed FIT, initramfs, USB image, or preflight check must emit a GitHub Actions `warning`, retain its log and summary, and continue with available raw build outputs.
- Keep compiler/build failures distinct from validation failures. A genuine compile failure may fail the workflow; a validator mismatch must not prevent uploading the compiled ITB and other available artifacts.
- When changing CKB01 board roles or device-tree expectations, keep the board DTS, `scripts/ckb01-fit.py`, and its test fixture in sync. Hardware-verified mapping: switch port 1 / PHY8 is physical LAN1 and is WAN; switch port 2 / PHY9 is physical LAN2 and is LAN. PHY reset uses TLMM GPIO37, active low.
- If FIT validation fails, preserve the original compiled FIT as `artifacts/uimage-initramfs.itb` and use it as the fallback input for USB image packaging. Clearly mark it as unvalidated in the workflow warning and uploaded logs.
