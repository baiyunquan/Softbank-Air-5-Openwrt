/* SPDX-License-Identifier: GPL-2.0-only */
#include "modem.h"
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <unistd.h>
volatile sig_atomic_t modem_stopping;
static void stop_requested(int sig) {
  (void)sig;
  modem_stopping = 1;
}
void modem_signals(void) {
  signal(SIGTERM, stop_requested);
  signal(SIGINT, stop_requested);
}
static gboolean cancel_poll(gpointer data) {
  Modem *m = data;
  if (modem_stopping && !m->shutting_down)
    g_cancellable_cancel(m->cancel);
  return G_SOURCE_CONTINUE;
}
static void done(GObject *source, GAsyncResult *res, gpointer data) {
  (void)source;
  Modem *m = data;
  m->result = g_object_ref(res);
  g_main_loop_quit(m->loop);
}
static GAsyncResult *wait_result(Modem *m) {
  if (!m->result)
    g_main_loop_run(m->loop);
  GAsyncResult *r = m->result;
  m->result = NULL;
  return r;
}
static void indication(QmiDevice *d, QmiMessage *msg, gpointer data) {
  (void)d;
  Modem *m = data;
  if (g_queue_get_length(&m->indications) >= 64)
    qmi_message_unref(g_queue_pop_head(&m->indications));
  g_queue_push_tail(&m->indications, qmi_message_ref(msg));
}
bool modem_open(Modem *m, const char *path, GError **e) {
  memset(m, 0, sizeof(*m));
  m->loop = g_main_loop_new(NULL, false);
  g_queue_init(&m->indications);
  m->token = g_random_int();
  m->cancel = g_cancellable_new();
  m->cancel_poll = g_timeout_add(50, cancel_poll, m);
  if (!strcmp(path, "qrtr")) {
    qrtr_bus_new(5000, m->cancel, done, m);
    GAsyncResult *r = wait_result(m);
    QrtrBus *b = qrtr_bus_new_finish(r, e);
    g_object_unref(r);
    if (!b)
      return false;
    QrtrNode *node = NULL;
    for (GList *l = qrtr_bus_peek_nodes(b); l; l = l->next)
      if (qrtr_node_lookup_port(l->data, 2) >= 0 &&
          qrtr_node_lookup_port(l->data, 3) >= 0) {
        if (node) {
          g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_FAILED,
                              "ambiguous QRTR modem nodes");
          g_object_unref(b);
          return false;
        }
        node = l->data;
      }
    if (!node) {
      g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_NOT_FOUND,
                          "no DMS/NAS QRTR node");
      g_object_unref(b);
      return false;
    }
    qmi_device_new_from_node(node, m->cancel, done, m);
    r = wait_result(m);
    m->dev = qmi_device_new_from_node_finish(r, e);
    g_object_unref(r);
    g_object_unref(b);
  } else {
    GFile *f = g_file_new_for_path(path);
    qmi_device_new(f, m->cancel, done, m);
    g_object_unref(f);
    GAsyncResult *r = wait_result(m);
    m->dev = qmi_device_new_finish(r, e);
    g_object_unref(r);
  }
  if (!m->dev)
    return false;
  m->signal = g_signal_connect(m->dev, QMI_DEVICE_SIGNAL_INDICATION,
                               G_CALLBACK(indication), m);
  qmi_device_open(m->dev,
                  !strcmp(path, "qrtr") ? QMI_DEVICE_OPEN_FLAGS_NONE
                                        : QMI_DEVICE_OPEN_FLAGS_PROXY,
                  60, m->cancel, done, m);
  GAsyncResult *r = wait_result(m);
  bool ok = qmi_device_open_finish(m->dev, r, e);
  g_object_unref(r);
  return ok;
}
QmiClient *modem_client(Modem *m, guint8 svc, GError **e) {
  if (m->clients[svc])
    return m->clients[svc];
  qmi_device_allocate_client(m->dev, svc, QMI_CID_NONE, 30, m->cancel, done, m);
  GAsyncResult *r = wait_result(m);
  m->clients[svc] = qmi_device_allocate_client_finish(m->dev, r, e);
  g_object_unref(r);
  return m->clients[svc];
}
void modem_close(Modem *m) {
  m->shutting_down = true;
  if (m->cancel_poll) {
    g_source_remove(m->cancel_poll);
    m->cancel_poll = 0;
  }
  if (m->cancel)
    g_cancellable_reset(m->cancel);
  if (m->dev) {
    if (m->signal)
      g_signal_handler_disconnect(m->dev, m->signal);
    for (unsigned i = 0; i < 256; i++)
      if (m->clients[i]) {
        qmi_device_release_client(m->dev, m->clients[i],
                                  QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID,
                                  1, NULL, done, m);
        GAsyncResult *r = wait_result(m);
        qmi_device_release_client_finish(m->dev, r, NULL);
        g_object_unref(r);
        g_object_unref(m->clients[i]);
      }
    qmi_device_close_async(m->dev, 1, NULL, done, m);
    GAsyncResult *r = wait_result(m);
    qmi_device_close_finish(m->dev, r, NULL);
    g_object_unref(r);
    g_object_unref(m->dev);
  }
  g_queue_clear_full(&m->indications, (GDestroyNotify)qmi_message_unref);
  if (m->loop)
    g_main_loop_unref(m->loop);
  g_clear_object(&m->cancel);
}
QmiMessage *request(Modem *m, guint8 svc, guint16 msg, GError **e) {
  if (modem_stopping && !m->shutting_down) {
    g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_CANCELLED,
                        "modem shutdown requested");
    return NULL;
  }
  QmiClient *c = modem_client(m, svc, e);
  return c ? qmi_message_new(svc, qmi_client_get_cid(c), ++m->tid, msg) : NULL;
}
static void record(json_object *o) {
  json_object_object_add(o, "monotonic_ms",
                         json_object_new_int64(g_get_monotonic_time() / 1000));
  json_object_object_add(o, "unix_time",
                         json_object_new_int64(g_get_real_time() / 1000000));
  FILE *f = fopen("/tmp/ckb01-modem.jsonl", "a");
  if (f) {
    flock(fileno(f), LOCK_EX);
    fprintf(f, "%s\n",
            json_object_to_json_string_ext(o, JSON_C_TO_STRING_PLAIN));
    flock(fileno(f), LOCK_UN);
    fclose(f);
  }
}
bool pdc_matches(QmiMessage *r, QmiMessage *q, guint32 token) {
  if (!qmi_message_is_indication(r) ||
      qmi_message_get_service(r) != qmi_message_get_service(q) ||
      qmi_message_get_client_id(r) != qmi_message_get_client_id(q) ||
      qmi_message_get_message_id(r) != qmi_message_get_message_id(q))
    return false;
  guint16 len = 0;
  const guint8 *t = qmi_message_get_raw_tlv(r, 0x10, &len);
  guint32 received = 0;
  if (t && len == 4)
    memcpy(&received, t, 4);
  return t && len == 4 && GUINT32_FROM_LE(received) == token;
}
json_object *execute(Modem *m, QmiMessage *q, bool pdc, GError **e) {
  if (!q)
    return NULL;
  guint32 token = ++m->token;
  if (pdc)
    add32(q, 0x10, token);
  if (m->shutting_down)
    g_cancellable_reset(m->cancel);
  qmi_device_command_full(m->dev, q, NULL, m->shutting_down ? 2 : 60, m->cancel,
                          done, m);
  GAsyncResult *ar = wait_result(m);
  QmiMessage *r = qmi_device_command_full_finish(m->dev, ar, e);
  g_object_unref(ar);
  if (!r)
    return NULL;
  json_object *o = decode_message(r, e);
  qmi_message_unref(r);
  if (!o)
    return NULL;
  record(o);
  if (!pdc || !good(o))
    return o;
  json_object_put(o);
  gint64 until = g_get_monotonic_time() + 60000000;
  while (g_get_monotonic_time() < until) {
    if (modem_stopping && !m->shutting_down) {
      g_set_error_literal(e, G_IO_ERROR, G_IO_ERROR_CANCELLED,
                          "shutdown while waiting for PDC indication");
      return NULL;
    }
    while (!g_queue_is_empty(&m->indications)) {
      r = g_queue_pop_head(&m->indications);
      if (!pdc_matches(r, q, token)) {
        qmi_message_unref(r);
        continue;
      }
      o = decode_message(r, e);
      qmi_message_unref(r);
      if (o)
        record(o);
      return o;
    }
    while (g_main_context_iteration(NULL, false)) {
    }
    g_usleep(10000);
  }
  g_set_error_literal(
      e, G_IO_ERROR, G_IO_ERROR_TIMED_OUT,
      "PDC response received but matching indication timed out");
  return NULL;
}
