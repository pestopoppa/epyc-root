#!/usr/bin/env python3
"""preflight.py - deterministic row pre-flight checks for every owner's rows (D9-ack, operator 2026-11-24, "Approve, WARN first").

Run from publish_row.py (after the D9 lint, before anything is published) and from the allocator just before a row's grant
is written (only the checks that can drift since publish: DRIFT_CHECKS). Static only: file stats, SHA256SUMS, `strings`,
GGUF headers, AST. No model loads, no GPU, no compute; seconds per row (the `strings` sets and the store verification are
cached per store SHA256SUMS digest under <flags>/preflight-cache/).

WARN FIRST: every check reports a raw level (FAIL = the row would fail it, WARN = advisory). A raw FAIL only refuses
(publish) or holds the grant (allocator) when PREFLIGHT_ENFORCE[check] is True. All start False. Flip one only when
`rowflow.py preflight --report` (or `preflight.py --report`) shows zero currently queued rows fail it.

Checks (AutoKernel spec 2026-11-24, items 1-10):
  selftest  1  job.py has a --selftest handler (all owners) and the D9 lint reports 0 FAIL (ak_row_lint, static part;
               publish_row's lint already runs the selftest itself)
  store     2  every kernel store / model path in the row's code exists; the store's SHA256SUMS verify; BUILD-IDENTITY
               source_sha matches the declared commit (spec kernel_store.source_sha / source_sha, else the store name's sha)
  flags     3  every server CLI flag in a llama-server argv appears in the store's llama-server strings; every
               GGML_/LLAMA_ env knob the row sets appears in the strings of that store's libs (in no store = FAIL)
  model     4  the row's declared model (id + spec.model) agrees with the GGUFs in its argv (size tokens 27b, a3b, ...)
  lane      5  taskset/numactl placement vs the NUMA node map; -t vs declared_threads and the pinned cpus; model bytes vs
               node / host RAM; GPU model + KV vs VRAM; concurrent streams under --interleave=all (c21-cpu-r2)
  smoke     6  the smoke writes smoke_measure.json where the keeper reads it (end_smoke, smoke_measure_paths()); no stale
               out/ or out-smoke/ artefacts (ak_row_lint smoke_checks + stale_out, every owner)
  estimate  7  estimate_s = units x measured unit_s (+ loads) x margin from a real smoke or a predecessor; a borrowed
               basis whose source row differs in model or shape fails; > 3x off warns
  ports     8  declared ports are unique across queued rows
  append    9  results are appended per unit (append-mode writes / ledger helper), not written once per group
  witness  10  a verdict that rests on a debug/log line declares it in spec.witness_lines [{line, needs, cap}]; the line
               must be in the store's strings and needs <= cap (gvfattn-served-r2: an 8-line debug cap)

Usage: preflight.py <row_dir|spec.json> [...]   |   preflight.py --report [--flags DIR] [--json]
"""
import ast
import glob
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:   # the keeper runs `python3 -I`
    sys.path.insert(0, _HERE)

CHECKS = ("selftest", "store", "flags", "model", "lane", "smoke", "estimate", "ports", "append", "witness")
# THE switch (operator 2026-11-24): one entry per check; True = a raw FAIL refuses/holds. All start False (WARN for everyone).
PREFLIGHT_ENFORCE = {c: False for c in CHECKS}
DRIFT_CHECKS = ("store", "flags", "lane", "smoke", "ports", "witness")   # re-run at grant time (code is sealed at publish)

_LLM = "/mnt/raid0/llm/"
TMP_ROOT = _LLM + "tmp"
STORE_RX = re.compile(r"(/(?:[A-Za-z0-9._+-]+/)*kernels/(?:builds|production|candidates|experimental|quarantine)/[A-Za-z0-9._+-]+)")
TREE_BUILD_RX = re.compile(re.escape(_LLM) + r"llama\.cpp/build(?:-hip)?/bin")
GGUF_RX = re.compile(r"(/[^\s\"'`,;:)\]}{$]+?\.gguf)\b")
SHARD_RX = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$")
KNOB_SET_RX = (re.compile(r"[\"']((?:GGML|LLAMA)_[A-Z0-9_]{2,})[\"']\s*:"),          # env dict {"GGML_X": ...}
               re.compile(r"(?<![A-Za-z0-9_])((?:GGML|LLAMA)_[A-Z0-9_]{2,})=(?!=)"),   # GGML_X=1 (sh / prose argv)
               re.compile(r"env\[\s*[\"']((?:GGML|LLAMA)_[A-Z0-9_]{2,})[\"']\s*\]\s*="),
               re.compile(r"setdefault\(\s*[\"']((?:GGML|LLAMA)_[A-Z0-9_]{2,})[\"']"))
SIZE_TOK_RX = re.compile(r"(?<![0-9.])(a?\d+(?:\.\d+)?b)(?![a-z0-9])")   # gpu27b -> 27b; a3b; 0.6b
WITNESS_DEP_RX = re.compile(r"\w+_DEBUG=1|\bdebug\b[^.\n]{0,80}\b(?:lines?|prints?|logs?)\b|"
                            r"\b(?:logs?|logged|prints?)\b[^.\n]{0,60}\blines?\b", re.I)
CONCURRENT_RX = re.compile(r"\bconcurrent|\bstreams\b|\bin parallel\b|\bparallel (?:paired|streams|quarters)", re.I)
ROWID_RX = re.compile(r"\b([a-z][a-z0-9.]*(?:-[a-z0-9.]+)*-20\d{6}(?:-[a-z0-9]+)*)\b")
WRAPPER_FLAGS = {"--interleave", "--membind", "--cpunodebind", "--physcpubind", "--preferred", "--localalloc",
                 "--selftest", "-c", "-n", "-N"}
OTHER_TOOLS_RX = re.compile(r"llama-(?:perplexity|bench|cli|batched-bench|quantize|imatrix|completion|fit-params)|"
                            r"test-backend-ops|\bgit\b|cmake|\bmake\b|\bcurl\b|rocm-smi|sha256sum|gcc|python|bench_readbw|\btbo\b")
KV_BYTES = {"f32": 4.0, "f16": 2.0, "bf16": 2.0, "q8_0": 34 / 32, "q5_0": 22 / 32, "q5_1": 24 / 32, "q4_0": 18 / 32,
            "q4_1": 20 / 32, "iq4_nl": 18 / 32}
HYBRID_MIN_THREADS = 8      # <= this many host threads under expert offload (--n-cpu-moe / -ot ...=CPU): WARN
EST_OFF_X = 3.0
DEFAULT_VRAM_GIB = 64.0     # MI210


# ---------------------------------------------------------------- small helpers
def _read(p, limit=8 << 20):
    try:
        with open(p, errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def _load_json(p):
    try:
        with open(p) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_cpus(s):
    out = []
    for t in str(s or "").split(","):
        t = t.strip()
        if re.fullmatch(r"\d+-\d+", t):
            a, b = t.split("-")
            out += range(int(a), int(b) + 1)
        elif t.isdigit():
            out.append(int(t))
    return out


def node_map(sysfs="/sys/devices/system/node"):
    """{node: set(cpus)} and {node: MemTotal bytes} from sysfs."""
    cpus, mem = {}, {}
    for p in sorted(glob.glob(os.path.join(sysfs, "node[0-9]*"))):
        n = int(os.path.basename(p)[4:])
        cpus[n] = set(parse_cpus(_read(os.path.join(p, "cpulist")).strip()))
        m = re.search(r"MemTotal:\s+(\d+)\s*kB", _read(os.path.join(p, "meminfo")))
        if m:
            mem[n] = int(m.group(1)) * 1024
    return cpus, mem


def host_mem_bytes():
    m = re.search(r"MemTotal:\s+(\d+)\s*kB", _read("/proc/meminfo"))
    return int(m.group(1)) * 1024 if m else 0


def vram_bytes():
    best = 0
    for p in glob.glob("/sys/class/drm/card*/device/mem_info_vram_total"):
        try:
            best = max(best, int(_read(p).strip() or 0))
        except ValueError:
            pass
    return best or int(DEFAULT_VRAM_GIB * (1 << 30))


def region_cpus(regions):
    out = set()
    for t in str(regions or "").split(","):
        t = t.strip()
        if re.fullmatch(r"q[0-3]", t):
            lo = int(t[1]) * 24
            out |= set(range(lo, lo + 24)) | set(range(lo + 96, lo + 120))
        elif re.fullmatch(r"\d+(-\d+)?", t):
            out |= set(parse_cpus(t))
    return out


class Row:
    """Everything the checks read about one row: spec (manifest or spec.json), dir, own code, all text."""

    def __init__(self, spec, row_dir=None):
        self.spec = dict(spec or {})
        lp = self.spec.get("launcher")
        lp = lp.get("path") if isinstance(lp, dict) else lp
        self.dir = row_dir or (os.path.dirname(os.path.abspath(lp)) if lp else self.spec.get("scratch_root") or "")
        self.id = str(self.spec.get("id") or os.path.basename(os.path.normpath(self.dir)))
        self.code, self.sh = {}, {}
        try:
            names = sorted(os.listdir(self.dir)) if self.dir else []
        except OSError:
            names = []
        for f in names:
            if f.endswith(".py") and f not in ("ak_row_harness.py",):
                self.code[f] = _read(os.path.join(self.dir, f))
            elif f.endswith(".sh"):
                self.sh[f] = _read(os.path.join(self.dir, f))
        self.prose = " ".join(str(self.spec.get(k) or "") for k in
                              ("decision_rule", "notes", "smoke_note", "rule", "width_justification", "shape_justification",
                               "model_recipe", "threads_evidence"))
        self.codetext = "\n".join(list(self.code.values()) + list(self.sh.values()))

    @property
    def owner(self):
        return str(self.spec.get("owner") or "")


# ---------------------------------------------------------------- argv extraction (static)
def _const_list(node):
    out = []
    for e in node.elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, (str, int, float)):
            out.append(str(e.value))
        else:
            out.append("<expr>")
    return out


def server_argvs(row):
    """Static llama-server argv fragments: python list/tuple literals with flag constants in files that start a server,
    plus shell lines that name llama-server. Lists naming another tool are skipped."""
    out = []
    for f, t in row.code.items():
        if "llama-server" not in t and "llama_server" not in t:
            continue
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.List, ast.Tuple)) and n.elts:
                a = _const_list(n)
                if not any(x.startswith("-") and len(x) > 1 and not re.fullmatch(r"-[\d.]+", x) for x in a):
                    continue
                if any(OTHER_TOOLS_RX.search(x) for x in a if not x.startswith("-")):
                    continue
                out.append((f, n.lineno, a))
    for f, t in row.sh.items():
        for i, l in enumerate(re.sub(r"\\\n", " ", t).splitlines(), 1):
            if "llama-server" in l and not l.lstrip().startswith("#"):
                out.append((f, i, l.split("llama-server", 1)[1].split()))
    return out


def argv_flags(argvs):
    fl = set()
    for _f, _ln, a in argvs:
        for x in [t for y in a for t in str(y).split()]:
            if x.startswith("-") and len(x) > 1 and not re.fullmatch(r"-[\d.]+", x):
                x = x.split("=", 1)[0]
                if x not in WRAPPER_FLAGS and not x.startswith("-D") and ":" not in x:
                    fl.add(x)
    return fl


def argv_value(argvs, *names):
    vals = []
    for _f, _ln, a in argvs:
        a = [t for y in a for t in str(y).split()]
        for i, x in enumerate(a[:-1]):
            if x in names:
                vals.append(a[i + 1])
    return vals


# ---------------------------------------------------------------- store cache (per SHA256SUMS digest)
def _cache_dir(flags):
    d = os.environ.get("PREFLIGHT_CACHE") or os.path.join(flags, "preflight-cache")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return None
    return d


def store_key(root):
    m = store_manifest(root)
    if not m:
        return hashlib.sha256(("nosums:" + os.path.realpath(root)).encode()).hexdigest()
    try:
        return _sha256(m)
    except OSError:
        return None


def _cache_get(flags, key, name):
    d = _cache_dir(flags) if flags else None
    return _load_json(os.path.join(d, f"{key}.{name}.json")) if d and key else None


def _cache_put(flags, key, name, value):
    d = _cache_dir(flags) if flags else None
    if not (d and key):
        return
    p = os.path.join(d, f"{key}.{name}.json")
    try:
        with open(p + f".tmp{os.getpid()}", "w") as f:
            json.dump(value, f)
        os.replace(p + f".tmp{os.getpid()}", p)
    except OSError:
        pass


def verify_store(root, flags=None):
    """[] when every SHA256SUMS entry verifies, else problem strings. Cached per digest + the entries' stat signature."""
    man = store_manifest(root) or os.path.join(root, "SHA256SUMS")
    try:
        lines = open(man, encoding="utf-8").read().splitlines()
    except (OSError, UnicodeError):
        return [f"{man} missing or unreadable"]
    key = store_key(root)
    ents, sig = [], []
    for ln in lines:
        m = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", ln)
        if not m:
            return [f"{man}: malformed entry {ln[:80]!r}"]
        p = os.path.join(root, m.group(2))
        try:
            st = os.stat(p)
        except OSError:
            return [f"{p} (in SHA256SUMS) is missing"]
        ents.append((p, m.group(1).lower()))
        sig.append(f"{m.group(2)}:{st.st_size}:{st.st_mtime_ns}:{st.st_ino}")
    sig_h = hashlib.sha256("\n".join(sig).encode()).hexdigest()
    c = _cache_get(flags, key, "verify")
    if c and c.get("sig") == sig_h:
        return list(c.get("bad") or [])
    bad = []
    for p, want in ents:
        try:
            if _sha256(p) != want:
                bad.append(f"{p} digest differs from SHA256SUMS")
        except OSError as e:
            bad.append(f"{p}: {e}")
    _cache_put(flags, key, "verify", {"sig": sig_h, "bad": bad, "root": root})
    return bad


def _strings(paths, n=2):
    out = []
    for p in paths:
        if os.path.isfile(p):
            try:
                out.append(subprocess.run(["strings", "-n", str(n), p], capture_output=True, text=True,
                                          timeout=60).stdout)
            except (OSError, subprocess.TimeoutExpired):
                pass
    return "\n".join(out)


def store_flags(root, flags=None):
    """Set of option tokens in the store's server binary + impl/common libs (tail-merged suffixes included), or None."""
    b = os.path.join(root, "bin")
    srv = os.path.join(b, "llama-server")
    if not os.path.isfile(srv):
        return None
    key = store_key(root)
    c = _cache_get(flags, key, "flags")
    if c and "flags" in c:
        return set(c["flags"])
    toks = set()
    for l in _strings([srv] + sorted(glob.glob(os.path.join(b, "libllama-server-impl.so"))) +
                      sorted(glob.glob(os.path.join(b, "libllama-common.so")))).splitlines():
        for i, ch in enumerate(l):   # every '-'-led suffix: the linker tail-merges "-ngl" into "--spec-draft-ngl"
            if ch == "-" and (i == 0 or l[i - 1] != "-"):
                tok = re.split(r"[\s,=<\[]", l[i:], 1)[0]
                if len(tok) > 1:
                    toks.add(tok)
    _cache_put(flags, key, "flags", {"flags": sorted(toks), "root": root})
    return toks


def _store_libs(root):
    b = os.path.join(root, "bin")
    libs = sorted({os.path.realpath(p) for p in glob.glob(os.path.join(b, "lib*.so*"))})
    return libs + ([os.path.join(b, "llama-server")] if os.path.isfile(os.path.join(b, "llama-server")) else [])


def store_knobs(root, flags=None):
    key = store_key(root)
    c = _cache_get(flags, key, "knobs")
    if c and "knobs" in c:
        return set(c["knobs"])
    k = set(re.findall(r"\b(?:GGML|LLAMA)_[A-Z0-9_]{2,}\b", _strings(_store_libs(root), 6)))
    _cache_put(flags, key, "knobs", {"knobs": sorted(k), "root": root})
    return k


def store_has_literal(root, literal, flags=None):
    key = store_key(root)
    lk = hashlib.sha256(literal.encode()).hexdigest()[:16]
    c = _cache_get(flags, key, f"lit-{lk}")
    if c and "has" in c:
        return bool(c["has"])
    has = literal in _strings(_store_libs(root), 4)
    _cache_put(flags, key, f"lit-{lk}", {"has": has, "literal": literal})
    return has


# ---------------------------------------------------------------- GGUF header (metadata only)
_GGUF_SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
_GGUF_MEMO = {}


def gguf_meta(path, want_prefixes=("general.", )):
    """Small dict of GGUF metadata (scalar keys, and int arrays as lists) or {} on any error. Reads the header only."""
    try:
        st = os.stat(path)
    except OSError:
        return {}
    k = (path, st.st_size, st.st_mtime_ns)
    if k in _GGUF_MEMO:
        return _GGUF_MEMO[k]
    out = {}
    try:
        with open(path, "rb") as f:
            rd = f.read

            def s():
                (n,) = struct.unpack("<Q", rd(8))
                return rd(n).decode("utf-8", "replace")

            def val(t):
                if t in _GGUF_SCALAR:
                    fmt = _GGUF_SCALAR[t]
                    return struct.unpack(fmt, rd(struct.calcsize(fmt)))[0]
                if t == 8:
                    return s()
                if t == 9:
                    (it,) = struct.unpack("<I", rd(4))
                    (n,) = struct.unpack("<Q", rd(8))
                    if it in _GGUF_SCALAR:
                        sz = struct.calcsize(_GGUF_SCALAR[it])
                        raw = rd(sz * n)
                        if n <= 4096:
                            return list(struct.unpack("<" + _GGUF_SCALAR[it][1] * n, raw))
                        return None
                    for _ in range(n):
                        val(it)
                    return None
                raise ValueError(f"gguf type {t}")
            if rd(4) != b"GGUF":
                return {}
            struct.unpack("<I", rd(4))
            _nt, nkv = struct.unpack("<QQ", rd(16))
            for _ in range(nkv):
                key = s()
                (t,) = struct.unpack("<I", rd(4))
                v = val(t)
                if v is not None and not isinstance(v, bytes):
                    out[key] = v
    except (OSError, ValueError, struct.error, MemoryError):
        pass
    _GGUF_MEMO[k] = out
    return out


def model_files(row):
    """{primary gguf path: [all shard paths]} for every absolute GGUF path in the row's code (not prose)."""
    out = {}
    for p in sorted(set(GGUF_RX.findall(row.codetext))):
        m = SHARD_RX.search(p)
        if m:
            n = int(m.group(2))
            first = SHARD_RX.sub(f"-00001-of-{m.group(2)}.gguf", p)
            out[first] = [SHARD_RX.sub(f"-{i:05d}-of-{m.group(2)}.gguf", p) for i in range(1, n + 1)]
        else:
            out[p] = [p]
    return out


def _bytes(paths):
    t = 0
    for p in paths:
        try:
            t += os.path.getsize(p)
        except OSError:
            pass
    return t


def store_root(path):
    """kernels/production/cpu -> builds/<store>/bin: the store is the parent of a bin/ link target."""
    real = os.path.realpath(path)
    return os.path.dirname(real) if os.path.basename(real) == "bin" else real


def stores_of(row):
    """Literal store roots in the row's code; a name still being formatted (`gpu-2026-{sha}`, `$X`) is skipped."""
    out = set()
    for m in STORE_RX.finditer(row.codetext):
        nxt = row.codetext[m.end():m.end() + 1]
        if m.group(1).endswith(("-", "_", ".")) or nxt in ("{", "$", "%"):
            continue
        out.add(m.group(1))
    return sorted(out)


def store_manifest(root):
    """SHA256SUMS, else the one tagged SHA256SUMS.<tag> (older stores), else None."""
    p = os.path.join(root, "SHA256SUMS")
    if os.path.isfile(p):
        return p
    tagged = sorted(glob.glob(os.path.join(root, "SHA256SUMS.*")))
    return tagged[0] if tagged else None


# ---------------------------------------------------------------- the checks: each returns [(level, code, msg)]
def check_selftest(row, ctx):
    out = []
    job = row.code.get("job.py")
    try:
        import ak_row_lint as LINT
    except ImportError:
        return [("WARN", "LINT-UNAVAILABLE", "ak_row_lint not importable")]
    if job is not None and LINT.selftest_missing(job):
        out.append(("FAIL", "SELFTEST-MISSING", "job.py has no `--selftest` argv handler that exits before main()"))
    if os.path.isdir(row.dir) and os.path.isfile(os.path.join(row.dir, "spec.json")):
        try:
            res = LINT.lint_dir(row.dir, selftest=ctx.get("run_selftest", False))
        except Exception as e:  # noqa: BLE001 - a lint crash is a finding, never a preflight crash
            res = [("FAIL", "LINT-CRASH", f"{type(e).__name__}: {e}")]
        fails = sorted({c for l, c, _m in res if l == "FAIL"} - {"SELFTEST-MISSING"})
        if fails:
            out.append(("FAIL", "LINT-FAIL", f"D9 lint reports FAIL: {', '.join(fails)}"))
    return out


def _declared_commit(row, root):
    ks = row.spec.get("kernel_store")
    if isinstance(ks, dict) and os.path.realpath(str(ks.get("path") or "")) == os.path.realpath(root) and ks.get("source_sha"):
        return str(ks["source_sha"]), "spec kernel_store.source_sha"
    for tok in os.path.basename(root).split("-"):
        if re.fullmatch(r"[0-9a-f]{7,40}", tok) and not re.fullmatch(r"\d{8}", tok):
            return tok, "store name"
    return None, None


def check_store(row, ctx):
    out = []
    if TREE_BUILD_RX.search(row.codetext):
        out.append(("WARN", "TREE-BUILD-PATH", "code reads llama.cpp/build*/bin: since v10 production serves from "
                                               "kernels/production/{cpu,gpu}; the tree's build dirs hold v9"))
    for root in stores_of(row):
        if not os.path.isdir(root):
            out.append(("FAIL", "STORE-MISSING", f"{root} does not exist"))
            continue
        real = store_root(root)
        if not store_manifest(real):
            out.append(("FAIL", "STORE-NO-SUMS", f"{root} has no SHA256SUMS"))
        else:
            bad = verify_store(real, ctx.get("flags"))
            if bad:
                out.append(("FAIL", "STORE-SUMS", f"{root}: {bad[0]}" + (f" (+{len(bad) - 1} more)" if len(bad) > 1 else "")))
        ident = _load_json(os.path.join(real, "BUILD-IDENTITY.json"))
        want, src = _declared_commit(row, root)
        if ident is None:
            out.append(("WARN", "STORE-NO-IDENTITY", f"{root} has no BUILD-IDENTITY.json; the commit is unproven"))
        elif want and not str(ident.get("source_sha") or "").startswith(want):
            out.append(("FAIL", "STORE-COMMIT", f"{root} BUILD-IDENTITY source_sha {str(ident.get('source_sha'))[:12]} != "
                                                f"{want} ({src})"))
    for first, shards in model_files(row).items():
        miss = [p for p in shards if not os.path.isfile(p)]
        if miss:
            out.append(("FAIL", "MODEL-MISSING", f"{miss[0]} does not exist" + (f" (+{len(miss) - 1})" if len(miss) > 1 else "")))
    return out


VENDORED = {"gpu_common.py", "gpuproof_row.py", "gpuproof.py", "lp_common.py", "base.py", "fold_row_guard.py"}


def _drop_test_funcs(t):
    """The source minus selftest/test function bodies (their fixture knobs are not the row's env)."""
    try:
        tree = ast.parse(t)
    except (SyntaxError, ValueError):
        return t
    drop = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and re.search(r"selftest|^_?test", n.name):
            drop |= set(range(n.lineno, (n.end_lineno or n.lineno) + 1))
    return "\n".join(l for i, l in enumerate(t.splitlines(), 1) if i not in drop)


def _declared_knobs(row):
    """Knobs the row's own code sets (vendored helpers' selftests are not the row's env)."""
    text = "\n".join([_drop_test_funcs(t) for f, t in row.code.items() if f not in VENDORED] + list(row.sh.values()))
    k = set()
    for rx in KNOB_SET_RX:
        k |= set(rx.findall(text))
    return k


def check_flags(row, ctx):
    out = []
    stores = [store_root(s) for s in stores_of(row) if os.path.isfile(os.path.join(store_root(s), "bin", "llama-server"))]
    fl = argv_flags(server_argvs(row))
    for root in stores:
        have = store_flags(root, ctx.get("flags"))
        if have is None:
            continue
        miss = sorted(f for f in fl if f not in have)
        if miss:
            out.append(("FAIL", "FLAG-UNKNOWN", f"server flag(s) {miss[:6]} not in {os.path.basename(root)}/bin/llama-server"))
    libstores = [store_root(s) for s in stores_of(row) if glob.glob(os.path.join(store_root(s), "bin", "libggml*.so*"))]
    if libstores:
        sets = {r: store_knobs(r, ctx.get("flags")) for r in libstores}
        for k in sorted(_declared_knobs(row)):
            if k.startswith(("GGML_CPU_", "GGML_CUDA_", "GGML_HIP_", "GGML_", "LLAMA_")) and not any(k in s for s in sets.values()):
                out.append(("FAIL", "KNOB-UNKNOWN", f"env knob {k} is in the strings of no store lib "
                                                    f"({', '.join(os.path.basename(r) for r in libstores)}): it does nothing"))
    return out


def _size_tokens(s):
    out = set()
    for w in re.split(r"[^a-z0-9.]+", s.lower()):
        if re.fullmatch(r"[0-9a-f]{7,}", w):
            continue   # a commit sha, not a model size
        out |= set(SIZE_TOK_RX.findall(w))
    return out


def check_model(row, ctx):
    files = model_files(row)
    if not files:
        return []
    names = " ".join(os.path.basename(p) for p in files)
    meta_names = " ".join(str(gguf_meta(p).get("general.name") or "") for p in files)
    have = _size_tokens(names + " " + meta_names)
    out = []
    for src, text in (("id", row.id), ("spec.model", str(row.spec.get("model") or ""))):
        want = _size_tokens(text) - {"0b"}
        miss = sorted(w for w in want if w not in have)
        if miss:
            out.append(("FAIL", "MODEL-DECLARED", f"{src} names {miss} but no GGUF in the row's argv does "
                                                  f"({', '.join(sorted(os.path.basename(p) for p in files))[:200]})"))
    return out


def check_lane(row, ctx):
    out = []
    ncpus, nmem = ctx.get("nodes") or node_map()
    text = row.codetext
    argvs = server_argvs(row)
    pinned = set()
    for m in re.finditer(r"taskset[\"',\s]+-c[\"',\s]+([0-9][0-9,\-]*)", text):
        pinned |= set(parse_cpus(m.group(1)))
    granted = region_cpus(row.spec.get("regions"))
    if pinned and granted and not pinned <= granted:
        out.append(("FAIL", "CPUS-OUTSIDE-GRANT", f"taskset cpus {sorted(pinned - granted)[:6]}... are outside regions "
                                                  f"{row.spec.get('regions')}"))
    cpus = pinned or granted
    membind = {int(x) for x in re.findall(r"--(?:membind|cpunodebind)[=\"',\s]+(\d+)\b", text)}
    for n in sorted(membind):
        if n in ncpus and cpus and not (cpus & ncpus[n]):
            out.append(("FAIL", "MEMBIND-REMOTE", f"numactl node {n} holds none of the pinned cpus: every access is remote"))
    nodes_used = {n for n, cs in ncpus.items() if cpus & cs}
    if (re.search(r"--interleave[=\"',\s]+all", text) and len(nodes_used) > 1
            and CONCURRENT_RX.search(row.prose + " " + text[:4000])):
        out.append(("FAIL", "INTERLEAVE-CONCURRENT", f"concurrent streams on nodes {sorted(nodes_used)} under numactl "
                                                     "--interleave=all draw every node's DRAM: the streams contend "
                                                     "(c21-cpu-r2); bind each stream to its node (--membind=q --cpunodebind=q)"))
    tvals = {int(v) for v in argv_value(argvs, "-t", "--threads") if v.isdigit()}
    dt = row.spec.get("declared_threads")
    if isinstance(dt, int) and tvals and max(tvals) != dt:
        out.append(("WARN", "THREADS-DECLARED", f"server -t {sorted(tvals)} != declared_threads {dt}"))
    if pinned and tvals and max(tvals) > len(pinned):
        out.append(("FAIL", "THREADS-OVERSUB", f"-t {max(tvals)} on {len(pinned)} pinned cpus"))
    offload = bool(re.search(r"--n-cpu-moe|--cpu-moe|exps=CPU|-ot[\"',\s]+[^\"'\n]*CPU", text))
    if offload and tvals and max(tvals) <= HYBRID_MIN_THREADS:
        out.append(("WARN", "HYBRID-THIN-HOST", f"expert offload to CPU (--n-cpu-moe/-ot CPU) with -t {max(tvals)}: the "
                                                "CPU experts run on that many threads; is this the cell you mean to measure?"))
    files = model_files(row)
    big = max((_bytes(s) for s in files.values()), default=0)
    if big:
        cap = sum(nmem[n] for n in membind if n in nmem) if membind else host_mem_bytes()
        if cap and big > cap:
            out.append(("FAIL", "RAM-FIT", f"largest model {big / 2**30:.0f} GiB > {'node' if membind else 'host'} RAM "
                                           f"{cap / 2**30:.0f} GiB"))
        rg = row.spec.get("ram_gib") or row.spec.get("gib")
        if isinstance(rg, (int, float)) and rg > 0 and big > rg * (1 << 30) and not offload and row.spec.get("lane") != "gpu":
            out.append(("WARN", "RAM-UNDERDECLARED", f"largest model {big / 2**30:.0f} GiB > declared ram {rg} GiB"))
    if row.spec.get("lane") == "gpu" and big and not offload:
        ngl = [v for v in argv_value(argvs, "-ngl", "--n-gpu-layers", "--gpu-layers") if v not in ("0",)]
        if ngl:
            kv = 0
            ctxs = [int(v) for v in argv_value(argvs, "-c", "--ctx-size") if v.isdigit()]
            ktypes = argv_value(argvs, "-ctk", "--cache-type-k") or ["f16"]
            primary = max(files, key=lambda p: _bytes(files[p]))
            md = gguf_meta(primary)
            arch = md.get("general.architecture")
            if arch and ctxs:
                L = int(md.get(f"{arch}.block_count") or 0)
                hk = md.get(f"{arch}.attention.head_count_kv") or 0
                if isinstance(hk, list):
                    L, hk = sum(1 for x in hk if x), max(hk or [0])
                kl = md.get(f"{arch}.attention.key_length") or (
                    (md.get(f"{arch}.embedding_length") or 0) // max(1, md.get(f"{arch}.attention.head_count") or 1))
                fai = md.get(f"{arch}.full_attention_interval")
                if isinstance(fai, int) and fai > 1:
                    L = L // fai
                kv = 2 * L * int(hk) * int(kl) * max(ctxs) * KV_BYTES.get(ktypes[0], 2.0)
            vr = ctx.get("vram") or vram_bytes()
            if big + kv > vr:
                out.append(("FAIL", "VRAM-FIT", f"model {big / 2**30:.1f} GiB + KV {kv / 2**30:.1f} GiB > VRAM {vr / 2**30:.0f} GiB"))
    return out


def check_smoke(row, ctx):
    try:
        import ak_row_lint as LINT
    except ImportError:
        return []
    out = []
    if not os.path.isdir(row.dir):
        return [("FAIL", "ROW-DIR", f"row dir {row.dir!r} missing")]
    own = {f: t for f, t in row.code.items() if f not in LINT.VENDORED}
    spec = dict(row.spec)
    spec.setdefault("scratch_root", row.dir)
    if LINT.SMOKE_RX.search("\n".join(own.values())):
        out += [(l, c, m) for l, c, m in LINT.smoke_checks(row.dir, spec, own)]
    out += LINT.stale_out(row.dir)
    return out


def _row_spec_by_id(rid, flags):
    for p in (os.path.join(flags or "", "ready", rid + ".json"), os.path.join(TMP_ROOT, rid, "spec.json")):
        d = _load_json(p)
        if d:
            return d
    return None


def check_estimate(row, ctx):
    out = []
    b = row.spec.get("estimate_basis")
    est = row.spec.get("estimate_s")
    if not isinstance(b, dict):
        return [("WARN", "NO-BASIS", "no estimate_basis (units x measured unit_s)")] if est else []
    units = b.get("units")
    unit_s = b.get("unit_s")
    src = "estimate_basis.unit_s"
    try:
        import rowflow as rf
        paths = rf.smoke_measure_paths(row.spec, rf.dry_dir(ctx.get("flags") or rf.FLAGS, row.id))
    except Exception:  # noqa: BLE001
        paths = [os.path.join(row.dir, "out-smoke", "smoke_measure.json")]
    for p in paths if not unit_s else []:   # a declared unit_s wins; a plumbing smoke's unit is not a run unit
        m = _load_json(p)
        if m and isinstance(m.get("unit_s"), (int, float)) and m["unit_s"] > 0:
            unit_s, src = m["unit_s"], p
            b = dict(b, loads_s=m.get("loads_s", b.get("loads_s")))
            break
    own_root = os.path.realpath(row.dir)
    refs = set()
    for p in paths if src != "estimate_basis.unit_s" else []:
        if not os.path.realpath(p).startswith(own_root + os.sep):
            refs |= set(ROWID_RX.findall(p))
    if src == "estimate_basis.unit_s":
        refs |= set(ROWID_RX.findall(str(b.get("reason") or "") + " " + str(b.get("rebook_from") or "")))
    refs.discard(row.id)
    mine_models = {SHARD_RX.sub(".gguf", os.path.basename(p)) for p in model_files(row)}
    mine_shape = row.spec.get("shape") or row.spec.get("declared_shape")
    for rid in sorted(refs):
        other = _row_spec_by_id(rid, ctx.get("flags"))
        if not other:
            continue
        orow = Row(other, os.path.join(TMP_ROOT, rid) if not other.get("launcher") else None)
        om = {SHARD_RX.sub(".gguf", os.path.basename(p)) for p in model_files(orow)}
        oshape = other.get("shape") or other.get("declared_shape")
        why = []
        if mine_models and om and not (mine_models & om):
            why.append(f"model {sorted(om)[:2]} vs {sorted(mine_models)[:2]}")
        if mine_shape and oshape and oshape != mine_shape:
            why.append(f"shape {oshape} vs {mine_shape}")
        mt, ot = row.spec.get("declared_threads"), other.get("declared_threads")
        if isinstance(mt, int) and isinstance(ot, int) and mt != ot:
            why.append(f"declared_threads {ot} vs {mt}")
        if why:
            out.append(("FAIL", "BORROWED-BASIS", f"estimate basis borrowed from {rid}, which differs: {'; '.join(why)}"))
        elif src == "estimate_basis.unit_s":
            out.append(("WARN", "BORROWED-BASIS", f"unit_s borrowed from {rid} (same model/shape); re-book from this row's "
                                                  "own smoke_measure.json"))
    if src == "estimate_basis.unit_s" and unit_s and not refs and b.get("provisional"):
        out.append(("WARN", "BASIS-PROVISIONAL", "unit_s is provisional (no smoke measurement on disk yet)"))
    if isinstance(units, (int, float)) and isinstance(unit_s, (int, float)) and units > 0 and unit_s > 0 and est:
        implied = (units * unit_s + float(b.get("loads_s") or 0)) * float(b.get("margin") or 1.25)
        r = float(est) / implied if implied else 0
        if r > EST_OFF_X or (r and r < 1 / EST_OFF_X):
            out.append(("WARN", "ESTIMATE-OFF", f"estimate_s {est} is {r:.1f}x the basis ({units} x {unit_s:g} s from {src})"))
    return out


def check_ports(row, ctx):
    out = []
    mine = set(int(p) for p in (row.spec.get("ports") or []) if str(p).isdigit())
    if not mine:
        return out
    sup = str(row.spec.get("supersedes") or "")
    for rid, d in sorted((ctx.get("queued") or {}).items()):
        if rid in (row.id, sup) or str(d.get("supersedes") or "") == row.id:
            continue
        clash = mine & set(int(p) for p in (d.get("ports") or []) if str(p).isdigit())
        if clash:
            out.append(("FAIL", "PORT-CLASH", f"port(s) {sorted(clash)} also declared by queued row {rid}"))
    return out


def _append_writes(code):
    n_append, n_w_results, batch = 0, 0, []
    for f, t in code.items():
        if re.search(r"\b(?:append_unit|append_result|Ledger|led\.add|ledger\.add|\.add\(\s*\{)", t):
            n_append += 1
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "open":
                mode = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == "mode"), None)
                mv = mode.value if isinstance(mode, ast.Constant) and isinstance(mode.value, str) else ""
                seg = ast.get_source_segment(t, n) or ""
                if "a" in mv:
                    n_append += 1
                elif "w" in mv and "results.jsonl" in seg:
                    n_w_results += 1
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "write" and n.args:
                seg = ast.get_source_segment(t, n.args[0]) or ""
                if re.search(r"\"\\n\"\.join|'\\n'\.join", seg):
                    batch.append(f"{f}:{n.lineno}")
    return n_append, n_w_results, batch


def check_append(row, ctx):
    rp = str(row.spec.get("result_path") or "")
    if not (row.spec.get("resumable") or row.spec.get("unit_key") or rp.endswith(".jsonl")):
        return []
    try:
        import ak_row_lint as LINT
        own = {f: t for f, t in row.code.items() if f not in LINT.VENDORED or f == "lp_common.py"}
    except ImportError:
        own = row.code
    if not own:
        return []
    n_append, n_w, _batch = _append_writes(own)
    if n_append == 0 and n_w:
        return [("FAIL", "RESULT-NOT-APPENDED", "results.jsonl is written in 'w' mode and never appended: a stop loses "
                                                "every unit of the group (append one line per unit)")]
    if n_append == 0:
        return [("WARN", "RESULT-APPEND-UNPROVEN", "resumable/per-unit row with no append-mode result write found")]
    return []


def check_witness(row, ctx):
    wl = row.spec.get("witness_lines")
    rule = str(row.spec.get("decision_rule") or "") + " " + str(row.spec.get("smoke_note") or "")
    if not wl:
        m = WITNESS_DEP_RX.search(rule)
        if m:
            return [("FAIL", "WITNESS-UNDECLARED", f"the verdict rests on a debug/log line ({m.group(0)[:60]!r}) but "
                                                   "spec.witness_lines is absent: declare [{line, needs, cap}] so the cap is "
                                                   "checked against the binary (gvfattn-served-r2: an 8-line debug cap)")]
        return []
    if not isinstance(wl, list):
        return [("FAIL", "WITNESS-SPEC", "witness_lines must be a list of {line, needs, cap}")]
    out = []
    stores = [store_root(s) for s in stores_of(row) if os.path.isdir(s)]
    for i, w in enumerate(wl):
        if not isinstance(w, dict) or not str(w.get("line") or "").strip():
            out.append(("FAIL", "WITNESS-SPEC", f"witness_lines[{i}] needs a non-empty 'line'"))
            continue
        line = str(w["line"])
        lit = re.split(r"%|\{", line, 1)[0].strip()
        st = [os.path.realpath(w["store"])] if w.get("store") else stores
        if lit and st and not any(store_has_literal(s, lit, ctx.get("flags")) for s in st):
            out.append(("FAIL", "WITNESS-NOT-IN-BINARY", f"witness line {lit[:50]!r} is in no store's strings"))
        cap, needs = w.get("cap"), w.get("needs")
        if cap is None:
            out.append(("FAIL", "WITNESS-CAP-UNDECLARED", f"witness_lines[{i}] ({lit[:40]!r}) declares no cap "
                                                          "(null-cap = 'unlimited' must be said as cap: -1)"))
        elif isinstance(cap, int) and cap >= 0 and isinstance(needs, int) and needs > cap:
            out.append(("FAIL", "WITNESS-CAP", f"witness {lit[:40]!r} needs {needs} line(s) per process; the binary caps it at {cap}"))
        cw = w.get("cap_witness")
        if cw and st and not any(store_has_literal(s, str(cw), ctx.get("flags")) for s in st):
            out.append(("FAIL", "WITNESS-CAP-UNPROVEN", f"cap_witness {str(cw)[:40]!r} is in no store's strings"))
    return out


CHECK_FNS = {"selftest": check_selftest, "store": check_store, "flags": check_flags, "model": check_model,
             "lane": check_lane, "smoke": check_smoke, "estimate": check_estimate, "ports": check_ports,
             "append": check_append, "witness": check_witness}


# ---------------------------------------------------------------- runners
def run(spec, row_dir=None, flags=None, queued=None, checks=CHECKS, run_selftest=False, nodes=None, vram=None):
    """[(check, raw_level, code, msg)] for one row. Never raises: a crashing check is reported as a WARN."""
    row = Row(spec, row_dir)
    ctx = {"flags": flags, "queued": queued, "run_selftest": run_selftest, "nodes": nodes, "vram": vram}
    out = []
    for c in checks:
        try:
            out += [(c, l, code, m) for l, code, m in CHECK_FNS[c](row, ctx)]
        except Exception as e:  # noqa: BLE001
            out.append((c, "WARN", "PREFLIGHT-CRASH", f"{type(e).__name__}: {e}"))
    return out


def effective(findings, enforce=None):
    """Apply the WARN-first switch: a raw FAIL stays FAIL only for an enforced check."""
    enforce = PREFLIGHT_ENFORCE if enforce is None else enforce
    return [(c, "FAIL" if l == "FAIL" and enforce.get(c) else ("WARN" if l == "FAIL" else l), code, m)
            for c, l, code, m in findings]


def fmt(f):
    c, l, code, m = f
    return f"{l} preflight/{c} {code}: {m}"


def queued_rows(flags):
    """{id: manifest} of rows not done/stopped (the same states `rowflow.py list` prints)."""
    import rowflow as rf
    allrows = rf.rows(flags)
    out = {}
    G = os.path.join(flags, "grants")
    for rid, d in allrows.items():
        if any(os.path.exists(p) for p in (os.path.join(G, rid + ".complete"), os.path.join(G, rid + ".ended"),
                                            os.path.join(flags, "filing-done", rid + ".FILED"))):
            continue   # done: the same test _status_raw makes first, without its lineage walk
        try:
            st = rf._status_raw(flags, rid, allrows).get("state")
        except Exception:  # noqa: BLE001
            st = "unknown"
        if st not in ("done", "stopped"):
            out[rid] = d
    return out


def publish_check(spec, flags, warn=print, queued=None):
    """publish_row hook: effective FAILs raise rowflow.Refused; every raw FAIL/WARN is reported through warn()."""
    import rowflow as rf
    if queued is None:
        try:
            queued = queued_rows(flags)
        except Exception:  # noqa: BLE001
            queued = {}
    res = run(spec, flags=flags, queued=queued)
    eff = effective(res)
    for raw, f in zip(res, eff):
        warn(fmt(f) + (" (would FAIL if enforced; publish continues)" if raw[1] == "FAIL" and f[1] != "FAIL" else ""))
    fails = [fmt(f) for f in eff if f[1] == "FAIL"]
    if fails:
        raise rf.Refused("preflight: " + "; ".join(fails))
    return res


def grant_check(flags, rid, d, queued=None):
    """Allocator hook (just before a grant is written): DRIFT_CHECKS only. Returns (hold_reason or None, lines)."""
    res = effective(run(d, flags=flags, queued=queued or {}, checks=DRIFT_CHECKS))
    lines = [fmt(f) for f in res if f[1] in ("FAIL", "WARN")]
    fails = [fmt(f) for f in res if f[1] == "FAIL"]
    return ("preflight: " + "; ".join(fails)[:600]) if fails else None, lines


def report(flags, as_json=False, out=print, queued=None):
    """Per check: how many queued rows would FAIL it (raw), and which; WARN counts too. The evidence for flipping."""
    queued = queued_rows(flags) if queued is None else queued
    nodes = node_map()
    per = {c: {"fail": [], "warn": [], "enforced": PREFLIGHT_ENFORCE.get(c, False)} for c in CHECKS}
    detail = {}
    for rid in sorted(queued):
        res = run(queued[rid], flags=flags, queued=queued, nodes=nodes)
        detail[rid] = [list(f) for f in res]
        for c in CHECKS:
            lv = {l for cc, l, _code, _m in res if cc == c}
            if "FAIL" in lv:
                per[c]["fail"].append(rid)
            elif "WARN" in lv:
                per[c]["warn"].append(rid)
    if as_json:
        out(json.dumps({"queued": len(queued), "checks": per, "detail": detail}, indent=1))
        return per
    out(f"PREFLIGHT REPORT over {len(queued)} queued row(s); FAIL = would fail if enforced (flip only at 0)")
    for c in CHECKS:
        p = per[c]
        out(f"{c:9} enforce={'on ' if p['enforced'] else 'off'} fail={len(p['fail']):3} warn={len(p['warn']):3}"
            + (f"  fail: {', '.join(p['fail'])}" if p["fail"] else ""))
        for rid in p["fail"]:
            for cc, l, code, m in detail[rid]:
                if cc == c and l == "FAIL":
                    out(f"    {rid}: {code}: {m[:220]}")
    return per


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", nargs="*")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--flags", default=None)
    a = ap.parse_args(argv)
    import rowflow as rf
    flags = a.flags or rf.FLAGS
    if a.report:
        report(flags, as_json=a.json)
        return 0
    if not a.rows:
        ap.print_help()
        return 2
    queued = queued_rows(flags)
    bad = 0
    for r in a.rows:
        p = os.path.join(r, "spec.json") if os.path.isdir(r) else r
        spec = _load_json(p) or {}
        res = run(spec, row_dir=os.path.dirname(os.path.abspath(p)), flags=flags, queued=queued)
        for f in res:
            print(f"{f[1]} {f[0]} {f[2]} {r}: {f[3]}")
        bad += sum(1 for f in effective(res) if f[1] == "FAIL")
        if not res:
            print(f"OK {r}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
