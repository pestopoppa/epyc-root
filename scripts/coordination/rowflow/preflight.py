#!/usr/bin/env python3
"""preflight.py - deterministic row pre-flight checks for every owner's rows (D9-ack, operator 2026-11-24, "Approve, WARN first").

Run from publish_row.py (after the D9 lint, before anything is published) and from the allocator just before a row's grant
is written (only the checks that can drift since publish: DRIFT_CHECKS). Static only: file stats, SHA256SUMS, `strings`,
GGUF headers, AST. No model loads, no GPU, no compute; seconds per row (the `strings` sets and the store verification are
cached per store SHA256SUMS digest under <flags>/preflight-cache/).

WARN FIRST: every check reports a raw level (FAIL = the row would fail it, WARN = advisory). A raw FAIL only refuses
(publish) or holds the grant (allocator) when PREFLIGHT_ENFORCE[check] is True. All start False. Flip one only when
`rowflow.py preflight --report` (or `preflight.py --report`) shows zero currently queued rows fail it.
`rowflow.py preflight --rollout` summarizes the remaining warn-only checks. Freeze rule changes during AK pushes;
zero failures indicates readiness, not authorization to change a switch during a freeze.
--report counts only really-queued rows (report_scope: not ended/superseded/STOP-held; excluded rows listed with the reason) and
grandfathers PUBLISH_ONLY checks (witness_log, witness_decl) on rows whose smoke PASSED. witness_log/witness_decl enforced 2026-11-24.

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
  served   11  spec.served_ref {registry_role, argv_delta} -> the registry server_mode entry's serving_shape, diffed
               against the job's llama-server argv; any delta not declared in argv_delta (with a reason) fails (RCA F2).
               mk_ak_row v2 schema: served_ref.argv is rebuilt via orchestrator_stack.build_server_command and diffed
  witness_log  13  a row declaring a knob witness (job.py KNOBS / spec.witness_lines) must run llama-server with -lv >= 4
               (INFO witness lines never print otherwise: ak-c22-i8pc-gate-gpu-20261124-r3). WITNESS-LOGLEVEL
  witness_log_tools 15  the same -lv >= 4 rule on EVERY other llama binary argv in the job (llama-perplexity KLD unit, llama-bench,
               llama-cli, ...): the e2e server had -lv 4 but unit_kld ran llama-perplexity without it (ak-c22-q8mc-gate-gpu-20261124).
               WITNESS-LOGLEVEL-TOOL. Separate switch from witness_log (the server part) so it can be WARN while the server part enforces.
  witness_decl 14  a row declaring job.py KNOBS but no spec.witness_lines: WITNESS-UNDECLARED
  inputs   16  every input file the row PINS exists in the row dir with the pinned sha256: INPUT-MISSING / INPUT-SHA. Pins =
               SHA256SUMS / SOURCE.sha256 lines, a 64-hex literal in job code next to a relative path (TEXT_SHA beside
               inputs/kld_text.txt), and any literal `inputs/<file>` path (existence only). Paths outside the row dir
               (GGUFs, stores) are the store/model checks' job. PUBLISH_ONLY (ak-c22-q8wp-op-gpu-20261125: kld_text.txt
               never copied, found only at smoke).
  replay_decide 17 (R4, waste audit 2026-11-25) a row whose family left a prior out/: `job.py --decide-from <prior out>`
               (nice 19, cpus 84-87, timeout 60; no GPU) must run, return a verdict and not reproduce the prior smoke FAIL's
               class: REPLAY-DECIDE-CRASH / -NO-VERDICT / -NO-UNITS / -SAME-CLASS; legacy jobs without the entry point WARN. PUBLISH_ONLY.
  replay_receipt 18 (R1) a republish of a family whose LAST smoke FAILED needs replay_decide's replay of THAT run's out/ to
               judge >= 1 witnessed unit and reach a different failure (witness: no prior (knob, arm) still missing;
               server/timeout/stop/residency/input failures are not replayable, never a refusal): REPLAY-RECEIPT-MISSING /
               -NO-UNITS / -GATE-REMOVED / -SAME-CLASS. spec.fix_ref {store, reason} naming a new kernel store is the one
               escape. No job-sha (fresh_attempt) bypass. PUBLISH_ONLY.
  generator 12 WARN only: job.py `# GENERATED-BY: mk_ak_row.py v2 harness_sha256=<sha>` + spec.generator agree
  (7, RCA F5: estimate_basis must cite {smoke_measure, sha256, units, unit_s, loads_s, margin} of this row or of a
   row with identical (model, lane, declared_threads, argv hash); arithmetic checked; estimate_history >1.5x warns)

Usage: preflight.py <row_dir|spec.json> [...]   |   preflight.py --report|--rollout [--flags DIR] [--json]
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

CHECKS = ("selftest", "store", "flags", "model", "lane", "smoke", "estimate", "ports", "append", "witness", "served", "generator", "witness_log", "witness_decl", "witness_log_tools", "inputs",
          "replay_decide", "replay_receipt")   # replay_decide BEFORE replay_receipt: R4's replay can serve as the R1 receipt
# THE switch (operator 2026-11-24): one entry per check; True = a raw FAIL refuses/holds. All start False (WARN for everyone).
PREFLIGHT_ENFORCE = {c: False for c in CHECKS}
# Operator 2026-11-24 (via coordinator): enforce the four checks with 0 failing queued rows at deploy time.
PREFLIGHT_ENFORCE.update(store=True, ports=True, append=True, witness_log=True, witness_decl=True,
                         witness_log_tools=True,
                         inputs=True)   # 2026-11-25: --report showed 0 queued non-grandfathered fails (inputs: 0 of 14)
# estimate: on the operator's 0-fail list, but the RCA F5 tightening (2026-11-24) re-stages it warn-first; flip at 0 fails.
DRIFT_CHECKS = ("store", "flags", "lane", "smoke", "ports", "witness", "served")   # re-run at grant time (code is sealed at publish)

_LLM = "/mnt/raid0/llm/"
TMP_ROOT = _LLM + "tmp"
STORE_RX = re.compile(r"(/(?:[A-Za-z0-9._+-]+/)*kernels/(?:builds|production|candidates|experimental|quarantine)/[A-Za-z0-9._+-]+)")
TREE_BUILD_RX = re.compile(re.escape(_LLM) + r"llama\.cpp/build(?:-hip)?/bin")
GGUF_RX = re.compile(r"(?<![\w}).$])(/[^\s\"'`,;:)\]}{$]+?\.gguf)\b")
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
                 "--selftest", "-c", "-n", "-N", "--"}
WRAPPER_TOOLS = {"taskset", "numactl", "nice", "ionice", "env", "chrt", "timeout", "stdbuf"}
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
            if f.endswith(".py") and f not in ("ak_row_harness.py", "ak_gate.py"):   # vendored, tested harness libraries
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
def _const_list(node, aliases=None):
    out = []
    for e in node.elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, (str, int, float)):
            out.append(str(e.value))
        else:
            out.append(_expr_binary(e, aliases) or "<expr>")
    return out


_BIN_HINT_RX = re.compile(r"(test[-_]backend[-_]ops|llama[-_][a-z][a-z0-9_-]*)", re.I)


def _expr_binary(e, aliases=None):
    """A non-literal argv element (f-string, path join, variable) that visibly names a llama binary -> its basename, else ''.
    Lets the argv[0] scoping see `[str(BIN / "test-backend-ops"), "--test-file", ...]` and `[TEST_BACKEND_OPS, ...]`."""
    for n in ast.walk(e):
        t = None
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            t = os.path.basename(n.value.rstrip("/"))
        elif isinstance(n, ast.Name):
            t = (aliases or {}).get(n.id) or n.id
        elif isinstance(n, ast.Attribute):
            t = n.attr
        m = _BIN_HINT_RX.fullmatch(t or "") or (_BIN_HINT_RX.match(t) if isinstance(n, ast.Constant) and t else None)
        if m:
            return m.group(1).replace("_", "-").lower()
    return ""


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
        aliases = {}   # NAME = <expr naming a llama binary> (any depth of assignment), so `[TBO, "--test-file"]` reads as test-backend-ops
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                b = _expr_binary(n.value, aliases)
                if b:
                    aliases[n.targets[0].id] = b
        for n in ast.walk(tree):
            if isinstance(n, (ast.List, ast.Tuple)) and n.elts:
                a = _const_list(n, aliases)
                if not any(x.startswith("-") and len(x) > 1 and not re.fullmatch(r"-[\d.]+", x) for x in a):
                    continue
                if any(OTHER_TOOLS_RX.search(x) for x in a if not x.startswith("-")):
                    continue
                srv = next((k for k, x in enumerate(a) if x.endswith("llama-server")), None)
                if srv is not None:
                    a = a[srv:]          # [taskset, -c, .., numactl, .., --, llama-server, ...]: the server's own argv
                elif any(os.path.basename(x) in WRAPPER_TOOLS for x in a):
                    continue             # a pure placement wrapper (taskset/numactl/nice ... --)
                elif not a[0].startswith("-") and a[0] != "<expr>" and not a[0].isdigit():
                    continue             # argv[0] names another binary (test-backend-ops, llama-bench, python3 ...): not a server argv
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
        if not os.path.isdir("/" + p.lstrip("/").split("/", 1)[0]):
            continue   # MDIR + '/UD-IQ4_XS/x.gguf': a suffix joined at run time, not an absolute path
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
def arm_deltas(row):
    """served_ref.argv_delta in canonical form [{arm?, flag, value, reason}] plus the legacy top-level
    arm_argv_delta {"ON": {"replace": {flag: value}, "append": [flag, value, ...]}} converted (legacy=True)."""
    ref = row.spec.get("served_ref") if isinstance(row.spec.get("served_ref"), dict) else {}
    out = [dict(d) for d in (ref.get("argv_delta") or []) if isinstance(d, dict)]
    legacy = row.spec.get("arm_argv_delta")
    if isinstance(legacy, dict):
        for arm, body in legacy.items():
            body = body if isinstance(body, dict) else {}
            for f, v in (body.get("replace") or {}).items():
                out.append({"arm": arm, "flag": f, "value": v, "reason": "legacy arm_argv_delta replace", "legacy": True})
            toks = [str(x) for x in (body.get("append") or [])]
            k = 0
            while k < len(toks):
                f = toks[k]
                v = toks[k + 1] if k + 1 < len(toks) and not toks[k + 1].startswith("-") else True
                out.append({"arm": arm, "flag": f, "value": v, "reason": "legacy arm_argv_delta append", "legacy": True})
                k += 2 if v is not True else 1
    return out


def _bin_store(path):
    p = str(path or "")
    return os.path.dirname(os.path.dirname(p)) if p.endswith("/bin/llama-server") else None


def row_stores(row):
    """The stores the row actually RUNS: literal stores in its code, plus served_ref.argv[0] after any `argv[0]` delta
    (lever rows swap it to a candidate store on purpose), minus a served argv[0] store every arm replaces."""
    lit = set(stores_of(row))
    ref = row.spec.get("served_ref") if isinstance(row.spec.get("served_ref"), dict) else {}
    argv = ref.get("argv") if isinstance(ref.get("argv"), list) else None
    if not argv:
        return sorted(lit)
    base = _bin_store(argv[0])
    d0 = [d for d in arm_deltas(row) if d.get("flag") == "argv[0]" and d.get("value")]
    allarm = [d for d in d0 if not d.get("arm")]
    eff = {_bin_store(d["value"]) for d in d0} - {None}
    if not allarm and base:
        eff.add(base)          # arms without an argv[0] delta run the registry binary
    if allarm and base and base not in eff:
        lit = {x for x in lit if store_root(x) != store_root(base)}
    return sorted(lit | eff)


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
    for root in row_stores(row):
        if not os.path.isdir(root):
            out.append(("FAIL", "STORE-MISSING", f"{root} does not exist"))
            continue
        real = store_root(root)
        if not store_manifest(real):
            out.append(("FAIL", "STORE-NO-SUMS", f"{root} has no SHA256SUMS"))
        elif not ctx.get("paths_only"):
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
    stores = [store_root(s) for s in row_stores(row) if os.path.isfile(os.path.join(store_root(s), "bin", "llama-server"))]
    fl = argv_flags(server_argvs(row))
    for root in stores:
        have = store_flags(root, ctx.get("flags"))
        if have is None:
            continue
        miss = sorted(f for f in fl if f not in have)
        if miss:
            out.append(("FAIL", "FLAG-UNKNOWN", f"server flag(s) {miss[:6]} not in {os.path.basename(root)}/bin/llama-server"))
    libstores = [store_root(s) for s in row_stores(row) if glob.glob(os.path.join(store_root(s), "bin", "libggml*.so*"))]
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
    gpu_host = set(range(88, 96)) | set(range(184, 192))
    shape = str(row.spec.get("shape") or row.spec.get("declared_shape") or "")
    if row.spec.get("lane") == "cpu" and (shape == "host" or granted & gpu_host):
        out.append(("WARN", "HOST-SHAPE-OVERLAPS-GPU", "HOST-SHAPE-OVERLAPS-GPU: book q0,q1,q2 quiet-host instead (q3 holds "
                                                       "the GPU host cores 88-95/184-191; a host booking waits on the GPU row "
                                                       "and idles q0-q2)"))
    tvals = {int(v) for v in argv_value(argvs, "-t", "--threads") if v.isdigit()}
    dt = row.spec.get("declared_threads")
    if isinstance(dt, int) and tvals and max(tvals) != dt:
        out.append(("WARN", "THREADS-DECLARED", f"server -t {sorted(tvals)} != declared_threads {dt}"))
    lim = len(granted) if granted else len(pinned)   # AK 2026-11-24: only -t > the granted cpus fails; a region
    if lim and tvals and max(tvals) > lim:            # wider than -t (16 vs 8) is the THREADS-DECLARED WARN above
        out.append(("FAIL", "THREADS-OVERSUB", f"-t {max(tvals)} > {lim} granted cpus"))
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


def argv_hash(row):
    """sha256 over the sorted server-argv tokens (paths reduced to basenames, ports dropped): the measured cell."""
    toks = []
    for _f, _ln, a in server_argvs(row):
        a = [t for y in a for t in str(y).split()]
        skip = False
        for x in a:
            if skip:
                skip = False
                continue
            if x == "--port":
                skip = True
                continue
            toks.append(os.path.basename(x) if x.startswith("/") else x)
    return hashlib.sha256("\x00".join(sorted(toks)).encode()).hexdigest()


def cell_identity(row):
    """(models, lane, declared_threads, argv hash): rows sharing it measure the same cell (RCA F5)."""
    models = tuple(sorted(SHARD_RX.sub(".gguf", os.path.basename(p)) for p in model_files(row)))
    return models, row.spec.get("lane"), row.spec.get("declared_threads"), argv_hash(row)


BASIS_FIELDS = ("smoke_measure", "sha256", "units", "unit_s", "loads_s", "margin")
HISTORY_OFF_X = 1.5
_HIST = {}


def _history(flags, rid, units):
    try:
        import estimate_history as EH
    except ImportError:
        return None
    fl = flags or EH.FLAGS
    if fl not in _HIST:
        try:
            _HIST[fl] = EH.samples(fl)
        except Exception:  # noqa: BLE001
            _HIST[fl] = []
    try:
        return EH.suggest(rid, units=units, flags=fl, recs=_HIST[fl])
    except Exception:  # noqa: BLE001
        return None


def check_estimate(row, ctx):
    """RCA F5 (2026-11-24): estimate_basis cites a measurement {smoke_measure, sha256, units, unit_s, loads_s, margin}
    from this row or from a row of identical (model, lane, declared_threads, argv hash); the arithmetic holds; the
    family history (estimate_history.suggest) is within 1.5x."""
    out = []
    b = row.spec.get("estimate_basis")
    est = row.spec.get("estimate_s")
    if not est:
        return out
    if not isinstance(b, dict):
        return [("FAIL", "NO-BASIS", "no estimate_basis: cite {smoke_measure, sha256, units, unit_s, loads_s, margin}")]
    miss = [k for k in BASIS_FIELDS if b.get(k) in (None, "")]
    sm = b.get("smoke_measure") or b.get("rebook_from")
    smp = (sm if os.path.isabs(str(sm)) else os.path.join(row.dir, str(sm))) if sm else None
    if miss:
        lvl = "WARN" if b.get("provisional") and not (smp and os.path.isfile(smp)) else "FAIL"
        out.append((lvl, "BASIS-INCOMPLETE", f"estimate_basis lacks {miss}" +
                    (" (provisional before the smoke; rebook at PASS)" if lvl == "WARN" else "")))
    if smp and os.path.isfile(smp):
        m = _load_json(smp) or {}
        if b.get("sha256") and _sha256(smp) != str(b["sha256"]).lower():
            out.append(("FAIL", "BASIS-SHA", f"{smp} sha256 differs from estimate_basis.sha256 (re-measured since)"))
        mu = m.get("unit_s")
        if isinstance(mu, (int, float)) and isinstance(b.get("unit_s"), (int, float)) and mu > 0 \
                and abs(b["unit_s"] - mu) > 0.01 * mu:
            out.append(("FAIL", "BASIS-MISMATCH", f"basis unit_s {b['unit_s']} != measured {mu} in {smp}"))
        own = os.path.realpath(smp).startswith(os.path.realpath(row.dir) + os.sep)
        if not own:
            src = next(iter(ROWID_RX.findall(smp)), None)
            other = _row_spec_by_id(src, ctx.get("flags")) if src else None
            if not other:
                out.append(("FAIL", "BORROWED-BASIS", f"{smp} is not this row's and its row cannot be resolved"))
            else:
                orow = Row(other, os.path.join(TMP_ROOT, src) if not other.get("launcher") else None)
                a, o = cell_identity(row), cell_identity(orow)
                if a != o:
                    diff = [n for n, x, y in zip(("model", "lane", "declared_threads", "argv"), a, o) if x != y]
                    out.append(("FAIL", "BORROWED-BASIS", f"basis measured on {src}, which differs in {diff}"))
    elif sm and not b.get("provisional"):
        out.append(("FAIL", "BASIS-MISSING", f"estimate_basis.smoke_measure {sm} does not exist"))
    else:   # prose-only basis naming another row (c21-gpu27b-identity r1)
        refs = set(ROWID_RX.findall(str(b.get("reason") or ""))) - {row.id}
        for rid in sorted(refs):
            other = _row_spec_by_id(rid, ctx.get("flags"))
            if other:
                orow = Row(other, os.path.join(TMP_ROOT, rid) if not other.get("launcher") else None)
                diff = [n for n, x, y in zip(("model", "lane", "declared_threads", "argv"), cell_identity(row),
                                             cell_identity(orow)) if x != y]
                out.append(("FAIL" if diff else "WARN", "BORROWED-BASIS",
                            f"timing borrowed from {rid}" + (f", which differs in {diff}" if diff else
                                                              " (same cell); cite its smoke_measure + sha256")))
    try:
        units, unit_s = float(b["units"]), float(b["unit_s"])
        implied = (units * unit_s + float(b.get("loads_s") or 0)) * float(b.get("margin") or 1.25)
        mg = max(1.0, float(b.get("margin") or 1.25))
        if implied > 0 and not (implied / mg <= float(est) <= implied * mg + 60):
            out.append(("FAIL", "ESTIMATE-ARITH", f"estimate_s {est} vs (units x unit_s + loads_s) x margin = {implied:.0f}"))
    except (KeyError, TypeError, ValueError):
        pass
    if ctx.get("history", True):
        h = _history(ctx.get("flags"), row.id, b.get("units") if isinstance(b.get("units"), int) else None)
        if h and h.get("estimate_s"):
            r = float(est) / float(h["estimate_s"])
            if r > HISTORY_OFF_X or r < 1 / HISTORY_OFF_X:
                out.append(("WARN", "ESTIMATE-HISTORY", f"estimate_s {est} is {r:.2f}x the family history "
                                                        f"({h.get('estimate_justification')})"))
    return out


# ---------------------------------------------------------------- 11 served argv (RCA F2)
REGISTRY = os.environ.get("PREFLIGHT_REGISTRY", _LLM + "epyc-orchestrator/orchestration/model_registry.yaml")
_REG = {}
FLAG_ALIASES = {"-c": ("-c", "--ctx-size"), "-np": ("-np", "--parallel"), "-ctk": ("-ctk", "--cache-type-k"),
                "-ctv": ("-ctv", "--cache-type-v"), "--no-mmap": ("--no-mmap",), "--cache-ram": ("--cache-ram", "-cram"),
                "--ctx-checkpoints": ("--ctx-checkpoints",)}


def served_expect(entry):
    """{flag: value or True} the registry server_mode entry implies for llama-server."""
    sh = entry.get("serving_shape") or {}
    e = {}
    if sh.get("n_ctx"):
        e["-c"] = str(sh["n_ctx"])
    slots = entry.get("slots")
    if slots:
        e["-np"] = str(slots)
    kv = sh.get("kv_quant") or {}
    if kv.get("k"):
        e["-ctk"] = str(kv["k"])
    if kv.get("v"):
        e["-ctv"] = str(kv["v"])
    if entry.get("no_mmap"):
        e["--no-mmap"] = True
    if entry.get("cache_ram") is not None:
        e["--cache-ram"] = str(entry["cache_ram"])
    if entry.get("ctx_checkpoints") is not None:
        e["--ctx-checkpoints"] = str(entry["ctx_checkpoints"])
    return e


def _registry(path):
    if path not in _REG:
        try:
            import yaml
            with open(path) as f:
                _REG[path] = yaml.safe_load(f) or {}
        except Exception:  # noqa: BLE001
            _REG[path] = None
    return _REG[path]


ORCH_ROOT = os.environ.get("PREFLIGHT_ORCH_ROOT", _LLM + "epyc-orchestrator")
REBUILD_TIMEOUT_S = 30
_REBUILD_PY = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from scripts.server.orchestrator_stack import build_server_command
from src.registry_loader import RegistryLoader
cmd = build_server_command(RegistryLoader().get_role(sys.argv[2]), int(sys.argv[3]), prepare_runtime_dirs=False)
print(json.dumps([str(x) for x in cmd]))
"""


def _git_head(root):
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def rebuild_served_argv(role, port, flags=None):
    """The served argv as mk_ak_row v2 builds it: orchestrator_stack.build_server_command(RegistryLoader().get_role(role),
    port, prepare_runtime_dirs=False), run in a subprocess in the orchestrator checkout (no server, no dirs). Cached per
    (registry sha, orchestrator HEAD, role, port). Returns (argv with {PORT}, None) or (None, why)."""
    reg = REGISTRY
    try:
        rsha = _sha256(reg)
    except OSError as e:
        return None, f"registry unreadable: {e}"
    head = _git_head(ORCH_ROOT) or "nohead"
    port = int(port or 1)
    key = hashlib.sha256(f"{rsha}:{head}:{role}:{port}".encode()).hexdigest()
    c = _cache_get(flags, key, "served")
    if c and "argv" in c:
        return c["argv"], None
    try:
        p = subprocess.run([sys.executable, "-I", "-c", _REBUILD_PY, ORCH_ROOT, str(role), str(port)], cwd=ORCH_ROOT,
                           capture_output=True, text=True, timeout=REBUILD_TIMEOUT_S,
                           env={"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
                                "HIP_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"rebuild failed: {type(e).__name__}"
    if p.returncode != 0:
        return None, f"rebuild rc {p.returncode}: {(p.stderr or '').strip()[-160:]}"
    try:
        argv = placeholder_argv(json.loads(p.stdout.strip().splitlines()[-1]))
    except (ValueError, IndexError):
        return None, "rebuild printed no argv"
    _cache_put(flags, key, "served", {"argv": argv, "role": role, "registry_sha256": rsha, "orchestrator_commit": head})
    return argv, None


def placeholder_argv(argv):
    """mk_ak_row v2 contract: the --port value becomes "{PORT}" and the --slot-save-path value "{SLOTDIR}"; nothing else."""
    out = [str(x) for x in argv]
    for k, x in enumerate(out[:-1]):
        if x == "--port":
            out[k + 1] = "{PORT}"
        elif x == "--slot-save-path":
            out[k + 1] = "{SLOTDIR}"
    return out


def served_argv_sha256(argv):
    """mk_ak_row v2 contract: sha256(json.dumps(argv)) with default separators."""
    return hashlib.sha256(json.dumps(argv).encode()).hexdigest()


def argv_map(tokens):
    """{flag: value | True} of a server argv; '<expr>' / '{PLACEHOLDER}' values are wildcards (None)."""
    toks = [t for y in tokens for t in str(y).split()]
    out = {}
    for k, x in enumerate(toks):
        if x.startswith("-") and len(x) > 1 and not re.fullmatch(r"-[\d.]+", x):
            if "=" in x and x.startswith("--"):
                f, v = x.split("=", 1)
            else:
                nxt = toks[k + 1] if k + 1 < len(toks) else None
                f, v = x, (nxt if nxt is not None and not (nxt.startswith("-") and not re.fullmatch(r"-[\d.]+", nxt)) else True)
            if isinstance(v, str) and (v == "<expr>" or re.search(r"\{[A-Z_]+\}", v)):
                v = None
            out[f] = v
    return out


def _diff(expected, got, declared):
    """Deltas of got vs expected not covered by declared {flag: value|None}. Wildcards (None) never differ."""
    out = []
    for f in sorted(set(expected) | set(got)):
        if f in ("--port",):
            continue
        e, g = expected.get(f, "<absent>"), got.get(f, "<absent>")
        if e is None or g is None or e == g:
            continue
        if f in declared and (None in declared[f] or str(g) in declared[f] or g is True):
            continue
        out.append(f"{f}: served {e!r} vs job {g!r}")
    return out


def check_served(row, ctx):
    """Check 11 (RCA F2, mk_ak_row v2 schema): spec.served_ref = {registry_role, port, argv ({PORT}/{SLOTDIR}),
    argv_sha256, argv_delta[{flag, value, reason}], serving_shape, registry_sha256, orchestrator_commit, ...}. The
    served argv is rebuilt the way the generator builds it and diffed against both served_ref.argv and the job's
    llama-server argv; a delta not declared in argv_delta (with a reason) fails."""
    ref = row.spec.get("served_ref")
    argvs = server_argvs(row)
    if not ref:
        return [("WARN", "SERVED-REF-MISSING", "server row with no spec.served_ref: its argv is not tied to a served "
                                               "shape (mk_ak_row v2 writes it)")] if argvs else []
    if not isinstance(ref, dict) or not ref.get("registry_role"):
        return [("FAIL", "SERVED-REF-SPEC", "served_ref must carry registry_role (mk_ak_row v2 schema)")]
    role = ref["registry_role"]
    out = []
    declared = {}      # flag -> set of allowed values (None = any); arm-scoped and all-arm entries alike
    deltas = arm_deltas(row)
    if any(d.get("legacy") for d in deltas):
        out.append(("WARN", "ARM-DELTA-LEGACY", "spec.arm_argv_delta is the legacy form; write served_ref.argv_delta "
                                                "entries {arm, flag, value, reason} (mk_ak_row --arm-delta ARM:flag=value:reason)"))
    for dlt in deltas:
        if not dlt.get("flag"):
            continue
        if not str(dlt.get("reason") or "").strip():
            out.append(("FAIL", "SERVED-DELTA-UNREASONED", f"argv_delta {dlt['flag']} has no reason"))
            continue
        if "arm" in dlt and not str(dlt.get("arm") or "").strip():
            out.append(("FAIL", "SERVED-DELTA-SPEC", f"argv_delta {dlt['flag']}: empty arm"))
            continue
        v = dlt.get("value")
        declared.setdefault(str(dlt["flag"]), set()).add(None if v is None or v is True else str(v))
    sargv = ref.get("argv")
    if isinstance(sargv, list):
        if not ref.get("argv_sha256"):
            out.append(("FAIL", "SERVED-ARGV-SHA", "served_ref.argv_sha256 missing"))
        elif str(ref["argv_sha256"]).lower() != served_argv_sha256(sargv):
            out.append(("FAIL", "SERVED-ARGV-SHA", "served_ref.argv_sha256 != sha256(json.dumps(served_ref.argv)): the "
                                                   "argv was edited after generation"))
    if ref.get("registry_sha256"):
        try:
            if _sha256(REGISTRY) != str(ref["registry_sha256"]).lower():
                out.append(("WARN", "SERVED-REGISTRY-DRIFT", "the registry changed since served_ref was written "
                                                             "(registry_sha256 differs); regenerate the row"))
        except OSError:
            pass
    if ref.get("orchestrator_dirty"):
        out.append(("WARN", "SERVED-DIRTY", "served_ref was built from a dirty orchestrator checkout"))
    rebuilt, why = (None, "disabled") if ctx.get("rebuild") is False else rebuild_served_argv(role, ref.get("port"), ctx.get("flags"))
    job = argv_map([t for _f, _ln, a in argvs for t in a])
    if rebuilt is not None:
        if isinstance(sargv, list) and [str(x) for x in sargv] != rebuilt:
            stale = _diff(argv_map(rebuilt), argv_map(sargv), {}) or ["token order/content"]
            out.append(("FAIL", "SERVED-STALE", f"served_ref.argv differs from a fresh build of {role}: {stale[:3]}"))
        expected = argv_map(rebuilt)
    elif isinstance(sargv, list):
        expected = argv_map(sargv)
        out.append(("WARN", "SERVED-REBUILD", f"could not rebuild {role} ({why}); diffed against served_ref.argv"))
    else:
        reg = _registry(REGISTRY)
        entry = ((reg or {}).get("server_mode") or {}).get(role)
        if not isinstance(entry, dict):
            return out + [("FAIL", "SERVED-ROLE", f"registry has no server_mode.{role} and no served_ref.argv ({why})")]
        expected = {}
        for f, v in served_expect(entry).items():   # legacy: only the serving_shape-derived flags
            names = FLAG_ALIASES.get(f, (f,))
            got = next((n for n in names if n in job), None)
            expected[got or f] = v
        job = {f: v for f, v in job.items() if f in expected}
    if argvs:
        d = _diff(expected, job, declared)
        if d:
            out.append(("FAIL", "SERVED-DELTA", f"job argv vs served {role}: {d[:4]}" + (f" (+{len(d) - 4})" if len(d) > 4 else "")
                        + "; declare each in served_ref.argv_delta with a reason"))
    return out


GEN_STAMP_RX = re.compile(r"^#\s*GENERATED-BY:\s*(\S+)\s+(v\S+)\s+harness_sha256=([0-9a-f]{64})\b", re.M)


def check_generator(row, ctx):
    """Check 12 (WARN only; enforce candidate at 0 unstamped queued rows). Valid: the job.py line `# GENERATED-BY:
    mk_ak_row.py v2 harness_sha256=<sha of the vendored ak_row_harness.py>` OR spec.generator {tool: "mk_ak_row.py",
    version: "v2", harness_sha256[, profile: "polar"]} (polar rows: akloop/chain.py rewrites job.py, spec only)."""
    job = row.code.get("job.py")
    if job is None:
        return []
    hp = os.path.join(row.dir, "ak_row_harness.py")
    hsha = _sha256(hp) if os.path.isfile(hp) else None
    out = []
    m = GEN_STAMP_RX.search(job)
    stamp_ok = bool(m and os.path.basename(m.group(1)) == "mk_ak_row.py" and m.group(2) == "v2"
                    and (hsha is None or m.group(3) == hsha))
    if m and not stamp_ok:
        out.append(("WARN", "GENERATOR-HARNESS", "job.py GENERATED-BY stamp is not mk_ak_row.py v2 or its harness_sha256 "
                                                 "differs from the vendored ak_row_harness.py"))
    g = row.spec.get("generator")
    spec_ok = bool(isinstance(g, dict) and os.path.basename(str(g.get("tool") or "")) == "mk_ak_row.py"
                   and str(g.get("version") or "") == "v2" and re.fullmatch(r"[0-9a-f]{64}", str(g.get("harness_sha256") or ""))
                   and g.get("profile") in (None, "polar"))
    if isinstance(g, dict) and not spec_ok:
        out.append(("WARN", "GENERATOR-SPEC", f"spec.generator {g} is not {{tool: mk_ak_row.py, version: v2, harness_sha256"
                                              "[, profile: polar]}"))
    if not (stamp_ok or spec_ok):
        out.append(("WARN", "GENERATOR-UNSTAMPED", "neither a job.py `# GENERATED-BY: mk_ak_row.py v2 harness_sha256=<sha>` "
                                                   "stamp nor spec.generator (hand-built row; publish will refuse these later)"))
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
    if "import ak_gate" in (row.code.get("job.py") or "") and os.path.isfile(os.path.join(row.dir, "ak_gate.py")):
        return []   # a declared gate row: ak_gate.Gate.run appends every unit via ak_row_harness.append_unit (tested)
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
    stores = [store_root(s) for s in row_stores(row) if os.path.isdir(s)]
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


WITNESS_LV_MIN = 4
KNOBS_DECL_RX = re.compile(r"^KNOBS\s*=\s*(\[.*?\])", re.M)


def _job_knobs(row):
    out = []
    for f, t in row.code.items():
        m = KNOBS_DECL_RX.search(t)
        if m:
            try:
                out += [str(x) for x in ast.literal_eval(m.group(1))]
            except (ValueError, SyntaxError):
                pass
    return out


def _knob_witnesses(row):
    """Knob names the row declares a witness for: job.py KNOBS = [...] (mk_ak_row) plus spec.witness_lines[].line."""
    out = _job_knobs(row)
    wl = row.spec.get("witness_lines")
    if isinstance(wl, list):
        out += [str(w.get("line")) for w in wl if isinstance(w, dict) and w.get("line")]
    return out


def effective_log_level(row):
    """(found_any_server_argv, level|None): max -lv/--verbosity (--log-verbose = 99) over the job argv, served_ref.argv
    and served_ref.argv_delta."""
    argvs = [a for _f, _ln, a in server_argvs(row)]
    ref = row.spec.get("served_ref") or {}
    if isinstance(ref.get("argv"), list):
        argvs.append([str(x) for x in ref["argv"]])
    deltas = [d for d in (ref.get("argv_delta") or []) if isinstance(d, dict)]
    if deltas:
        argvs.append([t for d in deltas for t in (str(d.get("flag")), str(d.get("value"))) if t not in ("True", "None")])
    lv = None
    for a in argvs:
        m = argv_map(a)
        if "--log-verbose" in m:
            lv = 99
        for k in ("-lv", "--verbosity", "--log-verbosity"):
            v = m.get(k)
            if isinstance(v, str) and v.lstrip("-").isdigit():
                lv = max(lv or 0, int(v))
    return bool(argvs), lv


def check_witness_loglevel(row, ctx):
    ws = _knob_witnesses(row)
    if not ws:
        return []
    have, lv = effective_log_level(row)
    if not have or (lv is not None and lv >= WITNESS_LV_MIN):
        return []
    x = "none" if lv is None else f"-lv {lv}"
    return [("FAIL", "WITNESS-LOGLEVEL", f"WITNESS-LOGLEVEL: witness {ws[0]} needs -lv >= {WITNESS_LV_MIN}; argv has {x}")]

TOOL_BIN_RX = re.compile(r"^llama-(?:perplexity|bench|cli|batched-bench|completion|imatrix|server)$")


def tool_argvs(row):
    """[(file, lineno, binary, argv)] for every statically visible llama-binary argv in the job (python list/tuple literals whose
    argv names llama-perplexity/bench/cli/... and shell lines naming one), argv cut at the binary. llama-server included."""
    out = []
    for f, t in row.code.items():
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        aliases = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                b = _expr_binary(n.value, aliases)
                if b:
                    aliases[n.targets[0].id] = b
        for n in ast.walk(tree):
            if isinstance(n, (ast.List, ast.Tuple)) and n.elts:
                a = _const_list(n, aliases)
                k = next((i for i, x in enumerate(a) if TOOL_BIN_RX.match(os.path.basename(x))), None)
                if k is not None and any(x.startswith("-") and len(x) > 1 for x in a[k + 1:]):
                    out.append((f, n.lineno, os.path.basename(a[k]), a[k:]))
    for f, t in row.sh.items():
        for i, l in enumerate(re.sub(r"\\\n", " ", t).splitlines(), 1):
            m = re.search(r"llama-(?:perplexity|bench|cli|batched-bench|completion|imatrix|server)\b", l)
            if m and not l.lstrip().startswith("#"):
                out.append((f, i, m.group(0), l[m.start():].split()))
    return out


def _argv_lv(a):
    m = argv_map(a)
    if "--log-verbose" in m:
        return 99
    lv = None
    for k in ("-lv", "--verbosity", "--log-verbosity"):
        v = m.get(k)
        if isinstance(v, str) and v.lstrip("-").isdigit():
            lv = max(lv or 0, int(v))
        elif k in m and v is None:
            return 99   # a placeholder value: unknowable statically, do not guess
    return lv


def check_witness_loglevel_tools(row, ctx):
    """WITNESS-LOGLEVEL-TOOL: every llama-binary argv other than the server needs -lv >= 4 when a knob witness is declared
    (the server argv is witness_log's aggregate check, which also reads served_ref)."""
    ws = _knob_witnesses(row)
    if not ws:
        return []
    out = []
    for f, ln, binary, a in tool_argvs(row):
        if binary == "llama-server":
            continue
        lv = _argv_lv(a)
        if lv is None or lv < WITNESS_LV_MIN:
            x = "none" if lv is None else f"-lv {lv}"
            out.append(("FAIL", "WITNESS-LOGLEVEL-TOOL", f"WITNESS-LOGLEVEL: witness {ws[0]} needs -lv >= {WITNESS_LV_MIN} on "
                                                          f"{binary} ({f}:{ln}); argv has {x}"))
    return out


def check_witness_declared(row, ctx):
    ws = _job_knobs(row)
    gate = (row.spec.get("generator") or {}).get("profile") == "gate"   # ak_gate judges every marker (re: ones too) per arm
    if ws and not row.spec.get("witness_lines") and not gate:
        return [("FAIL", "WITNESS-UNDECLARED", f"knob witness {ws[0]} declared (job.py KNOBS) but spec.witness_lines is absent: "
                                               "declare [{line, needs, cap}] so the cap is checked against the binary")]
    return []


HEX64_RX = re.compile(r"(?<![0-9A-Fa-f])([0-9a-f]{64})(?![0-9A-Fa-f])")
_STR_RX = re.compile(r"[\"']([^\"'\n]{1,300})[\"']")
INPUTS_JOIN_RX = re.compile(r"[\"']inputs[\"']\s*,\s*[\"']([A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*)[\"']")
INPUTS_LIT_RX = re.compile(r"[\"']/?(inputs/[A-Za-z0-9._+/-]+)[\"']")
PIN_PATH_RX = re.compile(r"^[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*$")


def _rel_ok(rel):
    return bool(rel) and not rel.startswith(("/", "..", "-")) and ".." not in rel.split("/") and bool(PIN_PATH_RX.match(rel)) \
        and not rel.endswith(".gguf")


def pinned_inputs(row):
    """{rel_path: sha256 or None} the row pins, all relative to the row dir (see the `inputs` check)."""
    pins = {}
    for name in ("SHA256SUMS", "SOURCE.sha256"):
        t = _read(os.path.join(row.dir, name)) if row.dir else ""
        for ln in (t or "").splitlines():
            m = re.match(r"^\s*([0-9a-fA-F]{64})\s+\*?(\S+)\s*$", ln)
            if m and _rel_ok(m.group(2).lstrip("./") if m.group(2).startswith("./") else m.group(2)):
                pins[m.group(2)[2:] if m.group(2).startswith("./") else m.group(2)] = m.group(1).lower()
    def _pathlike(rel):
        return (_rel_ok(rel) and not HEX64_RX.fullmatch(rel) and not re.fullmatch(r"[\d.:]+", rel) and "://" not in rel
                and not re.match(r"^[\w.-]+:\d+$", rel)
                and ("/" in rel or re.search(r"\.[A-Za-z][A-Za-z0-9]{0,5}$", rel)))

    def _pathlit(txt):
        for sm in reversed(list(_STR_RX.finditer(txt))):
            rel = sm.group(1)
            rel = rel[1:] if rel.startswith("/inputs/") else rel   # HERE + "/inputs/x"
            if _pathlike(rel):
                return rel
        return None

    for t in row.code.values():
        for ln in t.splitlines():
            hm = HEX64_RX.search(ln)
            if not hm:
                continue
            nm = re.match(r"\s*([A-Za-z_]\w*?)_SHA(?:256)?\w*\s*=", ln)
            rel = None
            if nm:   # TEXT_SHA = '<hex>' pairs with TEXT / TEXT_PATH / TEXT_FILE = <path literal>
                pm = re.search(r"^\s*%s(?:_PATH|_FILE)?\s*=\s*(.*)$" % re.escape(nm.group(1)), t, re.M)
                rel = _pathlit(pm.group(1)) if pm else None
            # no same-line pairing: a hex inside an argv list / long string (--chat-template-sha <hex> ... 127.0.0.1) is not a file pin
            if rel:
                pins.setdefault(rel, hm.group(1))
    for t in list(row.code.values()) + list(row.sh.values()):
        for rx in (INPUTS_LIT_RX,):
            for m in rx.finditer(t):
                pins.setdefault(m.group(1), None)
        for m in INPUTS_JOIN_RX.finditer(t):
            pins.setdefault("inputs/" + m.group(1), None)
    return pins


def check_inputs(row, ctx):
    out = []
    if not row.dir:
        return out
    for rel, want in sorted(pinned_inputs(row).items()):
        p = os.path.join(row.dir, rel)
        if not os.path.isfile(p):
            out.append(("FAIL", "INPUT-MISSING", f"{rel}: pinned input is absent in the row dir {row.dir} (copy it in before publish)"))
        elif want and _sha256(p) != want:
            out.append(("FAIL", "INPUT-SHA", f"{rel}: sha256 {str(_sha256(p))[:16]} != pinned {want[:16]}"))
    return out


# ---------------------------------------------------------------- replay gates (R1 receipt, R4 replay smoke)
# docs/design/ak-waste-audit-20261125.md §3 R1/R4 + pipeline-mgmt gate harness 2026-11-25 (trimmed after the Fable review
# /mnt/raid0/llm/tmp/review-akgate-20261125.md F1-F8). A -rN republish of a family whose LAST smoke FAILED must show that
# the NEW decision path, run offline on the failed run's real out/, reaches a DIFFERENT failure: "your fix does not change
# the verdict on the log it failed on" is the refusal. The receipt IS the replay preflight runs itself (R4: job.py
# --decide-from <prior out>, nice 19, cpus 84-87, 60 s); the agent never writes one (job.py --replay is the local fix loop).
# Not replayable (never a refusal; R2 family strikes are the backstop): server / timeout / stop / residency / input failures
# an offline replay cannot witness. A witness failure is the same failure only while a prior (knob, arm) is still missing.
# A new job sha alone is never evidence (no fresh_attempt bypass); spec.fix_ref {store, reason} naming a kernel store the
# failed run did not use is the one escape (the fix is in the binary, so the old log cannot show it).
REPLAY_PIN = ("/usr/bin/nice", "-n", "19", "/usr/bin/taskset", "-c", "84-87")
REPLAY_TIMEOUT_S = 60
# ak_gate verdict token -> fine class (read FIRST); the free-text regexes below are the fallback for hand-rolled rows
TOKEN_CLASS = (("NONDET", "nondet"), ("WITNESS", "witness"), ("CORRECTNESS", "correctness"), ("_AA", "aa"),
               ("MISSING_INPUT", "input"), ("RESIDENCY", "residency"), ("SERVER", "server"), ("TIMEOUT", "server"),
               ("STOPPED", "server"), ("MISSING_OUTPUT", "output"))
VERDICT_TOKEN_RX = re.compile(r"\b((?:FUTILITY|FAIL)_[A-Z0-9_]+)\b")
NOT_REPLAYABLE = ("server", "input", "residency")
FINE_CLASS_RX = (("witness", re.compile(r"WITNESS|witness")),
                 ("nondet", re.compile(r"NONDET|nondetermin", re.I)),
                 ("correctness", re.compile(r"CORRECTNESS|MISMATCH|identity|output_eq|\bKLD\b")),
                 ("aa", re.compile(r"_AA\b|\bA/A\b")),
                 ("input", re.compile(r"MISSING_INPUT|input \S+ missing|No such file|INPUT-MISSING")),
                 ("residency", re.compile(r"RESIDENCY|VRAM")),
                 ("server", re.compile(r"not ready|server exited|_SERVER\b|ServerDied|Connection refused")))
PAIR_RX = re.compile(r"knob ([A-Za-z0-9_.()-]+) arm ([A-Za-z0-9_.-]+)")
FALSE_KNOB_RX = re.compile(r"['\"]((?:GGML|LLAMA)_[A-Z0-9_]+)['\"]\s*:\s*False")


def _is_ak(row):
    return row.owner.startswith("autokernel") or row.id.startswith("ak-")


def _iso_or_mtime(rec, p):
    try:
        import rowflow as rf
        t = rf.iso_epoch((rec or {}).get("at"))
        if t:
            return float(t)
    except Exception:  # noqa: BLE001
        pass
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def family_ids(flags, rid):
    """Ids sharing rid's id_stem (rowflow.id_stem: dates / -rN stripped) with a dryrun dir or a ready manifest."""
    import rowflow as rf
    stem = rf.id_stem(rid)
    ids = {rid}
    for p in glob.glob(os.path.join(flags, "dryrun", "*")) + glob.glob(os.path.join(flags, "ready", "*.json")):
        oid = os.path.basename(p)[:-5] if p.endswith(".json") else os.path.basename(p)
        if rf.id_stem(oid) == stem:
            ids.add(oid)
    return ids


def family_last_smoke(flags, rid):
    """The newest smoke outcome of rid's family: {kind: PASS|FAIL, id, path, at} or None. Arming/launch FAILs (allocator
    records, rowflow.is_arm_fail) are not smoke outcomes."""
    import rowflow as rf
    recs = []
    for fid in family_ids(flags, rid):
        pp = rf.pass_path(flags, fid)
        if os.path.isfile(pp):
            recs.append((_iso_or_mtime(_load_json(pp), pp), "PASS", fid, pp))
        for fp in rf.fail_paths(flags, fid):
            f = _load_json(fp) or {}
            if not rf.is_arm_fail(f):
                recs.append((_iso_or_mtime(f, fp), "FAIL", fid, fp))
    if not recs:
        return None
    t, kind, fid, p = max(recs)
    return {"kind": kind, "id": fid, "path": p, "at": t}


def _manifest(flags, fid):
    import rowflow as rf
    return _load_json(rf.ready_path(flags, fid)) or _load_json(os.path.join(rf.dry_dir(flags, fid), "unpublished.json")) or {}


def prior_out(flags, fid):
    """The out/ dir of run `fid` (its manifest scratch_root, else <tmp>/<fid>) when it holds anything a replay reads."""
    root = str(_manifest(flags, fid).get("scratch_root") or os.path.join(TMP_ROOT, fid))
    out = os.path.join(root, "out")
    for p in (os.path.join(out, "results.jsonl"), os.path.join(out, "logs"), os.path.join(root, "out-smoke", "results.jsonl"),
              os.path.join(out, "TERMINAL-smoke.json")):
        if os.path.exists(p):
            return out
    return None


def family_prior_outs(flags, rid):
    """[(mtime, fid, out_dir)] of the family's OTHER runs that left an out/, newest first."""
    out = []
    for fid in family_ids(flags, rid) - {rid}:
        o = prior_out(flags, fid)
        if o:
            out.append((os.path.getmtime(o), fid, o))
    return sorted(out, reverse=True)


def _token_class(text):
    for tok in VERDICT_TOKEN_RX.findall(text or ""):
        for frag, cls in TOKEN_CLASS:
            if frag in tok:
                return cls
    return None


def _fine_class(text):
    """F4: the ak_gate verdict token is the class; the free-text regex is only the fallback."""
    tc = _token_class(text)
    if tc:
        return tc
    for name, rx in FINE_CLASS_RX:
        if rx.search(text or ""):
            return name
    return None


def _failclass_mod():
    try:
        import rowflow as rf
        return rf._failclass_mod()
    except Exception:  # noqa: BLE001
        return None


def prior_pairs(text):
    """{(knob, arm|None)} a recorded witness failure names: ak_gate 'knob K arm A' lines, else a hand-rolled {'K': False}."""
    pairs = {(k, a) for k, a in PAIR_RX.findall(text or "")}
    return pairs or {(k, None) for k in FALSE_KNOB_RX.findall(text or "")}


def prev_failure_class(flags, fid, fail_path):
    """{key: side:klass (akloop/failclass.classify_fail), fine, pairs, text} of a recorded smoke FAIL."""
    import rowflow as rf
    rec = _load_json(fail_path) or {}
    lo = _read(os.path.join(rf.dry_dir(flags, fid), "launcher.out")) or ""
    out = prior_out(flags, fid)
    term = _load_json(os.path.join(out, "TERMINAL-smoke.json")) if out else None
    smoke_lines = "\n".join(ln for ln in lo.splitlines() if "SMOKE FAIL" in ln or "FUTILITY" in ln)[-2000:]
    text = " ".join([str((term or {}).get("reason") or ""), str(rec.get("reason") or ""), smoke_lines])
    key = None
    fc = _failclass_mod()
    if fc is not None:
        try:
            c = fc.classify_fail(dict(rec, id=fid), lo)
            key = f"{c.side}:{c.klass}"
        except Exception:  # noqa: BLE001
            key = None
    return {"key": key, "fine": _fine_class(text), "pairs": prior_pairs(text), "text": text[:600]}


def observed_class(observed, pairs=()):
    """The replayed verdict's class. ok = not a failure (pass / keep / measured NO_KEEP / INCOMPLETE: the replay ran past
    the prior failure point) OR not replayable offline (server / timeout / stop / residency / input: F1)."""
    v = str((observed or {}).get("verdict") or "")
    fine = _fine_class(v) or _fine_class(str((observed or {}).get("reason") or ""))
    key = None
    fc = _failclass_mod()
    if fc is not None:
        try:
            c = fc.classify_result({"verdict": v, "polar": (observed or {}).get("polar"), "complete": True})
            key = f"{c.side}:{c.klass}"
        except Exception:  # noqa: BLE001
            key = None
    passed = v.startswith(("KEEP", "SMOKE_PASS", "PASS", "NO_KEEP", "INCOMPLETE")) or (observed or {}).get("polar") == "PASS"
    nr = fine in NOT_REPLAYABLE
    return {"key": key, "fine": None if passed else fine, "ok": passed or nr, "not_replayable": nr and not passed,
            "pairs": {tuple(p) for p in pairs}}


def same_failure_class(prev, obs):
    """True when the replayed verdict is the SAME failure as the recorded one. A replay that no longer fails (or cannot
    judge it offline) never is; witness vs witness is the same only while a prior (knob, arm) is still missing; another
    fine class on both sides decides by equality; otherwise the failclass side:klass keys (unknown never matches)."""
    if obs.get("ok"):
        return False
    if prev.get("fine") == obs.get("fine") == "witness" and prev.get("pairs"):
        return any((k, a) in obs["pairs"] or (a is None and any(k == ok for ok, _a in obs["pairs"]))
                   for k, a in prev["pairs"])
    if prev.get("fine") and obs.get("fine"):
        return prev["fine"] == obs["fine"]
    k1, k2 = prev.get("key"), obs.get("key")
    return bool(k1 and k2 and k1 == k2 and not k1.startswith("unknown"))


def _job_supports_replay(row):
    job = row.code.get("job.py") or ""
    return "--decide-from" in job or "import ak_gate" in job


def run_replay_decide(row, prior_out_dir, flags=None, pin=REPLAY_PIN, timeout=REPLAY_TIMEOUT_S):
    """job.py --decide-from <prior out> under nice 19 / taskset 84-87, `timeout` s: {rc, ...DECIDE} or {error} (never raises)."""
    job = os.path.join(row.dir, "job.py")
    env = {"PATH": "/usr/bin:/bin", "HIP_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1"}
    if flags:
        env["ROWFLOW_FLAGS"] = flags
    t0 = __import__("time").time()
    try:
        p = subprocess.run(list(pin) + [sys.executable, "-I", "-B", job, "--decide-from", prior_out_dir], cwd=row.dir,
                           env=env, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"rc": None, "error": f"{type(e).__name__}: {e}"}
    line = next((ln for ln in reversed(p.stdout.splitlines()) if ln.startswith("DECIDE ")), None)
    out = {"rc": p.returncode, "elapsed_s": round(__import__("time").time() - t0, 2), "prior_out": prior_out_dir,
           "stderr_tail": (p.stderr or "")[-300:]}
    if not line:
        return dict(out, error="no DECIDE line on stdout")
    try:
        d = json.loads(line[len("DECIDE "):])
    except ValueError:
        return dict(out, error="DECIDE line is not JSON")
    if d.get("error"):
        return dict(out, error=d["error"])
    return dict(out, **d)


def judge_replay(flags, row, r, last, code):
    """[(level, code, msg)] for a replay result `r` against the family's last smoke `last` (code = REPLAY-DECIDE or
    REPLAY-RECEIPT): no units, no witnessed unit, a removed correctness gate, or the same failure class."""
    obs = r.get("observed") or {}
    prev = prev_failure_class(flags, last["id"], last["path"]) if last and last["kind"] == "FAIL" else None
    oc = observed_class(obs, r.get("mismatch_pairs") or ())
    r.update(prev_failclass={k: (sorted(v) if isinstance(v, set) else v) for k, v in (prev or {}).items()} or None,
             observed_class={k: (sorted(v) if isinstance(v, set) else v) for k, v in oc.items()})
    if int(r.get("n_units") or 0) == 0:
        return [("FAIL", f"{code}-NO-UNITS", f"the replay of {r.get('prev_id')}'s out/ judged 0 units (skipped logs "
                                             f"{(r.get('skipped_logs') or [])[:4]}): an empty replay proves nothing")]
    if "n_witnessed" in r and int(r["n_witnessed"] or 0) == 0 and not oc["not_replayable"]:
        return [("FAIL", f"{code}-NO-UNITS", f"the replay of {r.get('prev_id')}'s out/ witnessed 0 of {r.get('n_units')} units")]
    if not prev:
        return []
    if prev.get("fine") == "correctness" and "correctness_kind" in r and not r.get("correctness_kind"):
        return [("FAIL", f"{code}-GATE-REMOVED", f"{last['id']} failed its correctness unit and the new declaration has no "
                                                 "correctness unit: removing the gate is not a fix")]
    if same_failure_class(prev, oc):
        return [("FAIL", f"{code}-SAME-CLASS", f"replaying the new decide() on {last['id']}'s out/ gives {obs.get('verdict')} "
                                               f"- the same failure as its smoke FAIL ({prev.get('fine') or prev.get('key')}"
                                               f"{' ' + str(sorted(prev['pairs'] & oc['pairs'] or prev['pairs'])) if prev.get('pairs') else ''}"
                                               "): your fix does not change the verdict on the log it failed on")]
    return []


def check_replay_decide(row, ctx):
    """R4: the new decide() replayed on the family's newest prior out/ must run, judge >= 1 witnessed unit, name a verdict,
    and (when that run's smoke FAILED last) not reproduce the same failure. Legacy jobs without --decide-from: WARN."""
    flags = ctx.get("flags")
    if not flags or not row.dir or not _is_ak(row) or "job.py" not in row.code:
        return []
    priors = family_prior_outs(flags, row.id)
    if not priors:
        return []
    last = family_last_smoke(flags, row.id)
    pick = next((p for p in priors if last and p[1] == last["id"]), priors[0])
    if not _job_supports_replay(row):
        return [("WARN", "REPLAY-DECIDE-UNSUPPORTED", f"family has a prior out/ ({pick[1]}) but job.py has no --decide-from "
                                                      "entry point (mk_ak_row v2 template / ak_gate rows have one)")]
    r = run_replay_decide(row, pick[2], flags)
    r["prev_id"] = pick[1]
    ctx.setdefault("replay_decide", {})[row.id] = r
    if r.get("error") or r.get("rc") not in (0,):
        return [("FAIL", "REPLAY-DECIDE-CRASH", f"job.py --decide-from {pick[2]} failed (rc {r.get('rc')}): "
                                                f"{r.get('error') or r.get('stderr_tail')}"[:400])]
    if not str((r.get("observed") or {}).get("verdict") or "").strip():
        return [("FAIL", "REPLAY-DECIDE-NO-VERDICT", f"job.py --decide-from {pick[2]} returned no verdict")]
    return judge_replay(flags, row, r, last if last and last["id"] == pick[1] else None, "REPLAY-DECIDE")


def _fix_ref_ok(row, flags, last):
    fr = row.spec.get("fix_ref")
    if not isinstance(fr, dict) or not str(fr.get("reason") or "").strip() or not fr.get("store"):
        return False
    prev = Row(_manifest(flags, last["id"]))
    prev_stores = {os.path.realpath(s) for s in row_stores(prev)} if prev.dir else set()
    st = os.path.realpath(str(fr["store"]))
    return os.path.isdir(st) and st not in prev_stores


def check_replay_receipt(row, ctx):
    """R1: a republish of a family whose LAST smoke FAILED needs a receipt = this preflight's own replay (replay_decide) of
    that failed run's out/, judged by judge_replay. spec.fix_ref naming a new kernel store is the one escape; a failed run
    that left no out/ cannot be replayed (WARN; R2 strikes are the backstop)."""
    flags = ctx.get("flags")
    if not flags or not _is_ak(row):
        return []
    last = family_last_smoke(flags, row.id)
    if not last or last["kind"] != "FAIL":
        return []
    if _fix_ref_ok(row, flags, last):
        return [("WARN", "REPLAY-RECEIPT-FIXREF", f"family's last smoke FAILED ({last['id']}); accepted on spec.fix_ref "
                                                  f"{row.spec['fix_ref'].get('store')} (a kernel store the failed run did not use)")]
    po = prior_out(flags, last["id"])
    if not po:
        return [("WARN", "REPLAY-RECEIPT-NO-PRIOR-OUT", f"family's last smoke FAILED ({last['id']}) and left no out/ to replay")]
    r = (ctx.get("replay_decide") or {}).get(row.id)
    if not r or r.get("prev_id") != last["id"] or not r.get("observed"):
        return [("FAIL", "REPLAY-RECEIPT-MISSING", f"family's last smoke FAILED ({last['id']}, {os.path.basename(last['path'])}) "
                                                   "and no replay of its out/ ran: job.py needs a --decide-from entry point "
                                                   "(mk_ak_row gate new / v2 rows); fix locally with "
                                                   f"`python3 -I -B {os.path.join(row.dir or '<row>', 'job.py')} --replay {po}`")]
    return judge_replay(flags, row, dict(r), last, "REPLAY-RECEIPT")


def replay_receipt_verdict(spec, flags, row_dir=None):
    """Hook for publish_row's family gate (republish_allowed): (ok, [messages]) from the R4 replay + R1 receipt checks."""
    row = Row(spec, row_dir)
    ctx = {"flags": flags}
    res = check_replay_decide(row, ctx) + check_replay_receipt(row, ctx)
    return not any(l == "FAIL" for l, _c, _m in res), [f"{l} {c}: {m}" for l, c, m in res]


CHECK_FNS = {"selftest": check_selftest, "store": check_store, "flags": check_flags, "model": check_model,
             "lane": check_lane, "smoke": check_smoke, "estimate": check_estimate, "ports": check_ports,
             "append": check_append, "witness": check_witness, "witness_log": check_witness_loglevel,
             "witness_decl": check_witness_declared, "witness_log_tools": check_witness_loglevel_tools,
             "served": check_served, "inputs": check_inputs,
             "generator": check_generator, "replay_decide": check_replay_decide,
             "replay_receipt": check_replay_receipt}


# ---------------------------------------------------------------- runners
# Publish-only checks: they judge what the row DECLARES before its smoke has run. A row whose smoke already PASSED ran the real
# binary and found the witness, which is stronger evidence, so report / keeper-side use grandfathers it (grandfather=True);
# publish never does (its new id has no PASS). Operator-adjacent origin: AutoKernel report 2026-11-24 23:2xZ.
PUBLISH_ONLY = ("witness_log", "witness_decl", "witness_log_tools", "inputs", "replay_decide", "replay_receipt")


def smoke_pass_date(flags, spec):
    """'YYYY-MM-DD' of the row's PASS.json (dryrun/<id>/) when it exists and, if both name a launcher sha, matches; else None."""
    rid = str((spec or {}).get("id") or "")
    if not (flags and rid):
        return None
    p = os.path.join(flags, "dryrun", rid, "PASS.json")
    d = _load_json(p)
    if not isinstance(d, dict):
        return None
    want = str(((spec or {}).get("launcher") or {}).get("sha256") or "")
    if want and d.get("launcher_sha256") and not str(d["launcher_sha256"]).startswith(want[:16]) and not want.startswith(str(d["launcher_sha256"])[:16]):
        return None   # PASS belongs to an older launcher: republish re-smokes, so it is not evidence for this one
    t = str(d.get("first_unit_at") or d.get("at") or "")
    if len(t) >= 10 and t[4] == "-":
        return t[:10]
    try:
        import time as _t
        return _t.strftime("%Y-%m-%d", _t.gmtime(os.path.getmtime(p)))
    except OSError:
        return None


def run(spec, row_dir=None, flags=None, queued=None, checks=CHECKS, run_selftest=False, nodes=None, vram=None, rebuild=True,
        grandfather=False, ctx_out=None):
    """[(check, raw_level, code, msg)] for one row. Never raises: a crashing check is reported as a WARN.
    grandfather=True: PUBLISH_ONLY checks on a row whose smoke PASSED report one PASS line instead of re-judging it."""
    row = Row(spec, row_dir)
    gf = smoke_pass_date(flags, spec) if grandfather else None
    ctx = {"flags": flags, "queued": queued, "run_selftest": run_selftest, "nodes": nodes, "vram": vram, "rebuild": rebuild,
           "history": rebuild}
    if ctx_out is not None:
        ctx_out["replay_decide"] = ctx.setdefault("replay_decide", {})   # shared: publish_check records the R4 replay
    out = []
    for c in checks:
        if gf and c in PUBLISH_ONLY:
            out.append((c, "PASS", "GRANDFATHERED", f"PASS (grandfathered: smoke PASS {gf})"))
            continue
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


def report_scope(flags):
    """({id: manifest} really queued, {id: reason} excluded). Queued = ready manifest or pending dry run (supersedes_check.live_ids),
    not ended/complete/filed, not superseded (ready/.superseded/ marker, or named in a live row's `supersedes`), not STOP-held."""
    import rowflow as rf
    import supersedes_check as SC
    base = queued_rows(flags)
    allrows = rf.rows(flags)
    G = os.path.join(flags, "grants")
    live = SC.live_ids(flags)
    markers = SC.superseded_markers(flags)
    named = {}
    for rid in live:
        for pred in SC._sup_list(allrows.get(rid) or {}):
            named.setdefault(pred, rid)
    queued, excl = {}, {}
    for rid, d in sorted(base.items()):
        if any(os.path.exists(os.path.join(G, rid + e)) for e in (".ended", ".complete")):
            excl[rid] = "ended/complete"
        elif rid in markers:
            excl[rid] = f"superseded by {markers[rid]}"
        elif rid in named:
            excl[rid] = f"superseded by {named[rid]}"
        elif rid not in live:
            excl[rid] = "not live (no ready manifest / pending dry run)"
        else:
            sf = None
            try:
                sf = rf.resolve_stop_path(d)
            except Exception:  # noqa: BLE001
                pass
            if sf and os.path.exists(sf):
                excl[rid] = f"STOP-held ({sf})"
            else:
                queued[rid] = d
    return queued, excl


def publish_check(spec, flags, warn=print, queued=None):
    """publish_row hook: effective FAILs raise rowflow.Refused; every raw FAIL/WARN is reported through warn()."""
    import rowflow as rf
    if queued is None:
        try:
            queued = queued_rows(flags)
        except Exception:  # noqa: BLE001
            queued = {}
    ctx_out = {}
    res = run(spec, flags=flags, queued=queued, ctx_out=ctx_out)
    if ctx_out.get("replay_decide"):
        spec.setdefault("preflight", {})["replay_decide"] = ctx_out["replay_decide"].get(str(spec.get("id")))
    eff = effective(res)
    for raw, f in zip(res, eff):
        warn(fmt(f) + (" (would FAIL if enforced; publish continues)" if raw[1] == "FAIL" and f[1] != "FAIL" else ""))
    fails = [fmt(f) for f in eff if f[1] == "FAIL"]
    if fails:
        raise rf.Refused("preflight: " + "; ".join(fails))
    return res


def grant_check(flags, rid, d, queued=None):
    """Allocator hook (just before a grant is written): DRIFT_CHECKS only. Returns (hold_reason or None, lines)."""
    # no orchestrator rebuild / history scan inside an allocator tick: served diffs against served_ref.argv here
    res = effective(run(d, flags=flags, queued=queued or {}, checks=DRIFT_CHECKS, rebuild=False))
    lines = [fmt(f) for f in res if f[1] in ("FAIL", "WARN")]
    fails = [fmt(f) for f in res if f[1] == "FAIL"]
    return ("preflight: " + "; ".join(fails)[:600]) if fails else None, lines


def report(flags, as_json=False, out=print, queued=None):
    """Per check: how many queued rows would FAIL it (raw), and which; WARN counts too. The evidence for flipping."""
    excl = {}
    if queued is None:
        queued, excl = report_scope(flags)
    nodes = node_map()
    per = {c: {"fail": [], "warn": [], "enforced": PREFLIGHT_ENFORCE.get(c, False)} for c in CHECKS}
    detail = {}
    for rid in sorted(queued):
        res = run(queued[rid], flags=flags, queued=queued, nodes=nodes, grandfather=True)
        detail[rid] = [list(f) for f in res]
        for c in CHECKS:
            lv = {l for cc, l, _code, _m in res if cc == c}
            if "FAIL" in lv:
                per[c]["fail"].append(rid)
            elif "WARN" in lv:
                per[c]["warn"].append(rid)
    if as_json:
        out(json.dumps({"queued": len(queued), "excluded": excl, "checks": per, "detail": detail}, indent=1))
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
    if excl:
        out(f"EXCLUDED {len(excl)} row(s) (not queued, not counted):")
        for rid, why in excl.items():
            out(f"    {rid}: {why}")
    return per


def rule_rollout_report(flags, as_json=False, out=print, queued=None):
    """Count queued raw failures per warn-only check, using report's scope and grandfathering."""
    per = report(flags, as_json=True, out=lambda _text: None, queued=queued)
    counts = {c: len(per[c]["fail"]) for c in CHECKS if not PREFLIGHT_ENFORCE.get(c, False)}
    if as_json:
        out(json.dumps(counts, indent=1))
    else:
        out("PREFLIGHT ROLLOUT (rule changes frozen during AK pushes)")
        for c, count in counts.items():
            out(f"{c}: failing={count}" + (" READY TO ENFORCE" if count == 0 else ""))
    return counts


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", nargs="*")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true")
    mode.add_argument("--rollout", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--flags", default=None)
    a = ap.parse_args(argv)
    import rowflow as rf
    flags = a.flags or rf.FLAGS
    if a.rollout:
        rule_rollout_report(flags, as_json=a.json)
        return 0
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
