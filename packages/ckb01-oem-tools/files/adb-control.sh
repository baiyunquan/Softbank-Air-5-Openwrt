#!/bin/sh
# Runs on SDX55 ARMv7 Linux. Everything this controller writes is in /tmp.
set -eu
state=/tmp/ckb01-adb
payload=$state/adb-tcp-property.so
snapshot=$state/snapshot
gpio=/sys/class/gpio/gpio92

error() { printf 'ckb01-adb(module): %s\n' "$*" >&2; }
identity() {
 [ "$(id -u)" = 0 ] && [ "$(uname -m)" = armv7l ] || {
  error 'expected SDX55 ARMv7 root'; return 69
 }
 [ "$(cat /sys/devices/soc0/machine)" = SDXPRAIRIE ] || {
  error 'expected the SDXPRAIRIE module'; return 69
 }
}
owned_pid() {
 [ -r "$state/adbd.pid" ] || return 1
 pid=$(cat "$state/adbd.pid")
 case "$pid" in ''|*[!0-9]*) return 1;; esac
 [ "$pid" -gt 1 ] && [ -r "/proc/$pid/environ" ] || return 1
 [ "$(readlink "/proc/$pid/exe")" = /sbin/adbd ] || return 1
 tr '\000' '\n' <"/proc/$pid/environ" | grep -qx "LD_PRELOAD=$payload"
}
restore_gpio() {
 [ -r "$state/gpio92.direction" ] || return 0
 [ -d "$gpio" ] || { error 'GPIO92 disappeared; snapshot retained'; return 1; }
 direction=$(cat "$state/gpio92.direction")
 case "$direction" in
  out)
   value=$(cat "$state/gpio92.value")
   case "$value" in 0|1) :;; *) return 1;; esac
   [ "$(cat "$gpio/direction")" = out ] || echo out >"$gpio/direction"
   echo "$value" >"$gpio/value"
   ;;
  in) echo in >"$gpio/direction" ;;
  *) return 1 ;;
 esac
}
restore() {
 if [ ! -f "$snapshot" ]; then
  error 'no managed ADB snapshot; original service left unchanged'
  return 0
 fi
 if owned_pid; then
  kill "$pid" 2>/dev/null || :
  sleep 1
  if owned_pid; then kill -9 "$pid" 2>/dev/null || :; sleep 1; fi
  if owned_pid; then error 'managed adbd did not exit; snapshot retained'; return 1; fi
 fi
 if [ "$(cat "$state/service.was-active")" = 1 ]; then
  if ! systemctl start adbd.service; then
   restore_gpio || :
   error 'original adbd service failed to start; snapshot retained'
   return 1
  fi
 fi
 # /etc/launch_adbd writes GPIO92=1; restore the state captured before enable.
 restore_gpio || return $?
 rm -f "$snapshot" "$state/adbd.pid" "$state/running.sha256" "$state/service.was-active" "$state/gpio92.direction" "$state/gpio92.value"
 printf 'original_adbd_restored=1\n'
}
start() {
 expected=${1:-}
 case "$expected" in ''|*[!0-9a-f]*) error 'missing payload SHA256'; return 64;; esac
 [ "${#expected}" = 64 ] || return 64
 actual=$(sha256sum "$payload"); actual=${actual%% *}
 [ "$actual" = "$expected" ] || { error 'payload SHA256 mismatch'; return 65; }
 if [ -f "$snapshot" ] && owned_pid; then
  if [ "$(cat "$state/running.sha256" 2>/dev/null || :)" != "$expected" ]; then
   error 'a different managed payload is running; disable before enabling the upgraded payload'
   return 75
  fi
  printf 'managed_adbd=already-running\npid=%s\ntcp_port=5555\n' "$pid"
  return 0
 fi
 if [ ! -f "$snapshot" ]; then
  active=$(systemctl is-active adbd.service 2>/dev/null || :)
  case "$active" in
   active) was_active=1 ;;
   inactive|failed|unknown) was_active=0 ;;
   *) error "adbd service is transitioning ($active); retry later"; return 75 ;;
  esac
  if [ "$was_active" = 0 ] && pgrep -x adbd >/dev/null; then
   error 'unmanaged adbd is running; refusing to replace it'
   return 75
  fi
  printf '%s\n' "$was_active" >"$state/service.was-active"
  if [ -r "$gpio/direction" ] && [ -r "$gpio/value" ]; then
   cat "$gpio/direction" >"$state/gpio92.direction"
   cat "$gpio/value" >"$state/gpio92.value"
  fi
  : >"$snapshot"
 fi
 trap 'result=$?; if [ "$result" -ne 0 ]; then restore || :; fi' EXIT
 systemctl stop adbd.service
 if pgrep -x adbd >/dev/null; then
  error 'an adbd process remains after stopping its unit'
  return 75
 fi
 LD_PRELOAD="$payload" /sbin/adbd </dev/null >"$state/adbd.log" 2>&1 &
 printf '%s\n' "$!" >"$state/adbd.pid"
 printf '%s\n' "$expected" >"$state/running.sha256"
 sleep 1
 if ! owned_pid; then
  cat "$state/adbd.log" >&2 || :
  error 'temporary adbd failed to start'
  return 70
 fi
 printf 'managed_adbd=running\npid=%s\ntcp_port=5555\n' "$pid"
 trap - EXIT
}
status() {
 printf 'machine=%s\n' "$(cat /sys/devices/soc0/machine)"
 if owned_pid; then printf 'managed_adbd=running\npid=%s\n' "$pid"; else printf 'managed_adbd=not-running\n'; fi
 printf 'original_snapshot=%s\n' "$([ -f "$snapshot" ] && echo present || echo absent)"
 printf 'adbd_service=%s\n' "$(systemctl is-active adbd.service 2>/dev/null || :)"
 printf 'gpio92=%s\n' "$(cat "$gpio/value" 2>/dev/null || echo unavailable)"
 netstat -lntp 2>/dev/null | grep -E ':5555[[:space:]]' || :
}

identity || exit $?
umask 077
case "${1:-status}" in
 start) shift; start "$@" ;;
 stop) restore ;;
 status) status ;;
 *) error 'use start SHA256, stop or status'; exit 64 ;;
esac
