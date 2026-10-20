/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static json_object *run(Modem *m, QmiMessage *q) {
  GError *e = NULL;
  json_object *r = execute(m, q, false, &e);
  if (q)
    qmi_message_unref(q);
  if (!r)
    r = failure(e ? e->message : "client unavailable");
  g_clear_error(&e);
  return r;
}
static void endpoint(QmiMessage *q, guint8 t, guint32 ep) {
  guint32 data[] = {GUINT32_TO_LE(3), GUINT32_TO_LE(ep)};
  qmi_message_add_raw_tlv(q, t, (guint8 *)data, 8, NULL);
}
static guint32 value(json_object *o, const char *key) {
  json_object *t = NULL;
  if (!json_object_object_get_ex(o, "tlvs", &t))
    return 0;
  GByteArray *b = hex_decode(jstr(t, key), NULL);
  guint32 v = 0;
  if (b && b->len == 4)
    memcpy(&v, b->data, 4);
  if (b)
    g_byte_array_unref(b);
  return GUINT32_FROM_LE(v);
}
static void spawn_ip(const char *const *args, bool *ok) {
  gint status = 0;
  GError *e = NULL;
  *ok = g_spawn_sync(NULL, (char **)args, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL,
                     NULL, NULL, &status, &e) &&
        g_spawn_check_wait_status(status, &e);
  if (e) {
    fprintf(stderr, "%s\n", e->message);
    g_error_free(e);
  }
}
static void publish(const char *iface, const char *data, json_object *four,
                    json_object *six) {
  json_object *o = json_object_new_object();
  json_object_object_add(o, "ifname", json_object_new_string(data));
  json_object_object_add(o, "up", json_object_new_boolean(four || six));
  if (four)
    json_object_object_add(o, "ipv4", json_object_get(four));
  if (six)
    json_object_object_add(o, "ipv6", json_object_get(six));
  json_object_to_file_ext("/tmp/ckb01-cellular-session.json", o,
                          JSON_C_TO_STRING_PRETTY);
  const char *args[] = {
      "/lib/netifd/ckb01-update", iface,
      json_object_to_json_string_ext(o, JSON_C_TO_STRING_PLAIN), NULL};
  gint status = 0;
  GError *e = NULL;
  if (!g_spawn_sync(NULL, (char **)args, NULL, 0, NULL, NULL, NULL, NULL,
                    &status, &e) ||
      !g_spawn_check_wait_status(status, &e))
    fprintf(stderr, "netifd update: %s\n", e ? e->message : "failed");
  g_clear_error(&e);
  json_object_put(o);
}
static json_object *settings(Modem *m) {
  QmiMessage *q = request(m, 1, 0x2d, NULL);
  if (!q)
    return failure("WDS unavailable");
  add32(q, 0x10,
        QMI_WDS_REQUESTED_SETTINGS_DNS_ADDRESS |
            QMI_WDS_REQUESTED_SETTINGS_IP_ADDRESS |
            QMI_WDS_REQUESTED_SETTINGS_GATEWAY_INFO |
            QMI_WDS_REQUESTED_SETTINGS_MTU |
            QMI_WDS_REQUESTED_SETTINGS_IP_FAMILY);
  json_object *r = run(m, q);
  if (!good(r))
    return r;
  json_object *tlvs = NULL;
  json_object_object_get_ex(r, "tlvs", &tlvs);
  const char *keys[] = {"1e", "20", "21", "15", "16", "25", "26", "27", "28"};
  const char *names[] = {"address",  "gateway",  "netmask", "dns1",  "dns2",
                         "address6", "gateway6", "dns6_1",  "dns6_2"};
  for (unsigned i = 0; i < 9; i++) {
    GByteArray *b = hex_decode(jstr(tlvs, keys[i]), NULL);
    if (!b)
      continue;
    char address[INET6_ADDRSTRLEN];
    if (i < 5 && b->len == 4) {
      guint32 v;
      memcpy(&v, b->data, 4);
      v = GUINT32_TO_BE(GUINT32_FROM_LE(v));
      if (inet_ntop(AF_INET, &v, address, sizeof(address)))
        json_object_object_add(r, names[i], json_object_new_string(address));
    }
    if (i >= 5 && b->len == (i < 7 ? 17U : 16U)) {
      if (inet_ntop(AF_INET6, b->data, address, sizeof(address)))
        json_object_object_add(r, names[i], json_object_new_string(address));
      if (i == 5)
        json_object_object_add(r, "prefix6", json_object_new_int(b->data[16]));
    }
    g_byte_array_unref(b);
  }
  json_object_object_add(r, "mtu", json_object_new_int64(value(r, "29")));
  return r;
}
static bool bind_wds(Modem *m, guint32 ep, bool qmap, unsigned family) {
  QmiMessage *q = request(m, 1, 0xa2, NULL);
  if (!q)
    return false;
  endpoint(q, 0x10, ep);
  if (qmap)
    add8(q, 0x11, 1);
  add32(q, 0x13, 1);
  json_object *r = run(m, q);
  bool ok = good(r);
  json_object_put(r);
  if (!ok)
    return false;
  q = request(m, 1, 0x4d, NULL);
  if (!q)
    return false;
  add8(q, 1, family);
  r = run(m, q);
  ok = good(r);
  json_object_put(r);
  return ok;
}
static json_object *start(Modem *m, const char *apn, unsigned family) {
  QmiMessage *q = request(m, 1, 0x20, NULL);
  if (!q)
    return failure("WDS unavailable");
  qmi_message_add_raw_tlv(q, 0x14, (const guint8 *)apn, strlen(apn), NULL);
  add8(q, 0x16, 0);
  add8(q, 0x19, family);
  return run(m, q);
}
static void end(Modem *m, guint32 handle) {
  m->shutting_down = true;
  if (!handle)
    return;
  QmiMessage *q = request(m, 1, 0x21, NULL);
  if (!q)
    return;
  add32(q, 1, handle);
  json_object *r = run(m, q);
  json_object_put(r);
}
static bool connected(Modem *m) {
  json_object *r = run(m, request(m, 1, 0x22, NULL)), *t = NULL;
  json_object_object_get_ex(r, "tlvs", &t);
  bool ok = good(r) && g_str_has_prefix(jstr(t, "01"), "02");
  json_object_put(r);
  return ok;
}
int session(Modem *m, const char *apn, const char *iface, const char *device,
            guint32 ep) {

  json_object *d = discover();
  char *data = g_strdup(jstr(d, "data"));
  json_object_put(d);
  if (!*data) {
    g_free(data);
    return 1;
  }
  /* Endpoint is supplied from the recorded OEM endpoint investigation, never
   * inferred from a network interface name or the shared PCI device ID. */
  QmiMessage *q = request(m, 26, 0x21, NULL);
  if (!q) {
    g_free(data);
    return 1;
  }
  endpoint(q, 0x10, ep);
  json_object *r = run(m, q);
  if (!good(r)) {
    fprintf(stderr, "endpoint WDA query failed: %s\n",
            json_object_to_json_string(r));
    json_object_put(r);
    g_free(data);
    return 1;
  }
  json_object_put(r);
  bool qmap = false, format = false;
  for (unsigned attempt = 0; attempt < 2; attempt++) {
    q = request(m, 26, 0x20, NULL);
    if (!q)
      break;
    add8(q, 0x10, 0);
    add32(q, 0x11, 2);
    add32(q, 0x12, attempt ? 5 : 0);
    add32(q, 0x13, attempt ? 5 : 0);
    endpoint(q, 0x17, ep);
    r = run(m, q);
    bool accepted = good(r);
    json_object_put(r);
    if (!accepted)
      continue;
    q = request(m, 26, 0x21, NULL);
    if (!q)
      break;
    endpoint(q, 0x10, ep);
    r = run(m, q);
    format = good(r) && jint(r, "qos_header") == 0 &&
             jint(r, "link_layer") == 2 &&
             jint(r, "uplink_aggregation") == (attempt ? 5 : 0) &&
             jint(r, "downlink_aggregation") == (attempt ? 5 : 0);
    json_object_put(r);
    if (format) {
      qmap = attempt;
      break;
    }
  }
  if (!format) {
    fprintf(stderr, "raw-IP/plain QMAP format was not confirmed\n");
    g_free(data);
    return 1;
  }
  bool ok = false;
  const char *up[] = {"ip", "link", "set", "dev", data, "up", NULL};
  spawn_ip(up, &ok);
  if (!ok) {
    g_free(data);
    return 1;
  }
  const char *net = data;
  if (qmap) {
    const char *args[] = {
        "ip",           "link", "add",   "link",   data, "name",
        "ckb01-rmnet1", "type", "rmnet", "mux_id", "1",  NULL};
    spawn_ip(args, &ok);
    if (!ok) {
      g_free(data);
      return 1;
    }
    net = "ckb01-rmnet1";
    const char *u[] = {"ip", "link", "set", "dev", net, "up", NULL};
    spawn_ip(u, &ok);
  }
  q = request(m, 3, 0x33, NULL);
  if (!q)
    goto cleanup;
  add16(q, 0x11, 0x50);
  addhex(q, 0x16, "0000000000");
  add8(q, 0x17, 0);
  r = run(m, q);
  ok = good(r);
  json_object_put(r);
  if (!ok)
    goto cleanup;
  if (!bind_wds(m, ep, qmap, 4))
    goto cleanup;
  Modem v6;
  GError *error = NULL;
  bool opened = modem_open(&v6, device, &error);
  if (!opened) {
    fprintf(stderr, "IPv6 control open: %s\n",
            error ? error->message : "failed");
    g_clear_error(&error);
    modem_close(&v6);
    goto cleanup;
  }
  guint32 h4 = 0, h6 = 0;
  r = start(m, apn, 4);
  h4 = good(r) ? value(r, "01") : 0;
  fprintf(stderr, "IPv4 start: %s\n", json_object_to_json_string(r));
  json_object_put(r);
  if (!h4) {
    modem_close(&v6);
    goto cleanup;
  }
  if (bind_wds(&v6, ep, qmap, 6)) {
    r = start(&v6, apn, 6);
    h6 = good(r) ? value(r, "01") : 0;
    fprintf(stderr, "IPv6 start: %s\n",
            json_object_to_json_string(
                r)); /* Only explicit unsupported IP-family or 3GPP IPv4-only
                        permits fallback. */
    bool fallback = jint(r, "protocol_error") ==
                    QMI_PROTOCOL_ERROR_INVALID_IP_FAMILY_PREFERENCE;
    json_object *t = NULL;
    json_object_object_get_ex(r, "tlvs", &t);
    const char *reason = jstr(t, "11");
    if (!strcmp(reason, "06003200"))
      fallback = true;
    json_object_put(r);
    if (!h6 && !fallback) {
      end(m, h4);
      modem_close(&v6);
      goto cleanup;
    }
  } else {
    end(m, h4);
    modem_close(&v6);
    goto cleanup;
  }
  json_object *four = settings(m), *six = h6 ? settings(&v6) : NULL;
  bool valid4 = good(four) && strlen(jstr(four, "address"));
  bool valid6 = !h6 || (good(six) && strlen(jstr(six, "address6")));
  if (valid4 && valid6) {
    publish(iface, net, four, six);
    while (!modem_stopping) {
      for (unsigned t = 0; t < 150 && !modem_stopping; t++) {
        while (g_main_context_iteration(NULL, false)) {
        }
        g_usleep(100000);
      }
      if (modem_stopping)
        break;
      q = request(m, 1, 0x24, NULL);
      if (q)
        add32(q, 1, 0xff);
      r = run(m, q);
      json_object_put(r);
      if (!connected(m) || (h6 && !connected(&v6)))
        break;
    }
  }
  json_object_put(four);
  if (six)
    json_object_put(six);
  publish(iface, net, NULL, NULL);
  end(m, h4);
  end(&v6, h6);
  modem_close(&v6);
cleanup:
  if (qmap) {
    const char *args[] = {"ip", "link", "del", "dev", "ckb01-rmnet1", NULL};
    spawn_ip(args, &ok);
  }
  g_free(data);
  return modem_stopping ? 0 : 1;
}
