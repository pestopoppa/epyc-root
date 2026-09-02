"""INF-70 CPU decode roofline ledger → ClaimTuple (SC53 write side).

An adapter PROJECTS. It never grades. `claim_tuple.grade()` decides, and this
file registers no ladder: INF-70 is `measurement` class and that class's one
ladder already lives in `scripts/vidya/claim_tuple.py`.

WHAT THE NATIVE RECORD IS
-------------------------
One INF-70 run directory (`/mnt/raid0/llm/tmp/inf70/results*-<UTC>/`) written
by `sweep_c0_d0.sh` / `c5_reanchor_v2.sh` / `c5_followup.sh`. Three kinds of
number live in it, and each gets its own tuple:

* **llama-bench arms** — `arms.log` declares each arm (binary, thread list,
  env) and carries its markdown rows; `bench-<arm>.log` carries the exact
  command line, the `build: <sha> (<n>)` stamp and the same rows. One tuple per
  ROW (one thread count × one test), because those are genuinely different
  measurements, sharing one run-level locator.
* **`bench_readbw` kernel rows** — `c0-*.txt`. One tuple per (block, kernel).
  The counting convention travels WITH the number: `copy` at 40 GB/s and
  `read-sum` at 66 GB/s are not comparable, and a GB/s stripped of its
  convention is the classic way this measurement gets misquoted.
* **`bench_barrier` rows** — `d0-barrier.txt`. One tuple per (block, impl).
  µs/barrier is `lower_better`; that is recorded, never inferred.

STRICTNESS — what is refused, and why
-------------------------------------
The reader refuses anything it cannot REDERIVE from the record itself:

* a run directory whose name carries no UTC stamp and that has no `DONE` —
  a dateless run cannot say when it measured;
* an arm with no `bench-<arm>.log` — the arm row alone cannot produce the
  command line or the build id, so the recipe would have to be assumed;
* an arm whose `arms.log` rows disagree with its bench log's rows;
* an arm with no `artifact.sha256`, or one that does not name the `-m` model
  the command actually loaded — the model identity would be unpinned, and
  SC53 requires artifact path AND sha on every arm. This refuses real,
  complete runs (`results-c5fu-*` today). That is the point: the fix belongs
  in the producer, not in an adapter inventing a hash on read.

PLACEMENT PROOF IS PROVENANCE, NEVER A GRADE
--------------------------------------------
`state-<arm>.log` samples `numastat -p` DURING the arm. Its presence, and the
per-node split it shows, are carried in `extra` as `placement_*`. They do NOT
move the grade: the ladder grades protocol / n / date / attestation, and a
second private rule ("skewed ⇒ downgrade") would be exactly the constitution
re-derived in an adapter that §4.7 forbids. A consumer that cares about
placement reads the field and decides for itself — which is also why the field
distinguishes *absent* (no sampler ran) from *present and skewed*.

CATEGORY
--------
`category` is structurally required and the runs do not declare it, so every
arm is `CANDIDATE` unless the run ships an `arms.meta` line naming otherwise.
CANDIDATE is the non-asserting floor: calling an undeclared arm `OPTIMUM` or
`BASELINE` would assert a comparison the run never recorded.

Usage:
    python3 scripts/vidya/adapters/inf70_roofline_ledger.py --dry-run
    python3 scripts/vidya/adapters/inf70_roofline_ledger.py --dry-run --root DIR
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, REPO_ROOT, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.inf70_roofline_ledger/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "inf70-roofline-measurement"

DEFAULT_CORPUS = Path("/mnt/raid0/llm/tmp/inf70")

# Protocol ids. Following the SC19 precedent, a protocol id names the native
# record shape this reader accepts; a producer change that breaks the shape must
# bump it rather than let the same id cover two different recipes.
PROTOCOL_ARM = "inf70.llama_bench_arm.v1"
PROTOCOL_READBW = "inf70.bench_readbw_block.v1"
PROTOCOL_BARRIER = "inf70.bench_barrier_block.v1"

ARMS_FILE = "arms.log"
ARTIFACT_SHA_FILE = "artifact.sha256"
DONE_FILE = "DONE"
META_FILE = "arms.meta"
BARRIER_FILE = "d0-barrier.txt"

CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})

_RUN_STAMP = re.compile(r"(\d{8})T(\d{6})Z")
# `ARM <name> start <hh:mm:ss> <key>=<value> ... env=[...]`. The key/value tail
# is parsed generically: c5_followup.sh added a `model=` field that a positional
# regex silently refused, which read as "this run has no arms" — a strict reader
# must refuse for a NAMED reason, never by failing to see the record at all.
_ARM_START = re.compile(
    r"^ARM (?P<arm>\S+) start (?P<t>\d\d:\d\d:\d\d) (?P<tail>.*?)"
    r"(?: env=\[(?P<env>[^\]]*)\])?\s*$"
)
_ARM_END = re.compile(
    r"^ARM (?P<arm>\S+) end\s+(?P<t>\d\d:\d\d:\d\d) exit=(?P<exit>-?\d+)"
    r"(?: contam_hits=(?P<contam>\d+))?\s*$"
)
_BUILD = re.compile(r"^build:\s+(?P<sha>[0-9a-f]{7,40})\s+\((?P<num>\d+)\)\s*$")
_SHA256 = re.compile(r"^([0-9a-f]{64})\s+(\S+)\s*$")
_BLOCK_LABEL = re.compile(r"^===\s*(?P<label>.+?)\s*===\s*$")
_READBW_PARAMS = re.compile(r"^threads=(?P<threads>\d+)\b.*\breps=(?P<reps>\d+)\b")
_READBW_ROW = re.compile(r"^(?P<kernel>[a-zA-Z0-9_-]+)\s+(?P<gbs>\d+\.\d+)\s+(?P<conv>\S.*?)\s*$")
_BARRIER_HEAD = re.compile(
    r"^===\s*(?P<impl>.+?) \| t=(?P<threads>\d+) \| OMP stack (?P<omp>ON|OFF)\s*===\s*$"
)
_BARRIER_ROW = re.compile(r"^(?P<kind>omp|flat|hier|work)\s+(?P<us>\d+\.\d+) us/(?P<unit>\S+)")
_NUMASTAT_TOTAL = re.compile(r"^Total\s+((?:\d+\.\d+\s+)+\d+\.\d+)\s*$")


# ---------------------------------------------------------------------------
# small readers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _repo_relative(path: Path) -> str:
    """The path under epyc-root, or "" when outside it.

    `artifact_present()` resolves repo-relative paths only; an out-of-tree run
    directory is honest as locator-only, never as an in-tree pin. Every INF-70
    run lives under /mnt/raid0/llm/tmp today, so this returns "" for all of
    them and the ladder answers Anchored rather than Attested — which is true.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def run_timestamp(run_dir: Path) -> str:
    """UTC ISO-8601 for the run: the DONE stamp, else the directory name."""
    done = _read(run_dir / DONE_FILE).strip()
    if done.startswith("done "):
        stamp = done.split(None, 1)[1].strip()
        if stamp:
            return stamp
    m = _RUN_STAMP.search(run_dir.name)
    if not m:
        return ""
    d, t = m.group(1), m.group(2)
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}T{t[0:2]}:{t[2:4]}:{t[4:6]}Z"


def _run_slug(run_dir: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", run_dir.name).strip("_")


def _declared_categories(run_dir: Path) -> dict[str, str]:
    """Optional `arms.meta`: `<arm> <CATEGORY>` per line. Unknown labels ignored."""
    out: dict[str, str] = {}
    for line in _read(run_dir / META_FILE).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] in CATEGORIES:
            out[parts[0]] = parts[1]
    return out


def artifact_sha_and_path(run_dir: Path) -> tuple[str, str]:
    """(sha256, path) from `artifact.sha256`, or ("", "")."""
    for line in _read(run_dir / ARTIFACT_SHA_FILE).splitlines():
        m = _SHA256.match(line.strip())
        if m:
            return m.group(1), m.group(2)
    return "", ""


# ---------------------------------------------------------------------------
# the recipe, rederived from the bench log's own command line
# ---------------------------------------------------------------------------

def parse_command(text: str) -> dict[str, Any]:
    """Rederive the recipe from the command line the bench log records.

    Returns {} when no command line is present — the arm is then refused rather
    than projected against an assumed recipe.
    """
    cmd = ""
    for line in text.splitlines():
        if "llama-bench" in line and " -m " in line:
            cmd = line.split("running:", 1)[1].strip() if "running:" in line else line.strip()
            break
    if not cmd:
        return {}
    tokens = cmd.split()
    env: dict[str, str] = {}
    i = 0
    if tokens and tokens[0] == "env":
        i = 1
    while i < len(tokens) and "=" in tokens[i] and not tokens[i].startswith("-"):
        key, _, val = tokens[i].partition("=")
        env[key] = val
        i += 1
    rest = tokens[i:]

    def _after(flag: str) -> str:
        return rest[rest.index(flag) + 1] if flag in rest and rest.index(flag) + 1 < len(rest) else ""

    numactl = ""
    for tok in rest:
        if tok.startswith("--interleave") or tok.startswith("--membind") or tok.startswith("--preferred"):
            numactl = tok
    binary = next((t for t in rest if t.endswith("llama-bench")), "")
    return {
        "command": cmd,
        "env": env,
        "cpu_list": _after("taskset") and _after("-c"),
        "numactl_policy": numactl,
        "binary": binary,
        "model": _after("-m"),
        "threads_flag": _after("-t"),
        "reps": _after("-r"),
        "n_prompt": _after("-p"),
        "n_gen": _after("-n"),
        "mmap": _after("-mmp"),
    }


def parse_build(text: str) -> str:
    for line in text.splitlines():
        m = _BUILD.match(line.strip())
        if m:
            return f"{m.group('sha')} ({m.group('num')})"
    return ""


def parse_bench_rows(text: str) -> tuple[dict, ...]:
    """llama-bench markdown result rows: (threads, test, value, stddev)."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8 or cells[0].startswith("-") or cells[0] == "model":
            continue
        try:
            threads = int(cells[4])
        except ValueError:
            continue
        value_cell = cells[7]
        parts = value_cell.split("±")
        try:
            value = float(parts[0].strip())
        except ValueError:
            continue
        stddev = None
        if len(parts) > 1:
            try:
                stddev = float(parts[1].strip())
            except ValueError:
                stddev = None
        rows.append({
            "model_label": cells[0], "size": cells[1], "params": cells[2],
            "backend": cells[3], "threads": threads, "mmap": cells[5],
            "test": cells[6], "value": value, "stddev": stddev,
        })
    return tuple(rows)


def _row_key(row: dict) -> tuple:
    return (row["threads"], row["test"], row["value"])


# ---------------------------------------------------------------------------
# placement proof — provenance only
# ---------------------------------------------------------------------------

def placement_proof(run_dir: Path, arm: str) -> dict[str, Any]:
    """The last in-window `numastat -p` sample for an arm, as provenance.

    `present=False` means no sampler ran, which is NOT the same as "placement
    was bad" — the distinction is why this is a field and not a grade.
    """
    path = run_dir / f"state-{arm}.log"
    if not path.is_file():
        return {"present": False, "reason": "no state-<arm>.log sampler output"}
    last: list[float] | None = None
    for line in _read(path).splitlines():
        m = _NUMASTAT_TOTAL.match(line.strip())
        if m:
            vals = [float(v) for v in m.group(1).split()]
            if len(vals) >= 2:
                last = vals[:-1]  # drop the printed grand total
    if not last or sum(last) <= 0:
        return {"present": False, "reason": "state log present but no parseable Total row",
                "source": path.name}
    total = sum(last)
    shares = [100.0 * v / total for v in last]
    max_idx = max(range(len(shares)), key=lambda i: shares[i])
    return {
        "present": True,
        "source": path.name,
        "per_node_mb": [round(v, 2) for v in last],
        "total_mb": round(total, 2),
        "max_node": max_idx,
        "max_share_pct": round(shares[max_idx], 1),
        "even_share_pct": round(100.0 / len(shares), 1),
    }


# ---------------------------------------------------------------------------
# native rows
# ---------------------------------------------------------------------------

def _parse_arms_log(text: str) -> tuple[dict, ...]:
    arms: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        ms = _ARM_START.match(line)
        if ms:
            fields = dict(
                tok.split("=", 1) for tok in (ms.group("tail") or "").split() if "=" in tok
            )
            current = {
                "arm": ms.group("arm"), "started": ms.group("t"),
                "binary": fields.get("bin", ""),
                "threads_flag": fields.get("threads", ""),
                "fields": fields,
                "env": dict(
                    p.split("=", 1) for p in (ms.group("env") or "").split() if "=" in p
                ),
                "rows": [],
            }
            arms.append(current)
            continue
        me = _ARM_END.match(line)
        if me and current is not None and me.group("arm") == current["arm"]:
            current["ended"] = me.group("t")
            current["exit"] = int(me.group("exit"))
            current["contam_hits"] = int(me.group("contam") or 0)
            continue
        if line.startswith("|") and current is not None:
            current["rows"].extend(parse_bench_rows(line))
    return tuple(arms)


def arm_refusals(run_dir: str | Path) -> dict[str, str]:
    """Arm name → why it yields no rows. Empty when every arm projects."""
    run_dir = Path(run_dir)
    out: dict[str, str] = {}
    sha, sha_path = artifact_sha_and_path(run_dir)
    for arm in _parse_arms_log(_read(run_dir / ARMS_FILE)):
        name = arm["arm"]
        bench = run_dir / f"bench-{name}.log"
        if not bench.is_file():
            out[name] = f"no bench-{name}.log — command line and build id are not rederivable"
            continue
        text = _read(bench)
        cmd = parse_command(text)
        if not cmd:
            out[name] = "bench log carries no llama-bench command line"
            continue
        if not parse_build(text):
            out[name] = "bench log carries no `build: <sha> (<n>)` stamp"
            continue
        if not sha:
            out[name] = (
                "no artifact.sha256 — the model identity is unpinned; SC53 requires "
                "artifact path AND sha per arm, and a hash invented on read claims "
                "warrant the run never captured")
            continue
        if sha_path and cmd.get("model") and sha_path != cmd["model"]:
            out[name] = (f"artifact.sha256 names {sha_path} but the command loaded "
                         f"{cmd['model']}")
            continue
        if not arm["rows"]:
            out[name] = "no result rows in arms.log"
            continue
        if {_row_key(r) for r in arm["rows"]} != {_row_key(r) for r in parse_bench_rows(text)}:
            out[name] = "arms.log rows disagree with the bench log's own rows"
            continue
    return out


def refusal_reason(run_dir: str | Path) -> str | None:
    """Why a run directory yields zero rows overall, else None."""
    path = Path(run_dir)
    if not path.is_dir():
        return "no emissions"
    if not run_timestamp(path):
        return "malformed: no DONE stamp and no UTC stamp in the directory name"
    has_any = (
        (path / ARMS_FILE).is_file()
        or (path / BARRIER_FILE).is_file()
        or any(path.glob("c0-*.txt"))
    )
    if not has_any:
        return "no emissions"
    return None


def native_rows(run_dir: str | Path) -> tuple[dict, ...]:
    """Every projectable record in one run directory. Refused arms are absent."""
    run_dir = Path(run_dir)
    if refusal_reason(run_dir) is not None:
        return ()
    date = run_timestamp(run_dir)
    slug = _run_slug(run_dir)
    locator = str(run_dir)
    rel = _repo_relative(run_dir)
    categories = _declared_categories(run_dir)
    rows: list[dict] = []

    # --- llama-bench arms ---
    sha, sha_path = artifact_sha_and_path(run_dir)
    refused = arm_refusals(run_dir)
    for arm in _parse_arms_log(_read(run_dir / ARMS_FILE)):
        name = arm["arm"]
        if name in refused:
            continue
        bench = run_dir / f"bench-{name}.log"
        text = _read(bench)
        cmd = parse_command(text)
        recipe_reps = cmd.get("reps") or ""
        proof = placement_proof(run_dir, name)
        digest = _file_sha256(bench)
        for row in arm["rows"]:
            rows.append({
                "kind": "arm",
                "run_dir": str(run_dir), "run_slug": slug, "date": date,
                "locator": locator, "repo_relative": rel,
                "arm": name, "exit": arm.get("exit"), "contam_hits": arm.get("contam_hits"),
                "arm_env": arm["env"], "binary": arm["binary"],
                "build": parse_build(text), "recipe": cmd,
                "artifact_path": sha_path or cmd.get("model", ""), "artifact_sha256": sha,
                "row": row, "reps": int(recipe_reps) if recipe_reps.isdigit() else None,
                "placement": proof,
                "category": categories.get(name, "CANDIDATE"),
                "category_declared": name in categories,
                "source_file": bench.name, "source_sha256": digest,
            })

    # --- bench_readbw blocks ---
    # A block STARTS at its `threads=... reps=...` parameter line, not at the
    # `=== label ===` banner: the banners are free-form (and absent entirely in
    # the per-node C0-c files), while the parameter line is emitted by
    # bench_readbw itself. Anchoring on the banner merged four distinct t=96
    # conditions into one id. The banner, when present, is kept as the label.
    for path in sorted(run_dir.glob("c0*.txt")):
        digest = _file_sha256(path)
        block: dict | None = None
        block_index = -1
        label = ""
        for line in _read(path).splitlines():
            banner = _BLOCK_LABEL.match(line)
            if banner:
                label = banner.group("label")
                block = None
                continue
            params = _READBW_PARAMS.match(line)
            if params:
                block_index += 1
                arr = re.search(r"\barray=(\S+ \S+ \S+)", line)
                hp = re.search(r"\bhugepage=(\d+)\b", line)
                block = {
                    "index": block_index,
                    "threads": int(params.group("threads")),
                    "reps": int(params.group("reps")),
                    "omp_stack": ("ON" if "OMP stack ON" in label
                                  else "OFF" if "OMP stack OFF" in label else "unstated"),
                    "label": label,
                    "array": arr.group(1) if arr else "",
                    "hugepage": int(hp.group(1)) if hp else None,
                    "per_node_threads": "",
                }
                label = ""
                continue
            if block is None:
                continue
            if line.startswith("threads per NUMA node:"):
                block["per_node_threads"] = line.split(":", 1)[1].strip()
                continue
            if line.startswith("kernel"):
                continue
            row = _READBW_ROW.match(line)
            if row:
                rows.append({
                    "kind": "readbw",
                    "run_dir": str(run_dir), "run_slug": slug, "date": date,
                    "locator": locator, "repo_relative": rel,
                    "block": dict(block), "kernel": row.group("kernel"),
                    "gbs": float(row.group("gbs")),
                    "counting_convention": row.group("conv"),
                    "category": "CANDIDATE", "category_declared": False,
                    "source_file": path.name, "source_sha256": digest,
                })

    # --- bench_barrier blocks ---
    bpath = run_dir / BARRIER_FILE
    if bpath.is_file():
        digest = _file_sha256(bpath)
        block = None
        block_index = -1
        for line in _read(bpath).splitlines():
            head = _BARRIER_HEAD.match(line)
            if head:
                block_index += 1
                block = {"index": block_index,
                         "impl": head.group("impl"), "threads": int(head.group("threads")),
                         "omp_stack": head.group("omp"), "topology": ""}
                continue
            if block is None:
                continue
            if line.startswith("threads="):
                block["topology"] = line.strip()
                continue
            row = _BARRIER_ROW.match(line)
            if row:
                rows.append({
                    "kind": "barrier",
                    "run_dir": str(run_dir), "run_slug": slug, "date": date,
                    "locator": locator, "repo_relative": rel,
                    "block": dict(block), "measure": row.group("kind"),
                    "us": float(row.group("us")), "unit": f"us/{row.group('unit')}",
                    "detail": line.strip(),
                    "category": "CANDIDATE", "category_declared": False,
                    "source_file": bpath.name, "source_sha256": digest,
                })
    return tuple(rows)


# ---------------------------------------------------------------------------
# the projection
# ---------------------------------------------------------------------------

def _attestation(native: dict) -> dict[str, Any]:
    rel = native.get("repo_relative") or ""
    path = f"{rel}/{native['source_file']}" if rel else ""
    return {
        "attestation_path": path,
        "attestation_locator": f"{native['locator']}/{native['source_file']}",
        "attestation_sha256": native.get("source_sha256") or "",
        # The run directories live outside epyc-root, so the hash is honest and
        # the artifact is not repo-resolvable: locator-only, Anchored not
        # Attested. Setting this explicitly stops `artifact_present()` guessing
        # from an empty path.
        "attestation_present": bool(path) and (REPO_ROOT / path).is_file(),
    }


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Never grades; `claim_tuple.grade()` decides."""
    if not isinstance(native, dict):
        raise ProjectionError("inf70 native must retain the run envelope")
    kind = native.get("kind")
    for key in ("run_dir", "run_slug", "locator", "source_file", "source_sha256"):
        if not native.get(key):
            raise ProjectionError(
                f"inf70 native row must retain {key} (callers cannot bypass native_rows)")
    if not Path(native["run_dir"]).is_dir():
        raise ProjectionError("inf70 native row must retain a live run directory")
    if native.get("category") not in CATEGORIES:
        raise ProjectionError(f"inf70 native row carries no admissible category: {native!r}")
    date = native.get("date") or ""

    if kind == "arm":
        return _project_arm(native, date)
    if kind == "readbw":
        return _project_readbw(native, date)
    if kind == "barrier":
        return _project_barrier(native, date)
    raise ProjectionError(f"unknown inf70 record kind {kind!r}")


def _project_arm(native: dict, date: str) -> ClaimTuple:
    row = native.get("row") or {}
    for key in ("threads", "test", "value"):
        if row.get(key) is None:
            raise ProjectionError(f"inf70 arm row must retain {key}")
    if not native.get("build"):
        raise ProjectionError("inf70 arm must retain its build id")
    if not native.get("artifact_sha256"):
        raise ProjectionError("inf70 arm must retain the artifact sha256")
    recipe = native.get("recipe") or {}
    if not recipe.get("command"):
        raise ProjectionError("inf70 arm must retain the command line it was measured with")

    threads, test = row["threads"], row["test"]
    ident = f"inf70_{native['run_slug']}_arm_{native['arm']}_t{threads}_{test}"
    ident = re.sub(r"[^A-Za-z0-9_]+", "_", ident)
    ms_per_token = round(1000.0 / row["value"], 3) if row["value"] else None
    claim = (
        f"INF-70 {native['arm']}: {test} = {row['value']} t/s at -t {threads} on "
        f"{row['model_label']} (build {native['build']})"
    )
    return ClaimTuple(
        measurement_id=ident,
        metric=f"llama_bench.{test}",
        value=row["value"],
        unit="t/s",
        date=date,
        category=native["category"],
        claim=claim,
        metric_direction="higher_better",
        protocol_id=PROTOCOL_ARM,
        reps=native.get("reps"),
        reps_basis="scored: llama-bench -r repetitions, all scored",
        source_kind=SOURCE_KIND,
        extra={
            "arm": native["arm"],
            "threads": threads,
            "test": test,
            "stddev": row.get("stddev"),
            "ms_per_token": ms_per_token if test.startswith("tg") else None,
            "model_label": row.get("model_label"),
            "build": native["build"],
            "binary": native.get("binary"),
            "artifact_path": native.get("artifact_path"),
            "artifact_sha256": native["artifact_sha256"],
            "recipe": recipe,
            "arm_env": native.get("arm_env"),
            "arm_exit": native.get("exit"),
            "contam_hits": native.get("contam_hits"),
            # Provenance, never a grade — see the module docstring.
            "placement_proof": native.get("placement"),
            "category_declared_by_producer": native.get("category_declared", False),
            "run_dir": native["run_dir"],
        },
        **_attestation(native),
    )


def _project_readbw(native: dict, date: str) -> ClaimTuple:
    block = native.get("block") or {}
    if block.get("reps") is None:
        raise ProjectionError("inf70 readbw row must retain its reps")
    if not native.get("counting_convention"):
        raise ProjectionError(
            "inf70 readbw row must retain its counting convention — a GB/s without one "
            "is not comparable to any other GB/s")
    kernel = native["kernel"]
    # Identity carries the source file and the block ordinal within it: one
    # c0-*.txt holds several blocks at the SAME thread count that differ only by
    # placement, and an id without the ordinal merged them into one belief —
    # the exact collision the carrier's identity rule exists to prevent.
    ident = re.sub(
        r"[^A-Za-z0-9_]+", "_",
        f"inf70_{native['run_slug']}_readbw_{Path(native['source_file']).stem}"
        f"_b{block.get('index', 0)}_{kernel}_t{block['threads']}_omp{block['omp_stack']}",
    )
    claim = (
        f"INF-70 bench_readbw {kernel} = {native['gbs']} GB/s at {block['threads']} threads "
        f"(OMP stack {block['omp_stack']}, {block['label'] or 'no banner'}; counting: "
        f"{native['counting_convention']})"
    )
    return ClaimTuple(
        measurement_id=ident,
        metric=f"bench_readbw.{kernel}",
        value=native["gbs"],
        unit="GB/s",
        date=date,
        category=native["category"],
        claim=claim,
        metric_direction="higher_better",
        protocol_id=PROTOCOL_READBW,
        reps=block["reps"],
        reps_basis="scored: bench_readbw reps, all scored",
        source_kind=SOURCE_KIND,
        extra={
            "kernel": kernel,
            "counting_convention": native["counting_convention"],
            "threads": block["threads"],
            "omp_stack": block["omp_stack"],
            "block_index": block.get("index"),
            "condition_label": block.get("label"),
            "per_node_threads": block.get("per_node_threads"),
            "array": block.get("array"),
            "hugepage": block.get("hugepage"),
            "run_dir": native["run_dir"],
        },
        **_attestation(native),
    )


def _project_barrier(native: dict, date: str) -> ClaimTuple:
    block = native.get("block") or {}
    measure = native["measure"]
    ident = re.sub(
        r"[^A-Za-z0-9_]+", "_",
        f"inf70_{native['run_slug']}_barrier_b{block.get('index', 0)}_{block['impl']}_{measure}"
        f"_t{block['threads']}_omp{block['omp_stack']}",
    )
    claim = (
        f"INF-70 bench_barrier {block['impl']} {measure} = {native['us']} {native['unit']} "
        f"at {block['threads']} threads (OMP stack {block['omp_stack']})"
    )
    return ClaimTuple(
        measurement_id=ident,
        metric=f"bench_barrier.{block['impl']}.{measure}",
        value=native["us"],
        unit=native["unit"],
        date=date,
        category=native["category"],
        claim=claim,
        # A barrier costs time: less is better. Recorded, never inferred.
        metric_direction="lower_better",
        protocol_id=PROTOCOL_BARRIER,
        # bench_barrier's tables report no repetition count, so n stays absent
        # and the ladder says so. Absence is recorded, never filled.
        reps=None,
        reps_basis="",
        source_kind=SOURCE_KIND,
        extra={
            "impl": block["impl"],
            "block_index": block.get("index"),
            "measure": measure,
            "threads": block["threads"],
            "omp_stack": block["omp_stack"],
            "topology": block.get("topology"),
            "detail": native.get("detail"),
            "run_dir": native["run_dir"],
        },
        **_attestation(native),
    )


# ---------------------------------------------------------------------------
# emission + CLI
# ---------------------------------------------------------------------------

def frames_for_run(run_dir: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier."""
    frames: list[dict] = []
    for native in native_rows(run_dir):
        frames.extend(
            to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)
        )
    return frames


def discover(root: str | Path = DEFAULT_CORPUS) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("results*") if p.is_dir())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="inf70_roofline_ledger.py",
        description="Project INF-70 roofline run directories into ClaimTuples (SC53).",
    )
    ap.add_argument("--root", default=str(DEFAULT_CORPUS), help="corpus root of results* dirs")
    ap.add_argument("--run", action="append", help="a specific run directory (repeatable)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what WOULD be projected and what is refused; write nothing")
    args = ap.parse_args(argv)

    runs = [Path(r) for r in args.run] if args.run else discover(args.root)
    if not runs:
        print(f"no run directories under {args.root}")
        return 0

    total = 0
    for run in runs:
        reason = refusal_reason(run)
        if reason:
            print(f"{run.name}: REFUSED — {reason}")
            continue
        rows = native_rows(run)
        by_kind: dict[str, int] = {}
        for row in rows:
            by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        kinds = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())) or "nothing"
        print(f"{run.name}: {len(rows)} claim(s) [{kinds}]  date={run_timestamp(run)}")
        for arm, why in sorted(arm_refusals(run).items()):
            print(f"    REFUSED arm {arm}: {why}")
        if args.dry_run:
            for row in rows:
                tup = project(row)
                proof = (row.get("placement") or {}).get("present")
                proof_txt = "" if proof is None else f"  placement_proof={'yes' if proof else 'no'}"
                print(f"    {tup.measurement_id}  {tup.metric}={tup.value} {tup.unit}"
                      f"  n={tup.reps}{proof_txt}")
        total += len(rows)
    print(f"total: {total} claim(s){' (dry run — nothing written)' if args.dry_run else ''}")
    return 0


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "DEFAULT_CORPUS",
    "PROTOCOL_ARM", "PROTOCOL_READBW", "PROTOCOL_BARRIER",
    "run_timestamp", "artifact_sha_and_path", "parse_command", "parse_build",
    "parse_bench_rows", "placement_proof", "arm_refusals", "refusal_reason",
    "native_rows", "project", "frames_for_run", "discover", "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
