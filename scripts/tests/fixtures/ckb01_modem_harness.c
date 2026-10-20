#include "modem.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
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
