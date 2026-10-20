/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <unistd.h>
static void usage(void) {
  fprintf(stderr,
          "ckb01-modem [--device /dev/wwan...qmi0|qrtr] "
          "status|probe|discover|radio n78|radio auto|profile cu|profile "
          "restore|connect APN NETIF "
          "ENDPOINT\nckb01-modem decode SERVICE BODY_HEX\nCKB01_BACKUP_DIR "
          "must refer to a USB directory for profile operations.\n");
}
int main(int argc, char **argv) {
  if (argc == 4 && !strcmp(argv[1], "decode")) {
    GError *e = NULL;
    GByteArray *b = hex_decode(argv[3], &e);
    json_object *o =
        b ? decode_body(strtoul(argv[2], NULL, 0), b->data, b->len, &e) : NULL;
    if (b)
      g_byte_array_unref(b);
    if (!o) {
      fprintf(stderr, "%s\n", e ? e->message : "decode error");
      g_clear_error(&e);
      return 1;
    }
    puts(json_object_to_json_string_ext(o, JSON_C_TO_STRING_PLAIN));
    json_object_put(o);
    return 0;
  }
  const char *device = NULL;
  int i = 1;
  if (argc > 3 && !strcmp(argv[i], "--device")) {
    device = argv[i + 1];
    i += 2;
  }
  if (i >= argc) {
    usage();
    return 2;
  }
  const char *cmd = argv[i++];
  bool prof = !strcmp(cmd, "profile"), conn = !strcmp(cmd, "connect"),
       rf = !strcmp(cmd, "radio");
  if ((prof &&
       (i >= argc || (strcmp(argv[i], "cu") && strcmp(argv[i], "restore")))) ||
      (rf &&
       (i >= argc || (strcmp(argv[i], "n78") && strcmp(argv[i], "auto")))) ||
      (!prof && !conn && !rf && strcmp(cmd, "probe") && strcmp(cmd, "status") &&
       strcmp(cmd, "discover")) ||
      (conn && argc - i != 3)) {
    usage();
    return 2;
  }
  json_object *d = discover();
  if (!strcmp(cmd, "discover")) {
    puts(json_object_to_json_string_ext(d, JSON_C_TO_STRING_PLAIN));
    int rc = good(d) ? 0 : 1;
    json_object_put(d);
    return rc;
  }
  if (!device)
    device = jstr(d, "control");
  if (!strlen(device)) {
    fprintf(stderr, "No channel-14 QMI control port: %s\n",
            json_object_to_json_string(d));
    json_object_put(d);
    return 1;
  }
  modem_signals();
  int lock = open("/var/lock/ckb01-modem.lock", O_CREAT | O_RDWR, 0600);
  bool locked = lock >= 0;
  if (locked && (prof || conn || rf)) {
    gint64 until = g_get_monotonic_time() + 30000000;
    while (flock(lock, LOCK_EX | LOCK_NB)) {
      if (modem_stopping || g_get_monotonic_time() >= until) {
        locked = false;
        break;
      }
      g_usleep(100000);
    }
  }
  if (!locked) {
    fprintf(stderr,
            "modem writer did not stop within 30s; no new operation started\n");
    if (lock >= 0)
      close(lock);
    json_object_put(d);
    return 1;
  }
  /* Diagnostic readers use qmi-proxy; they may run beside the session owner. */
  Modem m;
  GError *e = NULL;
  if (!modem_open(&m, device, &e)) {
    fprintf(stderr, "%s\n", e ? e->message : "open failed");
    g_clear_error(&e);
    modem_close(&m);
    close(lock);
    json_object_put(d);
    return 1;
  }
  int rc = 0;
  if (prof) {
    const char *dir = g_getenv("CKB01_BACKUP_DIR");
    rc = profile(&m, argv[i], dir ? dir : "/mnt/usb/air5-backup/cu");
  } else if (rf) {
    rc = radio(&m, argv[i]);
  } else if (conn) {
    char *end = NULL;
    unsigned long ep = strtoul(argv[i + 2], &end, 0);
    if (!end || *end || ep > 0xffffffffUL)
      rc = 2;
    else
      rc = session(&m, argv[i], argv[i + 1], device, ep);
  } else {
    json_object *o = probe(&m);
    json_object *data =
        json_object_from_file("/tmp/ckb01-cellular-session.json");
    if (data)
      json_object_object_add(o, "data_session", data);
    json_object_object_add(o, "discovery", d);
    d = NULL;
    puts(json_object_to_json_string_ext(o, JSON_C_TO_STRING_PRETTY));
    json_object_put(o);
  }
  modem_close(&m);
  close(lock);
  if (d)
    json_object_put(d);
  return rc;
}
