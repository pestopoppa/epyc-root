/* PROPOSED, NOT BUILT. Private per-Node preload, installed Ladybug stays intact.
 * ABI: @ladybugdb/core 0.17.1 x86_64 GNU C++ SystemConfig C1/C2 only.
 * The supervisor must verify the native ELF digest before starting this image.
 * Never interpose hardware_concurrency/get_nprocs or change kernel affinity.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#if !defined(__x86_64__) || __SIZEOF_POINTER__ != 8 || __SIZEOF_LONG__ != 8
#error "reviewed SystemConfig ABI is x86_64 LP64 only"
#endif

#define NATIVE "/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/gitnexus/node_modules/@ladybugdb/core/lbugjs.node"
#define C1 "_ZN4lbug4main12SystemConfigC1Emmbbmbmbbbbb"
#define C2 "_ZN4lbug4main12SystemConfigC2Emmbbmbmbbbbb"
typedef void (*config_ctor)(void *, uint64_t, uint64_t, bool, bool,
    uint64_t, bool, uint64_t, bool, bool, bool, bool, bool);

static void refuse(void) {
    static const char message[] = "gitnexus native constructor cap refused\n";
    const ssize_t written = write(STDERR_FILENO, message, sizeof(message) - 1);
    if (written != (ssize_t)(sizeof(message) - 1)) _exit(64);
    _exit(64);
}

static void cap(const char *symbol, void *caller, void *self, uint64_t buffer,
    uint64_t threads, bool compression, bool readonly, uint64_t maxdb,
    bool checkpoint, uint64_t threshold, bool wal, bool checksums,
    bool flag3, bool flag4, bool hashindex) {
    Dl_info origin = {0}, caller_info = {0};
    void *address = dlsym(RTLD_NEXT, symbol);
    if (!address || !dladdr(address, &origin) || !origin.dli_fname ||
        strcmp(origin.dli_fname, NATIVE) != 0 ||
        !dladdr(caller, &caller_info) || !caller_info.dli_fname ||
        strcmp(caller_info.dli_fname, NATIVE) != 0) refuse();
    config_ctor original;
    _Static_assert(sizeof(original) == sizeof(address), "x86_64 function pointer ABI");
    memcpy(&original, &address, sizeof(original));
    original(self, buffer, 1, compression, readonly, maxdb, checkpoint,
        threshold, wal, checksums, flag3, flag4, hashindex);
    /* Installed ELF proves SystemConfig's second u64 field is maxNumThreads.
     * Read back what the original constructor wrote; fail before DB init.
     */
    uint64_t observed;
    memcpy(&observed, (const char *)self + 8, sizeof(observed));
    if (observed != 1) refuse();
    char event[256];
    int length = snprintf(event, sizeof(event),
        "GNX_NATIVE_CAP pid=%ld requested=%llu applied=1 observed=%llu\n",
        (long)getpid(), (unsigned long long)threads, (unsigned long long)observed);
    if (length <= 0 || (size_t)length >= sizeof(event) ||
        write(STDERR_FILENO, event, (size_t)length) != length) refuse();
}

#define ARGS void *self, uint64_t buffer, uint64_t threads, bool compression, \
    bool readonly, uint64_t maxdb, bool checkpoint, uint64_t threshold, \
    bool wal, bool checksums, bool flag3, bool flag4, bool hashindex
#define FORWARD self, buffer, threads, compression, readonly, maxdb, \
    checkpoint, threshold, wal, checksums, flag3, flag4, hashindex
void ctor1(ARGS) __asm__(C1);
void ctor2(ARGS) __asm__(C2);
void ctor1(ARGS) { cap(C1, __builtin_return_address(0), FORWARD); }
void ctor2(ARGS) { cap(C2, __builtin_return_address(0), FORWARD); }
