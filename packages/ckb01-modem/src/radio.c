/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static json_object *call(Modem *m, QmiMessage *q) {
  GError *e = NULL;
  json_object *r = execute(m, q, false, &e);
  if (q)
    qmi_message_unref(q);
  if (!r)
    r = failure(e ? e->message : "unavailable");
  g_clear_error(&e);
  return r;
}
bool restore_nas(Modem *m, json_object *saved) {
  json_object *t = NULL;
  if (!good(saved) || !json_object_object_get_ex(saved, "tlvs", &t))
    return false;
  QmiMessage *q = request(m, 3, 0x33, NULL);
  if (!q)
    return false;
  /* GET and SET ids differ for the extended LTE and NR masks. */
  const char *keys[] = {"11", "12", "15", "23", "2c", "2d"};
  const guint8 types[] = {0x11, 0x12, 0x15, 0x24, 0x2f, 0x30};
  for (unsigned i = 0; i < G_N_ELEMENTS(keys); i++)
    if (strlen(jstr(t, keys[i])))
      addhex(q, types[i], jstr(t, keys[i]));
  const char *selection = jstr(t, "16"), *plmn = jstr(t, "1b");
  if (!strcmp(selection, "00"))
    addhex(q, 0x16, "0000000000");
  else if (!strcmp(selection, "01") && strlen(plmn) >= 8) {
    char *spec = g_strdup_printf("01%.8s", plmn);
    addhex(q, 0x16, spec);
    if (strlen(plmn) >= 10)
      addhex(q, 0x1a, plmn + 8);
    g_free(spec);
  } else {
    qmi_message_unref(q);
    return false;
  }
  add8(q, 0x17, 0);
  json_object *r = call(m, q);
  bool ok = good(r);
  json_object_put(r);
  if (!ok)
    return false;
  r = call(m, request(m, 3, 0x34, NULL));
  json_object *now = NULL;
  ok = good(r) && json_object_object_get_ex(r, "tlvs", &now);
  if (ok)
    for (unsigned i = 0; i < G_N_ELEMENTS(keys); i++)
      if (strlen(jstr(t, keys[i])) &&
          strcmp(jstr(t, keys[i]), jstr(now, keys[i])))
        ok = false;
  if (ok && strcmp(selection, jstr(now, "16")))
    ok = false;
  if (ok && !strcmp(selection, "01") && strcmp(plmn, jstr(now, "1b")))
    ok = false;
  fprintf(stderr, "NAS restore readback: %s\n", json_object_to_json_string(r));
  json_object_put(r);
  return ok;
}
int radio(Modem *m, const char *mode) {
  const char *path = "/tmp/ckb01-before-n78.json";
  if (!strcmp(mode, "auto")) {
    json_object *s = json_object_from_file(path);
    if (!s) {
      fprintf(stderr, "no saved temporary n78 preference\n");
      return 1;
    }
    bool ok = restore_nas(m, s);
    json_object_put(s);
    if (!ok)
      return 1;
    QmiMessage *q = request(m, 3, 0x33, NULL);
    if (!q)
      return 1;
    add16(q, 0x11, 0x50);
    addhex(q, 0x16, "0000000000");
    add8(q, 0x17, 0);
    json_object *r = call(m, q);
    ok = good(r);
    json_object_put(r);
    if (ok)
      unlink(path);
    return ok ? 0 : 1;
  }
  if (access(path, F_OK) == 0) {
    fprintf(stderr, "previous n78 test not restored; run radio auto first\n");
    return 1;
  }
  json_object *cap = call(m, request(m, 2, 0x45, NULL)), *bands = NULL;
  bool available = false;
  if (good(cap) && json_object_object_get_ex(cap, "nr_bands", &bands))
    for (size_t i = 0; i < json_object_array_length(bands); i++)
      if (json_object_get_int(json_object_array_get_idx(bands, i)) == 78)
        available = true;
  json_object_put(cap);
  if (!available) {
    fprintf(stderr, "module does not report n78; investigate hardware "
                    "MCFG/RF/NV restrictions\n");
    return 1;
  }
  json_object *saved = call(m, request(m, 3, 0x34, NULL));
  if (!good(saved) ||
      json_object_to_file_ext(path, saved, JSON_C_TO_STRING_PRETTY) < 0) {
    json_object_put(saved);
    return 1;
  }
  QmiMessage *q = request(m, 3, 0x33, NULL);
  if (!q) {
    json_object_put(saved);
    return 1;
  }
  guint8 mask[64] = {0};
  mask[77 / 8] = 1 << (77 % 8);
  qmi_message_add_raw_tlv(q, 0x2f, mask, 64, NULL);
  qmi_message_add_raw_tlv(q, 0x30, mask, 64, NULL);
  add16(q, 0x11, 0x50);
  addhex(q, 0x16, "0000000000");
  add8(q, 0x17, 0);
  json_object *r = call(m, q);
  bool ok = good(r);
  json_object_put(r);
  if (!ok)
    restore_nas(m, saved);
  json_object_put(saved);
  return ok ? 0 : 1;
}
