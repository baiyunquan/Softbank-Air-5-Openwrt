#!/bin/sh
# Separate MHI QMI protocol; no USB sysfs or raw_ip attribute assumption.
[ -n "$INCLUDE_ONLY" ] || {
 . /lib/functions.sh
 . ../netifd-proto.sh
 init_proto "$@"
}
proto_ckb01_qmi_init_config() {
 no_device=1
 available=1
 proto_config_add_string apn
 proto_config_add_string endpoint
 proto_config_add_int metric
}
proto_ckb01_qmi_setup() {
 local interface="$1" apn endpoint metric
 if [ -f /etc/ckb01-maintenance ] || [ -e /tmp/ckb01-edl-active ]; then
  proto_notify_error "$interface" MAINTENANCE_MODE
  proto_block_restart "$interface"
  return 1
 fi
 json_get_vars apn endpoint metric
 [ -n "$apn" ] || apn=3gnet
 local gate="${CKB01_MODEM_STATE_DIR:-/tmp}/ckb01-modem-ready.json" key
 for key in ok management qmi qrtr; do
  if [ "$(jsonfilter -i "$gate" -e "@.$key" 2>/dev/null)" != true ]; then
   proto_notify_error "$interface" TRANSPORT_NOT_READY
   return 1
  fi
 done
 # OEM MHI_UCI_EP_LOOKUP plus WDA GET, recorded 2026-10-20.
 [ -n "$endpoint" ] || endpoint=4
 case "$endpoint" in 4) :;; *)
  proto_notify_error "$interface" ENDPOINT_NOT_CONFIRMED
  proto_block_restart "$interface"
  logger -t ckb01-modem 'CKB01 measured endpoint is PCIe type=3/interface=4; refusing a different endpoint'
  return 1;;
 esac
 proto_run_command "$interface" /usr/sbin/ckb01-session "$interface" "$apn" "$endpoint"
}
proto_ckb01_qmi_teardown() {
 proto_kill_command "$1" 15
 proto_init_update '*' 0
 proto_send_update "$1"
}
[ -n "$INCLUDE_ONLY" ] || add_protocol ckb01_qmi
