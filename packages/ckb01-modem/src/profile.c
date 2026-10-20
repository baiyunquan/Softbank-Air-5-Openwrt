/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <errno.h>
#include <fcntl.h>
#include <mntent.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define CU "3b6df21a5b1e34bf2b66357780ba035bd65d1ea3"
static json_object *pdc(Modem *m, guint16 msg, const char *id) {
  GError *e = NULL;
  QmiMessage *q = request(m, 36, msg, &e);
  if (q) {
    if (id) {
      GByteArray *b = hex_decode(id, &e);
      if (!b || b->len > 255) {
        if (b)
          g_byte_array_unref(b);
        qmi_message_unref(q);
        g_clear_error(&e);
        return failure("invalid configuration id");
      }
      guint8 data[260] = {1, 0, 0, 0, (guint8)b->len};
      memcpy(data + 5, b->data, b->len);
      qmi_message_add_raw_tlv(q, 1, data, b->len + 5, NULL);
      g_byte_array_unref(b);
    } else
      add32(q, 1, 1);
  }
  json_object *o = execute(m, q, true, &e);
  if (q)
    qmi_message_unref(q);
  if (!o)
    o = failure(e ? e->message : "PDC unavailable");
  g_clear_error(&e);
  return o;
}
static bool mounted_backup(const char *dir) {
  FILE *f = setmntent("/proc/mounts", "r");
  if (!f)
    return false;
  struct mntent *ent;
  bool ok = false;
  size_t longest = 0;
  while ((ent = getmntent(f))) {
    size_t n = strlen(ent->mnt_dir);
    if (n > longest && !strncmp(dir, ent->mnt_dir, n) &&
        (dir[n] == '/' || dir[n] == 0)) {
      longest = n;
      ok = n > 1 &&
           (!strcmp(ent->mnt_type, "vfat") || !strcmp(ent->mnt_type, "ext4") ||
            !strcmp(ent->mnt_type, "exfat")) &&
           strstr(ent->mnt_fsname, "/dev/") == ent->mnt_fsname;
    }
  }
  endmntent(f);
  return ok;
}
static bool save_once(const char *path, json_object *o) {
  int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
  if (fd < 0)
    return false;
  const char *s = json_object_to_json_string_ext(o, JSON_C_TO_STRING_PRETTY);
  size_t n = strlen(s);
  bool ok = write(fd, s, n) == (ssize_t)n && fsync(fd) == 0;
  close(fd);
  if (ok) {
    char *parent = g_path_get_dirname(path);
    int directory = open(parent, O_RDONLY | O_DIRECTORY);
    ok = directory >= 0 && fsync(directory) == 0;
    if (directory >= 0)
      close(directory);
    g_free(parent);
  }
  if (!ok)
    unlink(path);
  return ok;
}
static bool baseline_complete(json_object *backup) {
  const char *required[] = {"revision", "capabilities", "nas_preference", "sim",
                            "original_selected"};
  for (unsigned i = 0; i < G_N_ELEMENTS(required); i++) {
    json_object *v = NULL;
    if (!json_object_object_get_ex(backup, required[i], &v) || !good(v))
      return false;
  }
  json_object *v = NULL;
  return json_object_object_get_ex(backup, "reference_mbn_manifest", &v) && v;
}
int profile(Modem *m, const char *action, const char *dir) {
  if (!mounted_backup(dir)) {
    fprintf(stderr, "profile requires a mounted USB backup directory: %s\n",
            dir);
    return 1;
  }
  if (g_mkdir_with_parents(dir, 0700) < 0)
    return 1;
  char *path = g_build_filename(dir, "original-profile.json", NULL);
  json_object *backup = NULL;
  char *target = NULL;
  if (!strcmp(action, "cu")) {
    json_object *selected = pdc(m, 0x22, NULL);
    if (!good(selected) || !strlen(jstr(selected, "active_id"))) {
      fprintf(stderr, "cannot read original active PDC id\n");
      json_object_put(selected);
      g_free(path);
      return 1;
    }
    if (!strcmp(jstr(selected, "active_id"), CU)) {
      puts("CU already active; no write");
      json_object_put(selected);
      g_free(path);
      return 0;
    }
    json_object *info = pdc(m, 0x28, CU);
    if (!good(info) ||
        strcmp(jstr(info, "description"), "OpenMkt-Commercial-CU") ||
        jint(info, "version") != 0x0a011502 || jint(info, "size") != 26180) {
      fprintf(stderr, "CU id/description/version/size mismatch: %s\n",
              json_object_to_json_string(info));
      json_object_put(info);
      json_object_put(selected);
      g_free(path);
      return 1;
    }
    json_object_put(info);
    backup = probe(m);
    json_object_object_add(backup, "original_selected", selected);
    json_object_object_add(
        backup, "reference_mbn_manifest",
        json_object_from_file("/usr/share/ckb01-modem/mbn-sha256.json"));
    if (!baseline_complete(backup)) {
      fprintf(stderr, "baseline is incomplete; no PDC writes performed\n");
      json_object_put(backup);
      g_free(path);
      return 1;
    }
    if (access(path, F_OK) == 0) {
      json_object *old = json_object_from_file(path), *v = NULL;
      bool same = old && baseline_complete(old) &&
                  json_object_object_get_ex(old, "original_selected", &v) &&
                  !strcmp(jstr(v, "active_id"), jstr(selected, "active_id"));
      if (old)
        json_object_put(old);
      if (!same) {
        fprintf(stderr, "existing backup differs; refusing to overwrite\n");
        json_object_put(backup);
        g_free(path);
        return 1;
      }
    } else if (!save_once(path, backup)) {
      perror("durable profile backup");
      json_object_put(backup);
      g_free(path);
      return 1;
    }
    target = g_strdup(CU);
  } else {
    backup = json_object_from_file(path);
    json_object *v = NULL;
    if (!backup ||
        !json_object_object_get_ex(backup, "original_selected", &v)) {
      fprintf(stderr, "original USB backup unavailable\n");
      if (backup)
        json_object_put(backup);
      g_free(path);
      return 1;
    }
    target = g_strdup(jstr(v, "active_id"));
    GByteArray *b = hex_decode(target, NULL);
    bool valid = b && b->len == 20;
    if (b)
      g_byte_array_unref(b);
    if (!valid) {
      json_object_put(backup);
      g_free(target);
      g_free(path);
      return 1;
    }
  }
  /* Caller holds the exclusive session lock; no active WDS client can remain.
   */
  json_object *r = pdc(m, 0x23, target);
  bool ok = good(r);
  fprintf(stderr, "PDC select: %s\n", json_object_to_json_string(r));
  json_object_put(r);
  if (ok) {
    r = pdc(m, 0x27, NULL);
    ok = good(r);
    fprintf(stderr, "PDC activate: %s\n", json_object_to_json_string(r));
    json_object_put(r);
  }
  if (ok) {
    r = pdc(m, 0x22, NULL);
    ok = good(r) && !strcmp(jstr(r, "active_id"), target);
    fprintf(stderr, "PDC readback: %s\n", json_object_to_json_string(r));
    json_object_put(r);
  }
  if (!ok)
    fprintf(stderr, "activation not confirmed; cold power cycle before status "
                    "or profile restore; do not MHI-reset\n");
  if (ok && !strcmp(action, "restore")) {
    json_object *nas = NULL;
    if (!json_object_object_get_ex(backup, "nas_preference", &nas) ||
        !restore_nas(m, nas)) {
      fprintf(stderr,
              "PDC restored but original NAS preferences not confirmed\n");
      ok = false;
    }
  }
  char *post = g_build_filename(
      dir, !strcmp(action, "cu") ? "after-cu.json" : "after-restore.json",
      NULL);
  r = probe(m);
  json_object_to_file_ext(post, r, JSON_C_TO_STRING_PRETTY);
  json_object_put(r);
  g_free(post);
  json_object_put(backup);
  g_free(target);
  g_free(path);
  return ok ? 0 : 1;
}
