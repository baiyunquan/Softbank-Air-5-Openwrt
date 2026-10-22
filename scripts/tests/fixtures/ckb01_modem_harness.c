#include "modem.h"
#include <stdio.h>
#include <string.h>
extern json_object *probe_transport(Modem *) __attribute__((weak));
extern bool confirm_data_format(Modem *, guint32) __attribute__((weak));
static const char *format_mode;
static unsigned format_queries;
QmiMessage *__wrap_request(Modem *m, guint8 svc, guint16 msg, GError **e) {
  (void)m; (void)e;
  return qmi_message_new(svc, 1, 1, msg);
}
json_object *__wrap_execute(Modem *m, QmiMessage *q, bool pdc, GError **e) {
  (void)m; (void)pdc; (void)e;
  if (format_mode) {
    if (qmi_message_get_service(q) != 26 || qmi_message_get_message_id(q) != 0x21)
      return failure("unexpected format mutation");
    guint16 length=0;
    const guint8 *ep=qmi_message_get_raw_tlv(q,0x10,&length);
    if (!ep || length!=8 || ep[0]!=3 || ep[4]!=4)
      return failure("wrong OEM endpoint");
    format_queries++;
    return json_tokener_parse(!strcmp(format_mode,"qmap") ?
      "{\"ok\":true,\"qos_header\":0,\"link_layer\":2,\"uplink_aggregation\":5,\"downlink_aggregation\":5}" :
      "{\"ok\":true,\"qos_header\":0,\"link_layer\":2,\"uplink_aggregation\":0,\"downlink_aggregation\":0}");
  }
  if (qmi_message_get_service(q) == 2 && qmi_message_get_message_id(q) == 0x23)
    return json_tokener_parse("{\"ok\":true,\"raw_hex\":\"revision-response\"}");
  if (qmi_message_get_service(q) == 11 && qmi_message_get_message_id(q) == 0x2f)
    return failure("SIM personalization locked");
  return failure("unexpected query: transport probe must be read-only");
}
int main(int argc, char **argv) {
  if (argc == 3 && !strcmp(argv[1], "format")) {
    if (!confirm_data_format) { puts("format confirmation not implemented"); return 1; }
    format_mode=argv[2]; Modem m={0};
    bool ok=confirm_data_format(&m,!strcmp(format_mode,"wrong_endpoint") ? 5 : 4);
    return ok==!strcmp(format_mode,"raw") &&
      format_queries==(!strcmp(format_mode,"wrong_endpoint") ? 0U : 1U) ? 0 : 1;
  }
  if (argc == 2 && !strcmp(argv[1], "transport")) {
    if (!probe_transport) { puts("transport probe not implemented"); return 1; }
    Modem m = {0};
    json_object *o = probe_transport(&m);
    puts(json_object_to_json_string(o));
    int rc = good(o) ? 0 : 1;
    json_object_put(o);
    return rc;
  }
  if (argc == 3 && !strcmp(argv[1], "discover")) {
    json_object *o = discover_at(argv[2]);
    puts(json_object_to_json_string_ext(o, JSON_C_TO_STRING_PLAIN));
    json_object_put(o);
    return 0;
  }
  if (argc == 2 && !strcmp(argv[1], "pdc")) {
    GByteArray *b = hex_decode("04010022000c0001020000001004002a000000", NULL);
    QmiMessage *r = qmi_message_new_from_data(36, 7, b, NULL);
    g_byte_array_unref(b);
    QmiMessage *q = qmi_message_new(36, 7, 9, 0x22);
    if (!r || !pdc_matches(r, q, 42) || pdc_matches(r, q, 43))
      return 1;
    qmi_message_unref(q);
    q = qmi_message_new(36, 8, 9, 0x22);
    if (pdc_matches(r, q, 42))
      return 2;
    qmi_message_unref(q);
    q = qmi_message_new(36, 7, 9, 0x27);
    if (pdc_matches(r, q, 42))
      return 3;
    qmi_message_unref(q);
    qmi_message_unref(r);
    return 0;
  }
  return 2;
}
