// SPDX-License-Identifier: BSD-3-Clause
/* Read-only Firehose transport and NAND table handling adapted from QFenix
 * firehose.c / gpt.c, commit 318a49cee9663a6a79fbcc8b44db8a3d2afdec2b.
 * Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
 * See LICENSE.qfenix. This client deliberately contains no write/reset commands.
 */
#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <linux/fs.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>
#include <termios.h>
#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ctype.h>
#include <libxml/parser.h>
#include <json-c/json.h>
#include "sha2.h"

#define PAGE UINT64_C(4096)
#define ERASE UINT64_C(262144)
#define TOTAL UINT64_C(536870912)
#define MIBIB UINT64_C(2621440)
#define EFS_START UINT64_C(5242880)
#define EFS_LEN UINT64_C(11534336)
#define XML_LIMIT (256 * 1024)
#define IO_SIZE (64 * 1024)
#ifndef CKB01_IO_TIMEOUT_MS
#define CKB01_IO_TIMEOUT_MS 30000
#endif
struct client {
    int dev, dir, log, report;
    unsigned char buf[IO_SIZE];
    size_t begin, end;
    uint64_t page, erase, blocks, payload;
    char error[256];
    json_object *metadata, *storage, *logs;
};
static int fail(struct client *c, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(c->error, sizeof(c->error), fmt, ap);
    va_end(ap);
    fprintf(stderr, "%s\n", c->error);
    return -1;
}
static int write_all(int fd, const void *p, size_t n)
{
    const unsigned char *b = p;
    while (n) {
        ssize_t k = write(fd, b, n);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return -1;
        b += k; n -= (size_t)k;
    }
    return 0;
}
static int64_t now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int ready(struct client *c, short events, int64_t deadline)
{
    struct pollfd p = { .fd = c->dev, .events = events };
    for (;;) {
        int64_t remaining = deadline - now_ms();
        if (remaining <= 0) return fail(c, "Firehose timeout");
        int n = poll(&p, 1, (int)remaining);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return fail(c, "poll: %s", strerror(errno));
        if (!n) return fail(c, "Firehose timeout");
        if (p.revents & events) return 0;
        if (p.revents & (POLLERR | POLLHUP | POLLNVAL))
            return fail(c, "Firehose disconnected or transport error");
    }
}
static int fill(struct client *c, int64_t deadline)
{
    if (c->begin != c->end) return 0;
    c->begin = c->end = 0;
    for (;;) {
        if (ready(c, POLLIN, deadline)) return -1;
        ssize_t n = read(c->dev, c->buf, sizeof(c->buf));
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (n <= 0) return fail(c, "Firehose short read: %s", n ? strerror(errno) : "EOF");
        c->end = (size_t)n;
        return 0;
    }
}
static int log_xml(struct client *c, const char *direction, const char *p, size_t n)
{
    if (write_all(c->log, direction, strlen(direction)) ||
        write_all(c->log, p, n) || write_all(c->log, "\n", 1))
        return fail(c, "XML log write failed: %s", strerror(errno));
    return 0;
}
static int send_xml(struct client *c, const char *s)
{
    size_t left = strlen(s);
    const char *p = s;
    int64_t deadline = now_ms() + CKB01_IO_TIMEOUT_MS;
    if (log_xml(c, "TX ", s, left)) return -1;
    while (left) {
        if (ready(c, POLLOUT, deadline)) return -1;
        ssize_t n = write(c->dev, p, left);
        if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
        if (n <= 0) return fail(c, "Firehose command write failed");
        p += n; left -= (size_t)n;
    }
    return 0;
}
/* Consume only through </data>. Any subsequent bytes, including raw bytes
 * coalesced with this XML in one driver read, stay in the transport buffer. */
static xmlDoc *receive_xml(struct client *c, int64_t deadline)
{
    static const char closing[] = "</data>";
    char *s = malloc(XML_LIMIT + 1);
    size_t n = 0;
    xmlDoc *doc = NULL;
    if (!s) { fail(c, "XML allocation failed"); return NULL; }
    while (n < XML_LIMIT) {
        if (fill(c, deadline)) goto done;
        unsigned char ch = c->buf[c->begin++];
        if (!n && isspace(ch)) continue;
        s[n++] = (char)ch;
        if (n >= sizeof(closing) - 1 &&
            !memcmp(s + n - sizeof(closing) + 1, closing, sizeof(closing) - 1)) {
            s[n] = 0;
            if (log_xml(c, "RX ", s, n)) goto done;
            doc = xmlReadMemory(s, (int)n, "firehose-response.xml", NULL,
                                XML_PARSE_NONET | XML_PARSE_NOERROR | XML_PARSE_NOWARNING);
            if (!doc) { fail(c, "Malformed Firehose XML"); goto done; }
            xmlNode *root = xmlDocGetRootElement(doc);
            if (doc->intSubset || doc->extSubset || !root || xmlStrcmp(root->name, BAD_CAST "data")) {
                xmlFreeDoc(doc); doc = NULL;
                fail(c, "Unexpected Firehose XML document or DTD");
            }
            goto done;
        }
    }
    fail(c, "Firehose XML exceeds bounded document limit");
done:
    /* Preserve malformed/truncated XML as evidence too. */
    if (!doc && n) (void)log_xml(c, "RX-INCOMPLETE ", s, n);
    free(s);
    return doc;
}
static bool number(const char *s, uint64_t *out)
{
    char *end;
    if (!s || !*s || *s == '-' || *s == '+') return false;
    errno = 0;
    unsigned long long value = strtoull(s, &end, 0);
    if (errno || end == s || *end) return false;
    *out = value;
    return true;
}
static int merge_value(struct client *c, const char *key, uint64_t value)
{
    uint64_t *field = NULL;
    if (!strcmp(key, "page_size") || !strcmp(key, "SECTOR_SIZE_IN_BYTES")) field = &c->page;
    if (!strcmp(key, "block_size")) field = &c->erase;
    if (!strcmp(key, "total_blocks")) field = &c->blocks;
    if (!field) return 0;
    if (!value || (*field && *field != value)) return fail(c, "Missing or contradictory storage geometry: %s", key);
    *field = value;
    json_object_object_add(c->storage, key, json_object_new_uint64(value));
    return 0;
}
static int storage_log(struct client *c, const char *text)
{
    const char *keys[] = { "page_size", "SECTOR_SIZE_IN_BYTES", "block_size", "total_blocks" };
    json_object_array_add(c->logs, json_object_new_string(text));
    const char *start = strchr(text, '{');
    if (start) {
        json_tokener *tok = json_tokener_new();
        json_object *obj = json_tokener_parse_ex(tok, start, (int)strlen(start));
        bool valid = json_tokener_get_error(tok) == json_tokener_success && obj && json_object_is_type(obj, json_type_object);
        json_tokener_free(tok);
        if (!valid) { if (obj) json_object_put(obj); return fail(c, "Malformed storage JSON"); }
        for (size_t i = 0; i < sizeof(keys)/sizeof(keys[0]); i++) {
            json_object *v;
            if (json_object_object_get_ex(obj, keys[i], &v)) {
                uint64_t value;
                if ((!json_object_is_type(v, json_type_int) && !json_object_is_type(v, json_type_string)) ||
                    !number(json_object_get_string(v), &value) || merge_value(c, keys[i], value)) {
                    json_object_put(obj); return fail(c, "Invalid storage geometry field %s", keys[i]);
                }
            }
        }
        json_object *mem;
        if (json_object_object_get_ex(obj, "mem_type", &mem) &&
            (!json_object_is_type(mem, json_type_string) ||
             strcasecmp(json_object_get_string(mem), "nand"))) {
            json_object_put(obj); return fail(c, "Programmer storage is not NAND");
        }
        json_object *policy;
        if (json_object_object_get_ex(obj, "bad_block_policy", &policy)) {
            if (!json_object_is_type(policy, json_type_string)) {
                json_object_put(obj); return fail(c, "Invalid reported bad-block policy");
            }
            json_object_object_add(c->metadata, "bad_block_policy",
                                   json_object_new_string(json_object_get_string(policy)));
            json_object_object_add(c->metadata, "bad_block_policy_source",
                                   json_object_new_string("programmer getstorageinfo"));
        }
        json_object_put(obj);
    } else {
        for (size_t i = 0; i < sizeof(keys)/sizeof(keys[0]); i++) {
            const char *p = text;
            while ((p = strstr(p, keys[i]))) {
                size_t len = strlen(keys[i]);
                if ((p == text || !isalnum((unsigned char)p[-1])) && p[len] == '=') {
                    char valuebuf[40]; size_t j = 0;
                    p += len + 1;
                    while (p[j] && !isspace((unsigned char)p[j]) && p[j] != ',' && j < sizeof(valuebuf)-1) {
                        valuebuf[j] = p[j]; j++;
                    }
                    valuebuf[j] = 0;
                    uint64_t value;
                    if (!number(valuebuf, &value) || merge_value(c, keys[i], value)) return fail(c, "Invalid storage geometry field %s", keys[i]);
                    p += j;
                } else p += len;
            }
        }
    }
    return 0;
}
/* raw_expected: -1 regular ACK, 1 entry into raw, 0 final ACK. */
static int response(struct client *c, int raw_expected, bool storage, bool configure)
{
    int64_t deadline = now_ms() + CKB01_IO_TIMEOUT_MS;
    for (unsigned docs = 0; docs < 1024; docs++) {
        xmlDoc *doc = receive_xml(c, deadline);
        if (!doc) return -1;
        int result = 1;
        bool seen_response = false;
        for (xmlNode *n = xmlDocGetRootElement(doc)->children; n; n = n->next) {
            if (n->type != XML_ELEMENT_NODE) continue;
            if (!xmlStrcmp(n->name, BAD_CAST "log")) {
                xmlChar *v = xmlGetProp(n, BAD_CAST "value");
                if (!v) { result = fail(c, "Firehose log missing value"); break; }
                if (storage) result = storage_log(c, (const char *)v) ? -1 : result;
                xmlFree(v);
                if (result < 0) break;
            } else if (!xmlStrcmp(n->name, BAD_CAST "response")) {
                if (seen_response) { result = fail(c, "Multiple Firehose responses"); break; }
                seen_response = true;
                xmlChar *v = xmlGetProp(n, BAD_CAST "value");
                xmlChar *raw = xmlGetProp(n, BAD_CAST "rawmode");
                if (!v || xmlStrcmp(v, BAD_CAST "ACK")) result = fail(c, "Firehose NAK or missing ACK");
                else if ((raw_expected == 1 && (!raw || xmlStrcmp(raw, BAD_CAST "true"))) ||
                         (raw_expected != 1 && raw && xmlStrcmp(raw, BAD_CAST "false")))
                    result = fail(c, "Unexpected Firehose rawmode state");
                else result = 0;
                xmlFree(v); xmlFree(raw);
                if (!result && configure) {
                    const char *attrs[] = { "MaxPayloadSizeToTargetInBytes", "MaxPayloadSizeToTargetInBytesSupported" };
                    bool found = false;
                    for (size_t i = 0; i < 2; i++) {
                        xmlChar *p = xmlGetProp(n, BAD_CAST attrs[i]);
                        if (p) {
                            uint64_t payload;
                            if (!number((char *)p, &payload) || payload < PAGE || payload > 1024 * 1024 || payload % PAGE)
                                result = fail(c, "Invalid negotiated Firehose payload bound");
                            else if (!found || payload < c->payload) c->payload = payload;
                            found = true;
                            xmlFree(p);
                        }
                    }
                    if (!found) result = fail(c, "Missing negotiated Firehose payload bound");
                }
                if (result < 0) break;
            } else { result = fail(c, "Unexpected Firehose XML element"); break; }
        }
        xmlFreeDoc(doc);
        if (result <= 0) return result;
    }
    return fail(c, "Excessive Firehose XML log documents");
}
static int exclusive(struct client *c, const char *name)
{
    int fd = openat(c->dir, name, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) fail(c, "Cannot create %s exclusively: %s", name, strerror(errno));
    return fd;
}
static int read_range(struct client *c, uint64_t start, uint64_t length,
                      const char *name, unsigned char *copy, char hash[65])
{
    char cmd[512];
    uint64_t received = 0;
    int fd = exclusive(c, name);
    SHA2_CTX sha;
    if (fd < 0) return -1;
    SHA256Init(&sha);
    snprintf(cmd, sizeof(cmd), "<?xml version=\"1.0\"?><data><read SECTOR_SIZE_IN_BYTES=\"%" PRIu64 "\" num_partition_sectors=\"%" PRIu64 "\" physical_partition_number=\"0\" start_sector=\"%" PRIu64 "\" PAGES_PER_BLOCK=\"%" PRIu64 "\"/></data>", c->page, length/c->page, start/c->page, c->erase/c->page);
    printf("Reading %s: %" PRIu64 " bytes\n", name, length); fflush(stdout);
    if (send_xml(c, cmd) || response(c, 1, false, false)) goto bad;
    while (received < length) {
        if (fill(c, now_ms() + CKB01_IO_TIMEOUT_MS)) goto bad;
        size_t n = c->end - c->begin;
        if ((uint64_t)n > length - received) n = (size_t)(length - received);
        if (write_all(fd, c->buf + c->begin, n)) { fail(c, "Backup write failed: %s", strerror(errno)); goto bad; }
        SHA256Update(&sha, c->buf + c->begin, n);
        if (copy) memcpy(copy + received, c->buf + c->begin, n);
        c->begin += n; received += n;
    }
    if (response(c, 0, false, false)) goto bad;
    if (fsync(fd)) { fail(c, "Backup fsync failed: %s", strerror(errno)); goto bad; }
    if (close(fd)) return fail(c, "Backup close failed: %s", strerror(errno));
    unsigned char digest[32];
    SHA256Final(digest, &sha);
    for (size_t i = 0; i < sizeof(digest); i++) snprintf(hash + 2*i, 3, "%02x", digest[i]);
    printf("Completed %s: %" PRIu64 " bytes, SHA256 %s\n", name, received, hash); fflush(stdout);
    return 0;
bad:
    (void)fsync(fd); close(fd);
    return -1;
}
static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int validate_mibib(struct client *c, const unsigned char *b)
{
    const unsigned char *t = b + c->page;
    if (le32(b) != 0xFE569FAC || le32(b+4) != 0xCD7F127A || le32(b+8) != 4)
        return fail(c, "MIBIB header magic mismatch");
    if (le32(t) != 0x55EE73AA || le32(t+4) != 0xE35EBDDB || le32(t+8) != 4 || le32(t+12) != 27)
        return fail(c, "MIBIB SMEM magic/version/count mismatch");
    uint64_t count = le32(t+12);
    if (16 + count * 28 > c->page) return fail(c, "MIBIB entries exceed table page");
    json_object *entries = json_object_new_array();
    json_object_object_add(c->metadata, "mibib_entries", entries);
    unsigned found = 0;
    uint64_t starts[27], ends[27];
    for (uint64_t i = 0; i < count; i++) {
        const unsigned char *e = t + 16 + 28*i;
        char name[17]; memcpy(name, e, 16); name[16] = 0;
        uint64_t offset = le32(e+16), blocks = le32(e+20);
        /* 0xffffffff means remainder-of-device, not multiplication overflow. */
        if (!name[0] || offset >= c->blocks || !blocks ||
            (blocks != UINT32_MAX && blocks > c->blocks - offset) || e[27] != 0)
            return fail(c, "MIBIB entry has invalid NAND bounds/flash");
        if (blocks == UINT32_MAX) blocks = c->blocks - offset;
        starts[i] = offset; ends[i] = offset + blocks;
        for (uint64_t previous = 0; previous < i; previous++)
            if (starts[i] < ends[previous] && starts[previous] < ends[i])
                return fail(c, "MIBIB partition entries overlap");
        json_object *entry = json_object_new_object();
        json_object_object_add(entry, "name", json_object_new_string(name));
        json_object_object_add(entry, "start_bytes", json_object_new_uint64(offset*c->erase));
        json_object_object_add(entry, "length_bytes", json_object_new_uint64(blocks*c->erase));
        json_object_array_add(entries, entry);
        if (!strcmp(name, "efs2") || !strcmp(name, "0:efs2")) {
            found++;
            if (offset*c->erase != EFS_START || blocks*c->erase != EFS_LEN)
                return fail(c, "EFS2 partition geometry mismatch");
        }
    }
    if (found != 1) return fail(c, "MIBIB must contain exactly one EFS2 entry");
    return 0;
}
/* Linux renameat2 supports FAT as well as ext4 without replacing a destination.
 * Older kernels fall back to exclusive link+unlink on filesystems with links. */
static int publish(struct client *c, const char *from, const char *to)
{
#ifdef SYS_renameat2
    if (!syscall(SYS_renameat2, c->dir, from, c->dir, to, RENAME_NOREPLACE)) return 0;
    if (errno != ENOSYS && errno != EINVAL && errno != EOPNOTSUPP)
        return fail(c, "Cannot publish %s exclusively: %s", to, strerror(errno));
#endif
    if (linkat(c->dir, from, c->dir, to, 0)) return fail(c, "Cannot publish %s exclusively: %s", to, strerror(errno));
    if (unlinkat(c->dir, from, 0)) return fail(c, "Cannot remove partial name: %s", strerror(errno));
    return 0;
}
int main(int argc, char **argv)
{
    const char *device = NULL, *output = NULL;
    struct client c = { .dev = -1, .dir = -1, .log = -1, .report = -1 };
    int rc = 1;
    unsigned char *mibib = NULL;
    char hash1[65], hash2[65], mhash[65], cmd[512];
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--device") && i+1 < argc && !device) device = argv[++i];
        else if (!strcmp(argv[i], "--output") && i+1 < argc && !output) output = argv[++i];
        else { fprintf(stderr, "Usage: %s --device PATH --output EXISTING-UNIQUE-DIRECTORY\n", argv[0]); return 2; }
    }
    if (!device || !output) { fprintf(stderr, "--device and --output are required\n"); return 2; }
    c.metadata = json_object_new_object(); c.storage = json_object_new_object(); c.logs = json_object_new_array();
    json_object_object_add(c.metadata, "storage", c.storage);
    json_object_object_add(c.metadata, "programmer_logs", c.logs);
    json_object_object_add(c.metadata, "transport_complete", json_object_new_boolean(false));
    json_object_object_add(c.metadata, "backup_scope", json_object_new_string("NAND ECC-corrected main data only; no OOB"));
    json_object_object_add(c.metadata, "bad_block_policy", json_object_new_string("unreported; retained programmer logs may provide details"));
    json_object_object_add(c.metadata, "restoration_verified", json_object_new_boolean(false));
    c.dir = open(output, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (c.dir < 0) { fail(&c, "Cannot open output directory: %s", strerror(errno)); goto done; }
    const char *names[] = { "firehose.xml.log", "report.json", "mibib.bin.partial", "mibib.bin", "efs2-pass1.bin.partial", "efs2-pass2.bin.partial", "efs2-pass1.bin", "efs2-pass2.bin" };
    for (size_t i = 0; i < sizeof(names)/sizeof(names[0]); i++) {
        struct stat st;
        if (!fstatat(c.dir, names[i], &st, AT_SYMLINK_NOFOLLOW) || errno != ENOENT) {
            fail(&c, "Output name already exists or cannot be checked: %s", names[i]); goto done;
        }
    }
    c.report = exclusive(&c, "report.json"); if (c.report < 0) goto done;
    c.log = exclusive(&c, "firehose.xml.log"); if (c.log < 0) goto done;
    struct statvfs space;
    const uint64_t required = 2 * EFS_LEN + UINT64_C(16) * 1024 * 1024;
    if (fstatvfs(c.dir, &space) || !space.f_frsize) {
        fail(&c, "Cannot determine available output space"); goto done;
    }
    json_object_object_add(c.metadata, "required_free_bytes", json_object_new_uint64(required));
    if ((uint64_t)space.f_bavail < required/(uint64_t)space.f_frsize + (required%(uint64_t)space.f_frsize != 0)) {
        fail(&c, "Insufficient free output space for two EFS2 passes and logs"); goto done;
    }
    c.dev = open(device, O_RDWR | O_NONBLOCK | O_NOCTTY | O_NOFOLLOW | O_CLOEXEC);
    if (c.dev < 0) { fail(&c, "Cannot open Firehose device: %s", strerror(errno)); goto done; }
    struct stat st;
    if (fstat(c.dev, &st) || !S_ISCHR(st.st_mode)) { fail(&c, "Firehose device must be a character device"); goto done; }
    /* WWAN nodes have no termios interface; PTY host fixtures do. */
    struct termios tty;
    if (!tcgetattr(c.dev, &tty)) { cfmakeraw(&tty); if (tcsetattr(c.dev, TCSANOW, &tty)) { fail(&c, "Cannot set raw transport"); goto done; } }
    snprintf(cmd, sizeof(cmd), "<?xml version=\"1.0\"?><data><configure MemoryName=\"nand\" MaxPayloadSizeToTargetInBytes=\"16384\" Verbose=\"0\" ZlpAwareHost=\"1\" SkipStorageInit=\"0\"/></data>");
    if (send_xml(&c, cmd) || response(&c, -1, false, true)) goto done;
    json_object_object_add(c.metadata, "negotiated_payload_bytes", json_object_new_uint64(c.payload));
    if (send_xml(&c, "<?xml version=\"1.0\"?><data><getstorageinfo physical_partition_number=\"0\"/></data>") || response(&c, -1, true, false)) goto done;
    if (c.page != PAGE || c.erase != ERASE || !c.blocks || c.blocks > UINT64_MAX/c.erase || c.blocks*c.erase != TOTAL) {
        fail(&c, "Missing, ambiguous or mismatching programmer NAND geometry"); goto done;
    }
    json_object_object_add(c.storage, "total_bytes", json_object_new_uint64(c.blocks*c.erase));
    json_object_object_add(c.storage, "pages_per_block", json_object_new_uint64(c.erase/c.page));
    mibib = malloc((size_t)c.erase);
    if (!mibib) { fail(&c, "MIBIB allocation failed"); goto done; }
    if (read_range(&c, MIBIB, c.erase, "mibib.bin.partial", mibib, mhash)) goto done;
    json_object_object_add(c.metadata, "mibib_sha256", json_object_new_string(mhash));
    if (validate_mibib(&c, mibib) || publish(&c, "mibib.bin.partial", "mibib.bin")) goto done;
    if (read_range(&c, EFS_START, EFS_LEN, "efs2-pass1.bin.partial", NULL, hash1)) goto done;
    json_object_object_add(c.metadata, "pass1_sha256", json_object_new_string(hash1));
    if (read_range(&c, EFS_START, EFS_LEN, "efs2-pass2.bin.partial", NULL, hash2)) goto done;
    json_object_object_add(c.metadata, "pass2_sha256", json_object_new_string(hash2));
    if (strcmp(hash1, hash2)) { fail(&c, "EFS2 independent pass SHA256 mismatch"); goto done; }
    if (fsync(c.log)) { fail(&c, "XML log fsync failed: %s", strerror(errno)); goto done; }
    if (publish(&c, "efs2-pass1.bin.partial", "efs2-pass1.bin") || publish(&c, "efs2-pass2.bin.partial", "efs2-pass2.bin")) goto done;
    if (fsync(c.dir)) { fail(&c, "Output directory fsync failed: %s", strerror(errno)); goto done; }
    json_object_object_add(c.metadata, "efs2_length_bytes", json_object_new_uint64(EFS_LEN));
    json_object_object_add(c.metadata, "transport_complete", json_object_new_boolean(true));
    rc = 0;
done:
    if (c.error[0]) json_object_object_add(c.metadata, "error", json_object_new_string(c.error));
    if (c.report >= 0) {
        const char *s = json_object_to_json_string_ext(c.metadata, JSON_C_TO_STRING_PRETTY);
        if (write_all(c.report, s, strlen(s)) || write_all(c.report, "\n", 1) || fsync(c.report)) { fprintf(stderr, "Report write failed: %s\n", strerror(errno)); rc = 1; }
        if (close(c.report)) rc = 1;
    }
    if (c.log >= 0) { if (fsync(c.log) || close(c.log)) rc = 1; }
    if (c.dev >= 0) close(c.dev);
    if (c.dir >= 0) close(c.dir);
    free(mibib); json_object_put(c.metadata); xmlCleanupParser();
    return rc;
}
