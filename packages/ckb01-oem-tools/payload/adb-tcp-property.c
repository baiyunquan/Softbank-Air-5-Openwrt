/* Temporary SDX55 adbd property override. No persistent files are changed.
 * OEM libcutils property_get only copies its default; property_set is a stub.
 * Preserve that behavior except for the requested TCP transport port.
 */
static int equal(const char *a, const char *b)
{
    if (!a || !b) return 0;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
int property_get(const char *key, char *value, const char *fallback)
{
    const char *source = fallback;
    int count = 0;
    if (equal(key, "service.adb.tcp.port")) source = "5555";
    if (!source) return 0;
    while (source[count] && count < 91) {
        value[count] = source[count];
        ++count;
    }
    value[count] = 0;
    return count;
}
