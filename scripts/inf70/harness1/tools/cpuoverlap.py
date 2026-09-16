#!/usr/bin/env python3
"""INF-70 HARNESS-1: classify a foreign process's CPU affinity against the bench region.

FIXES A MISLABEL inherited from champion1/arm.sh and propagated through champion3.
The old test was `any cpu id <= 95`, which reports cpus **184-191 as
"disjoint-from-0-95"**. They are not disjoint from anything: they are the SMT SIBLINGS of
physical cores 88-95, which are IN the bench region. A process pinned there competes for
the same physical cores, the same L1/L2 and the same execution ports as the arm.

That label was load-bearing and wrong: a contention escalation was retracted on its
authority, and CHAMPION-3 measured a REAL effect from that lane -- absolutes ~7% below the
anchor while it was live. An agent trusting "disjoint" would dismiss exactly that signal.

The sibling relation is read from /sys topology (thread_siblings_list), never assumed to be
`+96`: an assumed offset is the same class of error as the label it replaces.

  usage: cpuoverlap.py <Cpus_allowed_list> [bench_cpu_list]      default bench = 0-95
  emits exactly one of: DIRECT-OVERLAP  SMT-SIBLING-CONTENTION  DISJOINT-FROM-BENCH-CORES
"""
import sys, os

def parse(spec):
    out = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a, b = part.split("-")[:2]
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out

def core_of(cpu, _cache={}):
    """The physical core key of a logical cpu: its thread-sibling set, straight from /sys."""
    if cpu in _cache: return _cache[cpu]
    p = f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list"
    try:
        sibs = frozenset(parse(open(p).read().strip()))
    except OSError:
        sibs = frozenset({cpu})          # no topology: the cpu is its own core
    for s in sibs: _cache[s] = sibs
    return sibs

def fmt(cpus):
    cpus = sorted(cpus)
    if not cpus: return "-"
    runs, s, p = [], cpus[0], cpus[0]
    for c in cpus[1:]:
        if c == p + 1: p = c; continue
        runs.append((s, p)); s = p = c
    runs.append((s, p))
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)

def classify(allowed, bench):
    cpus  = parse(allowed)
    bench = parse(bench)
    direct = cpus & bench
    bench_cores = set()
    for c in bench: bench_cores |= {core_of(c)}
    sib_cpus, sib_bench = set(), set()
    for c in cpus - bench:
        k = core_of(c)
        if k in bench_cores:
            sib_cpus.add(c); sib_bench |= (set(k) & bench)
    if direct:
        return ("DIRECT-OVERLAP", f"DIRECT-OVERLAP on {fmt(direct)}"
                + (f" +SMT-siblings {fmt(sib_cpus)} of {fmt(sib_bench)}" if sib_cpus else ""))
    if sib_cpus:
        return ("SMT-SIBLING-CONTENTION",
                f"SMT-SIBLING-CONTENTION: {fmt(sib_cpus)} are the SMT siblings of bench cores "
                f"{fmt(sib_bench)} (shares physical cores, NOT disjoint)")
    return ("DISJOINT-FROM-BENCH-CORES", "DISJOINT-FROM-BENCH-CORES")

if __name__ == "__main__":
    if sys.argv[1] == "--selftest":
        bench = "0-95"
        for spec, want in [("184-191", "SMT-SIBLING-CONTENTION"), ("0-95", "DIRECT-OVERLAP"),
                           ("88-95",  "DIRECT-OVERLAP"),          ("96-183", "SMT-SIBLING-CONTENTION"),
                           ("0-191",  "DIRECT-OVERLAP"),          ("48-95",  "DIRECT-OVERLAP")]:
            got, msg = classify(spec, bench)
            ok = "ok " if got == want else "FAIL"
            print(f"  {ok} {spec:<10} -> {got:<26} {msg}")
            if got != want: sys.exit(1)
        print("  CPUOVERLAP SELFTEST OK")
        sys.exit(0)
    print(classify(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "0-95")[1])
