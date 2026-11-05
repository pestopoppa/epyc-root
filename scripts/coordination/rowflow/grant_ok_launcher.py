#!/usr/bin/python3 -I
"""grant_ok_launcher.py -- launcher-side half of grant_ok.v2.sh (CTC-Q-A2 + class/region match).

workspace-58 (calendar owner), 2026-10-23.  Read-only: reads FILLERS.md and /proc/<pid>/{stat,cmdline};
never signals, never writes.  Called by grant_ok.v2.sh; run it with /usr/bin/python3 -I -B.

    grant_ok_launcher.py --row ID [--pid P] [--window-s N] [--regions R] [--reserve R]
                         [--derived-class C] [--fillers FILE] [--proc ROOT]

Finds the launcher of ROW: --pid, else the row's `pid=` (validate_fillers.launcher_pid).  If that pid is a
wrapper (`bash -c '... launch.sh ...'`, a subshell that ran `setsid nohup bash launch.sh`), the nearest live
descendant whose argv is a filler_run*.sh engine with `--id ROW` (and not `--inner`) is the launcher.
Its argv is parsed exactly as filler_run{,2..8}.sh parse it (--min-window --class --claim-cpus --gpu-quiet
--no-fold-siblings --self-claim --gpu-threads ...), then:

  window   --window-s N must be >= min-window + 300 s (poll lag; three exactly-equal windows refused rc=3)
  regions  --regions R must survive the launcher's own parse_regions() for its --class (else it writes
           .ended rc=2), and every region the launcher's region-lock claim takes (its --cpu-list folded
           onto quarters, plus gpu-quiet) must be in R (mi210_0 = gpu-quiet) or in --reserve (regions the
           writer's claim-wait keeps free besides the grant, e.g. `gpu-quiet` for a CPU timing job that
           claims gpu-quiet exclusive, `0-95` for a GPU job whose claim is the whole host).

Exit / first stdout line
  0   ok: `launcher=... minwin=... claim=... [warn=...]`
  10  refuse: row not QUEUED (status != ARMED or ready != y; the validator's --for-grant passes a well-formed
      BACKLOG or COMPLETE row, so the legacy gate admits it)
  12  refuse: window short
  13  refuse: class/region mismatch (parse_regions refuses, claim not covered, no-fold SMT-only claim,
      unknown region token)
  14  refuse: launcher dead (no pid, /proc/<pid> missing or zombie, or a wrapper whose engine is gone)
  12  also: the launcher's --precond-cmd fails (run last, as the engine runs it): `not ready: precond-cmd failed: CMD`
  15  refuse: launcher argv unrecognised (no filler engine with --id ROW under the pid; --regions needs one)
  64  usage
Test override: --proc ROOT (a directory of <pid>/cmdline + <pid>/stat fixtures).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
# rowflow v4 (2026-11-01): the row is compute-flags/ready/<id>.json (epyc.row.v3) + dryrun/<id>/ARMED.json; no FILLERS.md.
def _v3_row(flags_dir, row):
    import json as _j
    try: m = _j.load(open(os.path.join(flags_dir, 'ready', row + '.json')))
    except Exception: m = {}
    try: a = _j.load(open(os.path.join(flags_dir, 'dryrun', row, 'ARMED.json')))
    except Exception: a = {}
    return m if isinstance(m, dict) else {}, a if isinstance(a, dict) else {}


MARGIN_S = 300
PRECOND_TIMEOUT_S = 30
ENGINE_RE = re.compile(r"^filler_run\d*\.sh$")
VALUE_FLAGS = {"--id", "--class", "--cmd", "--min-window", "--stop", "--stop-grace", "--complete-cmd", "--port",
               "--sched-port", "--excl-lock", "--gpu-threads", "--workdir", "--gpu-quiet", "--role",
               "--claim-cpus", "--precond-cmd",
               "--requires-tool", "--qual-interpreter"}  # ws58 2026-11-01: engine v14/v15 (D1 canonical) passes repeatable --requires-tool
BOOL_FLAGS = {"--self-claim", "--repeat", "--no-fold-siblings"}
LIST_RE = re.compile(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")
QUARTERS = ("q0", "q1", "q2", "q3")


class Refuse(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- /proc (read-only)
def read_cmdline(root: str, pid: int) -> list[str] | None:
    try:
        with open(f"{root}/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except OSError:
        return None
    if not raw:
        return []
    # keep EMPTY arguments (e.g. `--port ''`): dropping them shifted every later flag by one and made a live
    # engine read as "a wrapper with no engine" (hsf-5p-build / akx-lb3-2, 2026-10-24). Only the trailing NUL goes.
    parts = raw.split(b"\0")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return [a.decode("utf-8", "replace") for a in parts]


def read_stat(root: str, pid: int) -> tuple[str, int] | None:
    """(state, ppid) or None.  comm may contain spaces/parens: split after the LAST ')'."""
    try:
        with open(f"{root}/{pid}/stat", encoding="utf-8", errors="replace") as f:
            s = f.read()
    except OSError:
        return None
    rest = s[s.rfind(")") + 1:].split()
    if len(rest) < 2:
        return None
    try:
        return rest[0], int(rest[1])
    except ValueError:
        return None


def alive(root: str, pid: int) -> bool:
    st = read_stat(root, pid)
    return st is not None and st[0] not in ("Z", "X", "x")


def children_map(root: str) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    try:
        names = os.listdir(root)
    except OSError:
        return out
    for n in names:
        if not n.isdigit():
            continue
        st = read_stat(root, int(n))
        if st is not None and st[0] not in ("Z", "X", "x"):
            out.setdefault(st[1], []).append(int(n))
    for v in out.values():
        v.sort()
    return out


# ---------------------------------------------------------------- launcher argv (mirrors filler_run*.sh)
def parse_engine(argv: list[str]) -> dict | None:
    """The engine's options if argv runs a filler_run*.sh engine, else None.  Mirrors its while/case."""
    idx = next((i for i, a in enumerate(argv) if ENGINE_RE.match(os.path.basename(a))), None)
    if idx is None:
        return None
    o = {"engine": os.path.basename(argv[idx]), "engine_path": argv[idx], "inner": False, "id": "", "class": "", "min_window": 0,
         "claim_cpus": "", "gpu_quiet": "", "nofold": False, "self_claim": False, "gpu_threads": "184-191",
         "role": "", "workdir": "/workspace", "precond_cmd": ""}
    rest = argv[idx + 1:]
    if rest[:1] == ["--inner"]:
        o["inner"] = True
        rest = rest[1:]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in VALUE_FLAGS:
            if i + 1 >= len(rest):
                return None
            v = rest[i + 1]
            key = {"--min-window": "min_window", "--claim-cpus": "claim_cpus", "--gpu-quiet": "gpu_quiet",
                   "--gpu-threads": "gpu_threads", "--precond-cmd": "precond_cmd"}.get(a, a[2:])
            if key == "min_window":
                try:
                    v = int(v)
                except ValueError:
                    return None
            o[key] = v
            i += 2
        elif a in BOOL_FLAGS:
            o[{"--self-claim": "self_claim", "--no-fold-siblings": "nofold"}.get(a, a[2:])] = True
            i += 1
        else:
            # 2026-11-03 session review item 7: an unknown flag is the PARSER lagging the engine, not proof that this is
            # no engine (the live poller already logged 'launcher up pid='); recorded, skipped, never a rc=15 refusal.
            o.setdefault("unknown", []).append(a)
            i += 1
    return o


def find_launcher(root: str, pid: int, row: str) -> tuple[dict | None, int, list[str]]:
    """(engine options, engine pid, argv of `pid`).  BFS from pid over live descendants (depth <= 6)."""
    own = read_cmdline(root, pid) or []
    kids = None
    frontier, depth, seen = [pid], 0, {pid}
    while frontier and depth <= 6:
        nxt = []
        for p in frontier:
            argv = own if p == pid else (read_cmdline(root, p) or [])
            o = parse_engine(argv)
            if o and not o["inner"] and o["id"] == row:
                return o, p, own
            if p == pid and o and not o["inner"] and o["id"] != row:
                raise Refuse(15, f"pid {pid} is the {o['engine']} launcher of {o['id']!r}, not {row!r}")
            if kids is None:
                kids = children_map(root)
            for c in kids.get(p, []):
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier, depth = nxt, depth + 1
    return None, 0, own


# ---------------------------------------------------------------- regions (mirrors parse_regions + rlargs)
def expand(lst: str) -> list[int]:
    out: list[int] = []
    for t in lst.split(","):
        if "-" in t:
            a, b = t.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        elif t:
            out.append(int(t))
    return out


def quarter_cpus(n: int) -> str:
    a = n * 24
    return f"{a}-{a + 23},{a + 96}-{a + 96 + 15}"  # the engines' own expansion (16 siblings)


def parse_regions(regions: str, cls: str, gputhr: str) -> str:
    """The engine's parse_regions(): returns CPUS, or raises Refuse(13) where the engine writes .ended rc=2."""
    gpu, qs, lst, unknown = False, [], [], []
    for tok in regions.replace(";", ",").split(","):
        if tok == "mi210_0":
            gpu = True
        elif re.fullmatch(r"q[0-3]", tok):
            qs.append(int(tok[1]))
        elif tok[:1].isdigit():
            lst.append(tok)
        elif tok:
            unknown.append(tok)
    if unknown:  # the engine ignores them silently; a grant that names them meant something else
        raise Refuse(13, f"regions {regions!r}: unknown token(s) {unknown} (mi210_0, q0-q3, CPU lists only)")
    lst_s = ",".join(lst)
    why = f"--class {cls} launcher would refuse regions={regions} (.ended rc=2)"
    if cls == "cpu":
        if gpu:
            raise Refuse(13, f"{why}: class cpu takes no mi210_0 token (a CPU job that needs the GPU quiet "
                             "is --class cpu --gpu-quiet exclusive with a CPU-only grant)")
        cpus = lst_s or ",".join(quarter_cpus(n) for n in qs)
    elif cls == "gpu":
        if not gpu:
            raise Refuse(13, f"{why}: class gpu needs an mi210_0 token")
        cpus = lst_s or gputhr
    elif cls == "cpu+gpu":
        if not gpu:
            raise Refuse(13, f"{why}: class cpu+gpu needs an mi210_0 token")
        cpus = lst_s or ",".join(quarter_cpus(n) for n in qs)
    else:
        raise Refuse(15, f"launcher --class {cls!r} unknown")
    if not cpus:
        raise Refuse(13, f"{why}: no CPU part (qN or a CPU list)")
    if not LIST_RE.match(cpus) or any(c > 191 for c in expand(cpus)):
        raise Refuse(13, f"{why}: CPU part {cpus!r} is not a valid list <= 191")
    return cpus


def claim_of(o: dict, cpus: str | None) -> tuple[str, str]:
    """(cpu-list the launcher's region-lock claim takes or '', gpu-quiet mode or '') -- rlargs of run2..8."""
    if o["self_claim"]:
        return "", ""
    gq, cc, cls = o["gpu_quiet"], o["claim_cpus"], o["class"]
    if gq == "exclusive" and not cc:
        cc = "0-95"
    cpu_list, gmode = "", ""
    if cls == "cpu":
        cpu_list = cc or (cpus or "")
        gmode = gq if gq and gq != "none" else ""
    elif cls == "gpu":
        if gq == "exclusive":
            cpu_list, gmode = cc, "exclusive"
        elif gq == "none":
            cpu_list, gmode = "", ""
        else:
            cpu_list, gmode = cc, gq or "shared"
    elif cls == "cpu+gpu":
        cpu_list = cc or (cpus or "")
        gmode = "" if gq == "none" else (gq or "shared")
    if o["nofold"] and cls == "gpu":
        cpu_list, gmode = "", gmode or "shared"
    if cls == "gpu" and _grant_cpus_engine(o):
        # ws58 2026-11-02 GRANT_CPUS engine: a gpu claim is the grant's PRIMARY cpus only (host threads 184-191 unlocked);
        # --claim-cpus / --no-fold-siblings no longer widen it
        cpu_list = ",".join(str(c) for c in sorted(set(expand(cpus or ""))) if c < 96)
        gmode = "" if gq == "none" else (gq or "shared")
    return cpu_list, gmode


def _grant_cpus_engine(o: dict) -> bool:
    try:
        with open(o.get("engine_path") or "", errors="replace") as f:
            return "GRANT_CPUS" in f.read()
    except OSError:
        return False


def cpu_regions(lst: str, fold: bool = True) -> set[str]:
    out = set()
    for c in expand(lst):
        if c >= 96 and not fold:
            continue
        if 0 <= c <= 191:
            out.add(QUARTERS[(c % 96) // 24])
    return out


def region_set(spec: str) -> set[str]:
    out: set[str] = set()
    lst = []
    for tok in spec.replace(";", ",").split(","):
        if tok in ("mi210_0", "gpu-quiet"):
            out.add("gpu-quiet")
        elif tok in QUARTERS:
            out.add(tok)
        elif tok[:1].isdigit():
            lst.append(tok)
        elif tok:
            raise Refuse(13, f"region spec {spec!r}: unknown token {tok!r}")
    if lst:
        s = ",".join(lst)
        if not LIST_RE.match(s):
            raise Refuse(13, f"region spec {spec!r}: bad CPU list")
        out |= cpu_regions(s)
    return out


def fmt(rs: set[str]) -> str:
    order = list(QUARTERS) + ["gpu-quiet"]
    return "+".join(r for r in order if r in rs) or "none"


# ---------------------------------------------------------------- precond-cmd (v2.1)
def read_environ(root: str, pid: int) -> dict[str, str] | None:
    try:
        with open(f"{root}/{pid}/environ", "rb") as f:
            raw = f.read()
    except OSError:
        return None
    env = {}
    for kv in raw.split(b"\0"):
        k, sep, v = kv.partition(b"=")
        if sep and k:
            env[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    return env or None


def run_precond(o: dict, root: str, epid: int) -> str:
    """Run the engine's --precond-cmd exactly as the engine does: `( cd "$WORKDIR" && bash -c "$CMD" )`,
    stdout+stderr merged, the engine's own environment when /proc/<epid>/environ is readable (else ours).
    No timeout in the engine; the gate caps at PRECOND_TIMEOUT_S.  Returns a note ('' if nothing to say);
    raises Refuse(12) on failure.  A timeout or an unrunnable shell cannot be judged: warn and admit."""
    cmd = o["precond_cmd"]
    if not cmd:
        return ""
    env = read_environ(root, epid)
    try:
        r = subprocess.run(["bash", "-c", cmd], cwd=o["workdir"], env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=PRECOND_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return "precond-timeout-unchecked"
    except FileNotFoundError:  # cwd missing: the engine's `cd` fails too, so its precond fails
        raise Refuse(12, f"not ready: precond-cmd failed: {' '.join(cmd.split())}")
    except OSError:
        return "precond-unrunnable-unchecked"
    if r.returncode != 0:
        raise Refuse(12, f"not ready: precond-cmd failed: {' '.join(cmd.split())}")
    return "precond=ok"


# ---------------------------------------------------------------- row




# ---------------------------------------------------------------- main
def check(a: argparse.Namespace) -> str:
    flags_dir = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
    m, armed = _v3_row(flags_dir, a.row)
    if m.get("schema") != "epyc.row.v3":
        raise Refuse(10, f"row {a.row} has no epyc.row.v3 row in ready/ (legacy rows: rowflow.py publish --migrate)")
    rowpid = armed.get("pid") if isinstance(armed.get("pid"), int) else None
    pid = a.pid if a.pid is not None else rowpid
    warns = []
    if pid is None:
        raise Refuse(14, f"no launcher pid: neither --pid nor dryrun/{a.row}/ARMED.json (row not armed yet)")
    if a.pid is not None and rowpid is not None and a.pid != rowpid:
        warns.append(f"pid-differs-from-armed:{rowpid}")
    if not alive(a.proc, pid):
        raise Refuse(14, f"launcher pid {pid} of {a.row} is dead (no {a.proc}/{pid} or zombie)")
    o, epid, own = find_launcher(a.proc, pid, a.row)
    if o is None:
        joined = " ".join(own)
        if "filler_run" in joined or "launch.sh" in joined:
            raise Refuse(14, f"pid {pid} is a wrapper ({joined[:80]!r}) with no live filler engine "
                             f"for {a.row} under it")
        if a.regions is not None:
            raise Refuse(15, f"pid {pid} runs no filler_run*.sh engine with --id {a.row} "
                             f"({joined[:80]!r}): class/region check impossible; drop --regions only "
                             "after checking the launcher by hand")
    parts = []
    if o is not None:
        via = f" via {pid}" if epid != pid else ""
        parts.append(f"launcher={o['engine']}:{epid}{via} lclass={o['class']}")
        minwin, src = o["min_window"], "argv"
    else:
        minwin, src = (m.get("min_window_s") if isinstance(m.get("min_window_s"), int) else None), "row"
        parts.append(f"launcher=unrecognised:{pid}")
        if minwin is None and a.window_s is not None:
            raise Refuse(15, f"no --min-window in pid {pid}'s argv and no min_window_s in the v3 row")
    parts.append(f"minwin={minwin}({src})")
    if a.window_s is not None:
        if a.window_s < minwin + MARGIN_S:
            raise Refuse(12, f"window {a.window_s} s < min-window {minwin} s + {MARGIN_S} s "
                             f"({src}{', ' + o['engine'] + ' pid ' + str(epid) if o else ''}); "
                             "the launcher sees the grant up to one poll late and refuses rc=3")
        parts.append(f"window={a.window_s}")
    if o is not None:
        cpus = None
        if a.regions is not None:
            cpus = parse_regions(a.regions, o["class"], o["gpu_threads"])
        cl, gm = claim_of(o, cpus)
        if o["self_claim"]:
            parts.append("claim=self(job claims its own regions; not checked)")
        else:
            fold = not (o["nofold"] and o["class"] != "gpu")
            need = cpu_regions(cl, fold) if cl else set()
            if cl and not need:
                raise Refuse(13, f"claim --cpu-list {cl} with --no-fold-siblings maps to no regions "
                                 "(region-lock refuses an SMT-only list)")
            if gm:
                need.add("gpu-quiet")
            quiet = gm == "exclusive" and set(QUARTERS) <= need
            parts.append(f"claim={cl or '-'} gpuq={gm or '-'} claim_regions={fmt(need)}"
                         + (f" fold={fmt(cpu_regions(cl))}" if o["class"] == "gpu" and cl else ""))
            if a.regions is not None:
                have = region_set(a.regions) | (region_set(a.reserve) if a.reserve else set())
                miss = need - have
                if miss:
                    raise Refuse(13, f"{o['engine']} --class {o['class']}"
                                     f"{' --claim-cpus ' + o['claim_cpus'] if o['claim_cpus'] else ''}"
                                     f"{' --gpu-quiet ' + o['gpu_quiet'] if o['gpu_quiet'] else ''}"
                                     f"{' --no-fold-siblings' if o['nofold'] else ''} claims {fmt(need)}, "
                                     f"regions={a.regions}{' reserve=' + a.reserve if a.reserve else ''} "
                                     f"cover {fmt(have)}: missing {fmt(miss)} (grant them, or --reserve "
                                     "what the writer's claim-wait keeps free)")
                parts.append(f"regions={a.regions}" + (f" reserve={a.reserve}" if a.reserve else ""))
            dc = a.derived_class
            if dc and dc != "filler":
                if quiet and dc != "block-timing-quiet":
                    warns.append(f"quiet-claim-on-{dc}-row")
                if dc == "block-timing-quiet" and not quiet:
                    warns.append("quiet-row-launcher-not-whole-host-exclusive")
        note = run_precond(o, a.proc, epid)
        if note == "precond=ok":
            parts.append(note)
        elif note:
            warns.append(note)
    elif "--precond-cmd" in " ".join(own):
        warns.append("precond-not-extracted")
    if warns:
        parts.append("warn=" + ",".join(warns))
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--row", required=True)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--window-s", type=int)
    ap.add_argument("--regions")
    ap.add_argument("--reserve")
    ap.add_argument("--derived-class", default="")
    ap.add_argument("--fillers", default="/dev/null")  # ignored (v4)
    ap.add_argument("--proc", default="/proc")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 64 if e.code else 0
    try:
        print(check(a))
        return 0
    except Refuse as r:
        print(f"refuse: {r}")
        return r.code
    except (OSError, UnicodeDecodeError) as e:
        print(f"refuse: launcher check could not read its inputs: {e}")
        return 15


if __name__ == "__main__":
    sys.exit(main())
