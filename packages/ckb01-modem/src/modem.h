/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CKB01_MODEM_H
#define CKB01_MODEM_H
#include <json-c/json.h>
#include <libqmi-glib.h>
#include <libqrtr-glib.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct {
  QmiDevice *dev;
  QmiClient *clients[256];
  GMainLoop *loop;
  GAsyncResult *result;
  GQueue indications;
  guint16 tid;
  guint32 token;
  gulong signal;
  GCancellable *cancel;
  guint cancel_poll;
  bool shutting_down;
} Modem;
extern volatile sig_atomic_t modem_stopping;
void modem_signals(void);
char *hex_encode(const void *, size_t);
GByteArray *hex_decode(const char *, GError **);
json_object *decode_body(unsigned, const guint8 *, size_t, GError **);
json_object *decode_message(QmiMessage *, GError **);
json_object *failure(const char *);
bool good(json_object *);
const char *jstr(json_object *, const char *);
int64_t jint(json_object *, const char *);
void add32(QmiMessage *, guint8, guint32);
void add16(QmiMessage *, guint8, guint16);
void add8(QmiMessage *, guint8, guint8);
void addhex(QmiMessage *, guint8, const char *);
bool modem_open(Modem *, const char *, GError **);
void modem_close(Modem *);
QmiClient *modem_client(Modem *, guint8, GError **);
QmiMessage *request(Modem *, guint8, guint16, GError **);
bool pdc_matches(QmiMessage *, QmiMessage *, guint32);
json_object *execute(Modem *, QmiMessage *, bool, GError **);
json_object *discover(void);
json_object *discover_at(const char *);
json_object *probe(Modem *);
int radio(Modem *, const char *);
bool restore_nas(Modem *, json_object *);
int profile(Modem *, const char *, const char *);
int session(Modem *, const char *, const char *, const char *, guint32);
#endif
