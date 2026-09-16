import mmap, os, sys, time
n = int(sys.argv[1]) << 30 if len(sys.argv) > 1 else 2 << 30
m = mmap.mmap(-1, n, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
t0 = time.time()
step = 4096
for off in range(0, n, step):
    m[off] = 1
t1 = time.time()
tot = {}
for line in open('/proc/self/numa_maps'):
    if 'anon=' not in line:
        continue
    f = line.split()
    pages = 0
    for p in f:
        if p.startswith('N') and '=' in p and p[1].isdigit():
            k, v = p.split('='); pages = int(v)
            if pages > 1000:
                tot[k] = tot.get(k, 0) + pages
    # pick the big mapping only
big = {k: v for k, v in tot.items()}
print(f"touched {n>>20} MiB in {t1-t0:.2f}s; anon pages per node (mappings >1000 pages):", {k: f"{v*4/1024:.0f} MiB" for k, v in sorted(big.items())})
