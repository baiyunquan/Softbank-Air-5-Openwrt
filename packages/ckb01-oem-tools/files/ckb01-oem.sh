#!/bin/sh
# Shared host-side helpers. The module is reached through IP_SW0, not DIAG.
CKB01_OEM_HOST=${CKB01_OEM_HOST:-169.254.10.2}
CKB01_OEM_TIMEOUT=${CKB01_OEM_TIMEOUT:-30}
CKB01_TIMEOUT=/usr/libexec/timeout-coreutils

ckb01_oem_error() { printf 'ckb01-oem: %s\n' "$*" >&2; }
ckb01_oem_guard() {
 [ "$(id -u)" = 0 ] || { ckb01_oem_error 'root is required'; return 77; }
 tr '\000' '\n' </sys/firmware/devicetree/base/compatible 2>/dev/null | grep -qx 'oppo,ckb01' || {
  ckb01_oem_error 'this command requires the oppo,ckb01 OpenWrt board profile'; return 69
 }
 case "$CKB01_OEM_HOST" in ''|*[!0-9.]*) ckb01_oem_error 'CKB01_OEM_HOST must be an IPv4 address'; return 64;; esac
 case "$CKB01_OEM_TIMEOUT" in ''|*[!0-9]*) ckb01_oem_error 'invalid CKB01_OEM_TIMEOUT'; return 64;; esac
 [ "$CKB01_OEM_TIMEOUT" -ge 1 ] && [ "$CKB01_OEM_TIMEOUT" -le 600 ] || return 64
}
ckb01_oem_discover() {
 ckb01_oem_discovery=$(ckb01-modem discover 2>/dev/null) || :
 ckb01_oem_management=$(printf '%s' "$ckb01_oem_discovery" | jsonfilter -e '@.management' 2>/dev/null) || :
 [ -n "$ckb01_oem_management" ]
}
ckb01_oem_network() {
 ckb01_oem_guard || return $?
 if ! ckb01_oem_discover; then
  ckb01_oem_error 'SDX55 IP_SW0 is unavailable; inspect ckb01-modem discover and MHI logs (no reset attempted)'
  return 69
 fi
 ip link set dev "$ckb01_oem_management" up || return $?
 ip addr replace 169.254.10.1/24 dev "$ckb01_oem_management" || return $?
}
ckb01_oem_call() {
 "$CKB01_TIMEOUT" -k 2 "$CKB01_OEM_TIMEOUT" /usr/bin/oatprsync "$@"
}
