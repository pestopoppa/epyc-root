// INF-70 HARNESS-1: targeted page-cache tool.
//   pagecache measure <file>...      -> per-file resident bytes, measured with mincore(2)
//   pagecache drop    <file>...      -> POSIX_FADV_DONTNEED, then RE-MEASURE with mincore(2)
//
// The syscall's return value proves nothing: POSIX_FADV_DONTNEED is advisory and only evicts
// CLEAN pages, so the only honest evidence is a before/after residency count of the mapping.
// mincore() reports, page by page, whether that page of the file is in the page cache.
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static long PS;

// resident bytes of `path` according to mincore(); -1 on error
static long long resident(const char * path, long long * total) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size == 0) { close(fd); return -1; }
    *total = st.st_size;
    long long res = 0;
    const size_t CHUNK = (size_t)1 << 30;           // 1 GiB windows: vec stays 256 KiB
    unsigned char * vec = malloc(CHUNK / PS + 1);
    if (!vec) { close(fd); return -1; }
    for (long long off = 0; off < st.st_size; off += (long long)CHUNK) {
        size_t len = (size_t)((st.st_size - off) < (long long)CHUNK ? (st.st_size - off) : (long long)CHUNK);
        void * m = mmap(NULL, len, PROT_READ, MAP_SHARED, fd, off);   // maps, does NOT fault in
        if (m == MAP_FAILED) { free(vec); close(fd); return -1; }
        size_t npages = (len + PS - 1) / PS;
        if (mincore(m, len, vec) == 0) {
            for (size_t i = 0; i < npages; i++) if (vec[i] & 1) res += PS;
        }
        munmap(m, len);
    }
    free(vec); close(fd);
    return res;
}

int main(int argc, char ** argv) {
    PS = sysconf(_SC_PAGESIZE);
    if (argc < 3) { fprintf(stderr, "usage: pagecache measure|drop <file>...\n"); return 2; }
    const int do_drop = strcmp(argv[1], "drop") == 0;
    long long sum_before = 0, sum_after = 0;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int i = 2; i < argc; i++) {
        long long total = 0;
        long long before = resident(argv[i], &total);
        if (before < 0) { printf("SKIP    %s (unreadable/empty)\n", argv[i]); continue; }
        long long after = before;
        if (do_drop) {
            int fd = open(argv[i], O_RDONLY);
            if (fd >= 0) {
                // rc is reported but is NOT the evidence -- the re-measure below is.
                int rc = posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
                close(fd);
                if (rc != 0) printf("WARN    %s fadvise rc=%d\n", argv[i], rc);
            }
            after = resident(argv[i], &total);
            if (after < 0) after = 0;
        }
        sum_before += before; sum_after += after;
        printf("%-7s %10.3f GiB -> %10.3f GiB resident of %10.3f GiB  %s\n",
               do_drop ? "DROP" : "MEASURE",
               before / 1073741824.0, after / 1073741824.0, total / 1073741824.0, argv[i]);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("TOTAL   resident_before=%.3f GiB resident_after=%.3f GiB freed=%.3f GiB elapsed=%.2fs\n",
           sum_before / 1073741824.0, sum_after / 1073741824.0,
           (sum_before - sum_after) / 1073741824.0, el);
    return 0;
}
