#!/bin/sh
# shellcheck shell=busybox
# Shared CKB01 calibration/bring-up helpers. Sourcing this file has no side effects.

ckb01_find_art_chardev() {
	local label art
	for label in '0:ART' ART '0:art' art; do
		art=$(find_mtd_chardev "$label")
		[ -n "$art" ] || continue
		printf '%s\n' "$art"
		return 0
	done
	return 1
}

ckb01_wifi_has_band() (
	band=$1
	info=$2
	awk -v band="$band" '
	$1 == "*" && $3 == "MHz" {
		frequency = $2 + 0
		if (band == "2g" && frequency >= 2400 && frequency < 2500) found = 1
		if (band == "5g" && frequency >= 5000 && frequency < 6000) found = 1
	}
	END { if (found) print "yes"; else exit 1 }
	' "$info"
)

ckb01_caldata_extract() (
	art=$1
	size=$2
	output=$3
	state=$4
	umask 077
	work=$(mktemp -d /tmp/ckb01-caldata.XXXXXX) || return 1
	trap 'rm -rf "$work"' EXIT
	trap 'exit 1' HUP INT TERM
	failed() {
		printf 'status=failed\nreason=%s\n' "$1" >"$state"
		logger -t ckb01-caldata "$1"
		return 1
	}
	[ -r "$art" ] || { failed 'ART partition is missing or unreadable'; return 1; }
	[ "$size" = 262144 ] || { failed 'unexpected ART size (expected 262144)'; return 1; }
	for read in first second; do
		dd if="$art" of="$work/$read" bs=4096 count=64 2>/dev/null || {
			failed 'ART read failed'; return 1;
		}
		[ "$(wc -c <"$work/$read")" -eq 262144 ] || {
			failed 'short ART read'; return 1;
		}
	done
	cmp -s "$work/first" "$work/second" || { failed 'ART reads disagree'; return 1; }
	# OEM read_caldata_to_fs.sh: skip=4096, count=131072.
	dd if="$work/first" of="$work/caldata" bs=4096 skip=1 count=32 2>/dev/null || return 1
	[ "$(wc -c <"$work/caldata")" -eq 131072 ] || { failed 'short calibration slice'; return 1; }
	# Qualcomm board/cal images use the XOR of all little-endian 16-bit words.
	# Arithmetic XOR works with BusyBox awk without non-POSIX bitwise extensions.
	hexdump -v -e '1/2 "%u\n"' "$work/caldata" | awk '
	function word_xor(a,b, r,p) {
		r=0; p=1
		while (a || b) {
			if ((a%2) != (b%2)) r+=p
			a=int(a/2); b=int(b/2); p*=2
		}
		return r
	}
	{ sum=word_xor(sum,$1); words++ }
	END { exit !(words == 65536 && sum == 65535) }' || {
		failed 'calibration checksum mismatch'; return 1;
	}
	art_hash=$(sha256sum "$work/first" | awk '{print $1}')
	cal_hash=$(sha256sum "$work/caldata" | awk '{print $1}')
	mkdir -p "$(dirname "$output")" || return 1
	# Stage in the destination directory so firmware readers see an atomic publish.
	staged=$(mktemp "$output.XXXXXX") || return 1
	if ! cat "$work/caldata" >"$staged" || ! mv -f "$staged" "$output"; then
		rm -f "$staged"
		failed 'cannot publish calibration'; return 1
	fi
	printf 'status=ready\nsource=%s\nart_bytes=262144\noffset=0x1000\ncal_bytes=131072\nart_sha256=%s\ncal_sha256=%s\nchecksum=xor16-ffff\n' \
		"$art" "$art_hash" "$cal_hash" >"$state"
	logger -t ckb01-caldata "Loaded CKB01 calibration from $art; SHA256=$cal_hash" || true
)

ckb01_wifi_valid_mac() {
	printf '%s\n' "$1" | grep -Eq '^([0-9a-f]{2}:){5}[0-9a-f]{2}$' || return 1
	case "$1" in
		00:00:00:00:00:00|ff:ff:ff:ff:ff:ff|00:03:7f:ba:db:ad|00:03:7f:12:*|02:03:7f:12:*) return 1 ;;
	esac
	[ "$((0x${1%%:*} & 1))" -eq 0 ]
}

ckb01_wifi_mac() (
	candidate=$(printf '%s' "$1" | tr 'A-F' 'a-f')
	seed=$2
	band=$3
	used=" $4 "
	if ckb01_wifi_valid_mac "$candidate"; then
		case "$used" in
			*" $candidate "*) ;;
			*) printf '%s\n' "$candidate"; return 0 ;;
		esac
	fi
	[ -n "$seed" ] || return 1
	for counter in 0 1 2 3; do
		hash=$(printf 'CKB01-WLAN-%s:%s:%s\n' "$band" "$seed" "$counter" | sha256sum | awk '{print $1}')
		first=$(printf '%s' "$hash" | cut -c1-2)
		mac=$(printf '%02x:%s' "$(( (0x$first & 254) | 2 ))" \
			"$(printf '%s' "$hash" | cut -c3-12 | sed 's/../&:/g;s/:$//')")
		case "$used" in
			*" $mac "*) continue ;;
			*) printf '%s\n' "$mac"; return 0 ;;
		esac
	done
	return 1
)

ckb01_wifi_channel() (
	band=$1
	info=$2
	allowed() {
		awk -v chan="[$1]" -v freq="$2" -v width="${3:-20}" '
		$1 == "*" && $2 == freq && $3 == "MHz" && $4 == chan &&
		$0 !~ /disabled|no IR|radar detection/ &&
		!(width == 80 && $0 ~ /no 80MHz/) { found=1 }
		END { exit !found }' "$info"
	}
	if [ "$band" = 2g ]; then
		for channel in 1 6 11 2 3 4 5 7 8 9 10 12 13; do
			if allowed "$channel" "$((2407 + channel * 5))"; then
				printf '%s\n' "$channel"; return 0
			fi
		done
	elif [ "$band" = 5g ]; then
		# Prefer the locally measured low-latency CKB01 block; fall back to 36.
		# All four non-DFS 80 MHz constituent channels must permit AP use.
		for channel in 149 36; do
			available=1
			for delta in 0 4 8 12; do
				part=$((channel + delta))
				allowed "$part" "$((5000 + part * 5))" 80 || available=0
			done
			[ "$available" -eq 1 ] || continue
			printf '%s\n' "$channel"; return 0
		done
	fi
	return 1
)

ckb01_wifi_wait() {
	local ckb01_attempts=$1
	local ckb01_attempt=0
	while [ "$ckb01_attempt" -lt "$ckb01_attempts" ]; do
		ckb01_attempt=$((ckb01_attempt + 1))
		ckb01_wifi_try && return 0
		[ "$ckb01_attempt" -ge "$ckb01_attempts" ] || sleep 2
	done
	return 1
}

ckb01_wifi_configure_radio() (
	radio=$1
	phy=$2
	band=$3
	info=$4
	candidate=$5
	seed=$6
	used=$7
	# Mark the device, rather than the SSID, so LuCI edits survive later retries.
	[ "$(uci -q get "wireless.$radio.ckb01_initialized")" != 1 ] || return 0
	grep -q 'HE Iftypes:.*AP' "$info" || { echo "$band: no HE AP capability on $phy" >&2; return 1; }
	channel=$(ckb01_wifi_channel "$band" "$info") || {
		echo "$band: no usable non-DFS channel/block" >&2; return 1;
	}
	mac=$(ckb01_wifi_mac "$candidate" "$seed" "$band" "$used") || return 1
	case "$band" in
		2g) ssid=Air5-2G; htmode=HE20 ;;
		5g) ssid=Air5-5G; htmode=HE80 ;;
		*) return 1 ;;
	esac
	uci -q batch <<EOF
set wireless.$radio.country='CN'
set wireless.$radio.channel='$channel'
set wireless.$radio.htmode='$htmode'
set wireless.$radio.disabled='0'
set wireless.default_$radio.disabled='1'
set wireless.ckb01_$band='wifi-iface'
set wireless.ckb01_$band.device='$radio'
set wireless.ckb01_$band.network='lan'
set wireless.ckb01_$band.mode='ap'
set wireless.ckb01_$band.ssid='$ssid'
set wireless.ckb01_$band.encryption='psk2'
set wireless.ckb01_$band.key='Air5-OpenWrt'
set wireless.ckb01_$band.macaddr='$mac'
set wireless.ckb01_$band.disabled='0'
set wireless.$radio.ckb01_initialized='1'
commit wireless
EOF
)
