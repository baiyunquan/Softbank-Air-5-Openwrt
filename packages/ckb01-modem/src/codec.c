/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <string.h>
static guint16 le16(const guint8 *p) { return p[0] | p[1] << 8; }
static guint32 le32(const guint8 *p) {
  return (guint32)le16(p) | (guint32)le16(p + 2) << 16;
}
char *hex_encode(const void *v, size_t n) {
  const guint8 *p = v;
  char *s = g_malloc(n * 2 + 1);
  for (size_t i = 0; i < n; i++)
    g_snprintf(s + 2 * i, 3, "%02x", p[i]);
  s[2 * n] = 0;
  return s;
}
GByteArray *hex_decode(const char *s, GError **e) {
  size_t n = strlen(s);
  if (n % 2 || n > 131070) {
    g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_INVALID_DATA,
                        "invalid hex length");
    return NULL;
  }
  GByteArray *b = g_byte_array_sized_new(n / 2);
  for (size_t i = 0; i < n; i += 2) {
    int a = g_ascii_xdigit_value(s[i]), c = g_ascii_xdigit_value(s[i + 1]);
    if (a < 0 || c < 0) {
      g_byte_array_unref(b);
      g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_INVALID_DATA,
                          "non-hex input");
      return NULL;
    }
    guint8 x = a * 16 + c;
    g_byte_array_append(b, &x, 1);
  }
  return b;
}
json_object *failure(const char *s) {
  json_object *o = json_object_new_object();
  json_object_object_add(o, "ok", json_object_new_boolean(false));
  json_object_object_add(o, "error", json_object_new_string(s));
  return o;
}
bool good(json_object *o) {
  json_object *v = NULL;
  return o && json_object_object_get_ex(o, "ok", &v) &&
         json_object_get_boolean(v);
}
const char *jstr(json_object *o, const char *key) {
  json_object *v = NULL;
  return o && json_object_object_get_ex(o, key, &v) ? json_object_get_string(v)
                                                    : "";
}
int64_t jint(json_object *o, const char *key) {
  json_object *v = NULL;
  return o && json_object_object_get_ex(o, key, &v) ? json_object_get_int64(v)
                                                    : -1;
}
static void text_field(json_object *o, const char *key, const guint8 *v,
                       size_t n) {
  char *s = g_strndup((const char *)v, n);
  json_object_object_add(o, key, json_object_new_string(s));
  g_free(s);
}
static void bands(json_object *o, const char *key, const guint8 *v, size_t n,
                  bool list) {
  json_object *a = json_object_new_array();
  if (list) {
    for (unsigned i = 0; i < le16(v); i++)
      json_object_array_add(a, json_object_new_int(le16(v + 2 + i * 2)));
  } else
    for (size_t i = 0; i < n * 8; i++)
      if (v[i / 8] & (1 << (i % 8)))
        json_object_array_add(a, json_object_new_int(i + 1));
  json_object_object_add(o, key, a);
}
json_object *decode_body(unsigned service, const guint8 *p, size_t n,
                         GError **error) {
  json_object *o = NULL, *tlvs = NULL;
  bool result = false;
  const char *why = "truncated QMI body";
  if (n < 7 || le16(p + 5) != n - 7 || (p[0] != 2 && p[0] != 4))
    goto bad;
  unsigned msg = le16(p + 3);
  bool ind = p[0] == 4;
  o = json_object_new_object();
  tlvs = json_object_new_object();
  json_object_object_add(o, "tlvs", tlvs);
  json_object_object_add(o, "service", json_object_new_int(service));
  json_object_object_add(o, "message", json_object_new_int(msg));
  json_object_object_add(o, "transaction", json_object_new_int(le16(p + 1)));
  json_object_object_add(
      o, "kind", json_object_new_string(ind ? "indication" : "response"));
  char *hex = hex_encode(p, n);
  json_object_object_add(o, "raw", json_object_new_string(hex));
  g_free(hex);
  for (size_t i = 7; i < n;) {
    if (n - i < 3)
      goto bad;
    unsigned t = p[i];
    size_t len = le16(p + i + 1);
    i += 3;
    if (len > n - i)
      goto bad;
    const guint8 *v = p + i;
    i += len;
    char key[4];
    g_snprintf(key, sizeof(key), "%02x", t);
    hex = hex_encode(v, len);
    json_object_object_add(tlvs, key, json_object_new_string(hex));
    g_free(hex);
    if ((!ind && t == 2) || (ind && service == 36 && t == 1)) {
      if (len != (!ind ? 4U : 2U)) {
        why = "invalid result TLV";
        goto bad;
      }
      unsigned code = !ind ? le16(v + 2) : le16(v);
      bool ok = !ind ? le16(v) == 0 : code == 0;
      result = true;
      json_object_object_add(o, "ok", json_object_new_boolean(ok));
      json_object_object_add(o, "protocol_error", json_object_new_int(code));
    }
    if (service == 2 && msg == 0x45) {
      if (t == 0x10)
        bands(o, "lte_mask_bands", v, len, false);
      if (t == 0x12 || t == 0x13) {
        if (len < 2 || len != 2U + le16(v) * 2U) {
          why = "invalid band array";
          goto bad;
        }
        bands(o, t == 0x12 ? "lte_bands" : "nr_bands", v, len, true);
      }
    }
    if (service == 2 && msg == 0x23 && t == 1)
      text_field(o, "revision", v, len);
    if (service == 36 && ind) {
      if (t == 0x10) {
        if (len != 4)
          goto bad;
        json_object_object_add(o, "token", json_object_new_int64(le32(v)));
      }
      if (msg == 0x22 && (t == 0x11 || t == 0x12)) {
        if (len < 1 || len != 1U + v[0])
          goto bad;
        hex = hex_encode(v + 1, len - 1);
        json_object_object_add(o, t == 0x11 ? "active_id" : "pending_id",
                               json_object_new_string(hex));
        g_free(hex);
      }
      if (msg == 0x28 && t == 0x12) {
        if (len < 1 || len != 1U + v[0])
          goto bad;
        text_field(o, "description", v + 1, len - 1);
      }
      if (msg == 0x28 && (t == 0x11 || t == 0x13)) {
        if (len != 4)
          goto bad;
        json_object_object_add(o, t == 0x11 ? "size" : "version",
                               json_object_new_int64(le32(v)));
      }
    }
    if (service == 26 && t == 0x10) {
      if (len != 1)
        goto bad;
      json_object_object_add(o, "qos_header", json_object_new_int(v[0]));
    }
    if (service == 26 && t >= 0x11 && t <= 0x13) {
      if (len != 4)
        goto bad;
      json_object_object_add(o,
                             t == 0x11   ? "link_layer"
                             : t == 0x12 ? "uplink_aggregation"
                                         : "downlink_aggregation",
                             json_object_new_int64(le32(v)));
    }
  }
  if (!result) {
    why = "missing operation result";
    goto bad;
  }
  return o;
bad:
  if (o)
    json_object_put(o);
  g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_INVALID_DATA, why);
  return NULL;
}
json_object *decode_message(QmiMessage *m, GError **error) {
  gsize n = 0;
  const guint8 *p = qmi_message_get_raw(m, &n, error);
  if (!p || n < 6)
    return NULL;
  json_object *o = decode_body(qmi_message_get_service(m), p + 6, n - 6, error);
  if (o) {
    char *decoded = qmi_message_get_printable_full(m, NULL, "");
    json_object_object_add(o, "decoded",
                           json_object_new_string(decoded ? decoded : ""));
    g_free(decoded);
  }
  return o;
}
void add32(QmiMessage *m, guint8 t, guint32 x) {
  x = GUINT32_TO_LE(x);
  qmi_message_add_raw_tlv(m, t, (guint8 *)&x, 4, NULL);
}
void add16(QmiMessage *m, guint8 t, guint16 x) {
  x = GUINT16_TO_LE(x);
  qmi_message_add_raw_tlv(m, t, (guint8 *)&x, 2, NULL);
}
void add8(QmiMessage *m, guint8 t, guint8 x) {
  qmi_message_add_raw_tlv(m, t, &x, 1, NULL);
}
void addhex(QmiMessage *m, guint8 t, const char *s) {
  GByteArray *b = hex_decode(s, NULL);
  if (b) {
    qmi_message_add_raw_tlv(m, t, b->data, b->len, NULL);
    g_byte_array_unref(b);
  }
}
