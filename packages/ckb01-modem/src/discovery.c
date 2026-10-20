/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <glob.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static bool content(const char *dir, const char *name, const char *wanted) {
  char *p = g_build_filename(dir, name, NULL), *v = NULL;
  bool ok =
      g_file_get_contents(p, &v, NULL, NULL) && !strcmp(g_strstrip(v), wanted);
  g_free(p);
  g_free(v);
  return ok;
}
json_object *discover(void) { return discover_at("/sys"); }
json_object *discover_at(const char *sysfs) {
  json_object *o = json_object_new_object();
  char *compatible = NULL;
  gsize len = 0;
  bool board = false;
  char *path =
      g_build_filename(sysfs, "firmware/devicetree/base/compatible", NULL);
  if (g_file_get_contents(path, &compatible, &len, NULL))
    for (gsize i = 0; i < len;) {
      size_t n = strnlen(compatible + i, len - i);
      if (n == 10 && !memcmp(compatible + i, "oppo,ckb01", 10))
        board = true;
      i += n + 1;
    }
  g_free(compatible);
  g_free(path);
  if (!board) {
    json_object_put(o);
    return failure("not an oppo,ckb01 board");
  }
  glob_t pci = {0};
  path = g_build_filename(sysfs, "bus/pci/devices/*", NULL);
  glob(path, 0, NULL, &pci);
  g_free(path);
  unsigned found = 0;
  char root[PATH_MAX] = "";
  for (size_t i = 0; i < pci.gl_pathc; i++) {
    char *p = pci.gl_pathv[i];
    if (content(p, "vendor", "0x17cb") && content(p, "device", "0x0306") &&
        content(p, "subsystem_vendor", "0x17cb") &&
        content(p, "subsystem_device", "0x010c")) {
      found++;
      if (!realpath(p, root))
        root[0] = 0;
    }
  }
  globfree(&pci);
  if (found != 1 || !root[0]) {
    json_object_put(o);
    return failure("expected exactly one CKB01 SDX55 PCI device");
  }
  json_object_object_add(o, "pci", json_object_new_string(root));
  const char *patterns[] = {"class/wwan/*qmi*", "class/net/*"};
  for (unsigned t = 0; t < 2; t++) {
    glob_t g = {0};
    path = g_build_filename(sysfs, patterns[t], NULL);
    glob(path, 0, NULL, &g);
    g_free(path);
    for (size_t i = 0; i < g.gl_pathc; i++) {
      char target[PATH_MAX];
      if (!realpath(g.gl_pathv[i], target) ||
          strncmp(target, root, strlen(root)) || target[strlen(root)] != '/')
        continue;
      const char *name = strrchr(g.gl_pathv[i], '/') + 1;
      const char *key = NULL;
      if (!t && (strstr(target, "_QMI/") || strstr(name, "qmi0")))
        key = "control";
      if (t && strstr(target, "_IP_SW0/"))
        key = "management";
      if (t && strstr(target, "_IP_HW0/"))
        key = "data";
      if (key) {
        char *v = !t ? g_strconcat("/dev/", name, NULL) : g_strdup(name);
        json_object_object_add(o, key, json_object_new_string(v));
        g_free(v);
      }
    }
    globfree(&g);
  }
  json_object_object_add(
      o, "ok",
      json_object_new_boolean(strlen(jstr(o, "control")) &&
                              strlen(jstr(o, "management")) &&
                              strlen(jstr(o, "data"))));
  return o;
}
json_object *probe(Modem *m) {
  struct {
    const char *name;
    guint8 svc;
    guint16 msg;
  } qs[] = {{"revision", 2, 0x23},      {"capabilities", 2, 0x45},
            {"sim", 11, 0x2f},          {"nas_preference", 3, 0x34},
            {"serving", 3, 0x24},       {"rf", 3, 0x31},
            {"system_info", 3, 0x4d},   {"signal", 3, 0x4f},
            {"pdc_selected", 36, 0x22}, {"pdc_list", 36, 0x24}};
  json_object *o = json_object_new_object();
  for (unsigned i = 0; i < G_N_ELEMENTS(qs); i++) {
    GError *e = NULL;
    QmiMessage *q = request(m, qs[i].svc, qs[i].msg, &e);
    if (q && qs[i].svc == 36)
      add32(q, qs[i].msg == 0x24 ? 0x11 : 1, 1);
    json_object *r = execute(m, q, qs[i].svc == 36, &e);
    if (q)
      qmi_message_unref(q);
    if (!r)
      r = failure(e ? e->message : "request unavailable");
    g_clear_error(&e);
    json_object_object_add(o, qs[i].name, r);
  }
  return o;
}
