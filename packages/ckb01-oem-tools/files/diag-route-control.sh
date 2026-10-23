#!/bin/sh
# Runs on SDX55. The routing owner keeps /dev/diag open; its exit restores
# the OEM default. No SDX55 persistent file or GPIO is changed.
umask 077
root=/tmp/ckb01-diag-route
program=/usr/bin/test_diag
expected=9b97b570a7b1787c13e7438712f7911868666daab143e982ef9e1e9c1bd559d3
error() { echo "ckb01-diag-route: $*" >&2; }
guard() {
 [ "$(id -u)" = 0 ] && [ "$(uname -m)" = armv7l ] &&
 [ "$(cat /sys/devices/soc0/machine)" = SDXPRAIRIE ] || { error 'wrong module identity'; return 69; }
}
alive() {
 [ -r "$root/owner" ] || return 1
 read -r pid birth <"$root/owner"
 case "$pid:$birth" in *[!0-9:]*|:*) return 1;; esac
 [ -r "/proc/$pid/stat" ] || return 1
 [ "$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)" = "$birth" ] || return 1
 [ "$(awk '{print $3}' "/proc/$pid/stat" 2>/dev/null)" != Z ] || return 1
 cmd=$(tr '\000' ' ' 2>/dev/null <"/proc/$pid/cmdline")
 [ "$cmd" = "$program -p 7" ] || [ "$cmd" = "$program -p 7 " ]
}
lock() {
 mkdir -p "$root"; chmod 700 "$root"
 if ! mkdir "$root/lock" 2>/dev/null; then
  owner=$(cat "$root/lock/pid" 2>/dev/null)
  case "$owner" in ''|*[!0-9]*) error 'route lock is incomplete'; return 75;; esac
  kill -0 "$owner" 2>/dev/null && { error 'route lock is busy'; return 75; }
  rm -f "$root/lock/pid"
  rmdir "$root/lock" && mkdir "$root/lock" || return 75
 fi
 echo "$$" >"$root/lock/pid"
 trap 'rm -f "$root/lock/pid"; rmdir "$root/lock" 2>/dev/null || :' EXIT
}
guard || exit $?
case "${1:-status}" in
 status)
  if alive; then echo "route_process=running pid=$pid"; else echo route_process=stopped; fi
  ;;
 start)
  lock || exit $?
  if alive; then echo "route_process=running pid=$pid"; exit 0; fi
  # Do not take ownership of another diagnostic application or default route.
  [ "$(tr -d '\000\r\n' </data/debug_transport.conf)" = usb ] || { error 'only the verified USB default is supported'; exit 69; }
  [ -z "$(pidof test_diag 2>/dev/null)" ] || { error 'unmanaged test_diag is already running'; exit 75; }
  [ "$(sha256sum "$program" | cut -d' ' -f1)" = "$expected" ] || { error 'unverified OEM test_diag binary'; exit 69; }
  "$program" -p 7 >"$root/owner.log" 2>&1 </dev/null &
  pid=$!
  birth=$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)
  echo "$pid $birth" >"$root/owner"
  sleep 1
  alive || { error 'routing owner exited; inspect owner.log'; exit 1; }
  echo "route_process=running pid=$pid"
  ;;
 stop)
  lock || exit $?
  if alive; then
   kill -TERM "$pid" || exit 1
   n=0
   while alive && [ "$n" -lt 5 ]; do sleep 1; n=$((n+1)); done
   alive && { error 'owner did not exit; no forced reset attempted'; exit 1; }
  fi
  rm -f "$root/owner"
  echo route_process=stopped
  ;;
 *) error 'expected start, stop or status'; exit 64;;
esac
