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
 json_get_vars apn endpoint metric
 [ -n "$apn" ] || apn=3gnet
 case "$endpoint" in ''|*[!0-9]*)
  proto_notify_error "$interface" ENDPOINT_NOT_CONFIRMED
  proto_block_restart "$interface"
  logger -t ckb01-modem 'Set network.cellular.endpoint only after OEM endpoint mapping has been recorded'
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
