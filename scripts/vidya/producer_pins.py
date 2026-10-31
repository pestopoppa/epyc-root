#!/usr/bin/env python3
"""VB-AK-PIN-REPIN: which of the VB adapters' pinned producer digests went stale, and the re-pin.

WHY. Adapters pin the bytes of the producer they read (sha256 of one producer file, or the sampled-CPU
source-closure digest). Every change to the producer on research/orchestrator main that touches a pinned file
makes the pin stale and the adapter's producer-backed tests fail (the 15 failures of 2026-10-22 had this shape).
This tool lists the stale pins READ-ONLY, computes the new closure digest, and appends the re-pin.

    python3 scripts/vidya/producer_pins.py check  [--ref origin/main] [--json]    # exit 0 current, 3 stale/unresolved
    python3 scripts/vidya/producer_pins.py digest [--ref REF]                      # closure digest of REF (python3.13)
    python3 scripts/vidya/producer_pins.py repin  [--ref REF] [--apply]            # plan; --apply appends the pin

Run `check` whenever research or orchestrator main changes a producer file and at every operator `/wrap-up`. It
is operator- or session-triggered; NOTHING here installs a cron. Zero inference: git reads, sha256, one
fixture-free import of the producer's own ``source_identity()``.

Detection is the task's own: ``git log <pinned-commit>..<ref> -- <file>``. A FILE pin is current iff the blob at
``ref`` hashes to the pinned digest; if not, the commit that DID hash to the pin is found by walking the file's
history (so the report names exactly which commits changed it since), and a pin that no committed version
reproduces is UNRESOLVED (drift or an uncommitted producer). The CLOSURE pin (sampled-CPU) tracks the LAST entry of
``autokernel_profile.SAMPLED_CPU_ROLLING_PINS``: stale iff a closure file changed on ``ref`` since that commit.

``repin --apply`` edits ONLY the ROLLING-PINS block of ``adapters/autokernel_profile.py`` (append-only; older pins stay
allow-listed because captures keep their identity). File pins are one-line constant edits that need a human
decision on WHICH producer version the adapter now reads, so for those ``repin`` prints the new digest and the
test command and does not edit. After a re-pin re-run the producer-backed tests (printed) before committing.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

RESEARCH = Path(os.environ.get("EPYC_RESEARCH_ROOT") or "/workspace/repos/epyc-inference-research")
ORCHESTRATOR = Path(os.environ.get("EPYC_ORCHESTRATOR_ROOT") or "/workspace/repos/epyc-orchestrator")
REPOS = {"research": RESEARCH, "orchestrator": ORCHESTRATOR}
PYTHON313 = "/usr/bin/python3.13"  # the closure digest includes the interpreter identity
PROFILE = "adapters.autokernel_profile"
PROFILE_PATH = HERE / "adapters" / "autokernel_profile.py"
HISTORY_CAP = 400

#: (adapter module, constant, repo, path in repo, kind). ``kind`` "file" = the constant is the sha256 of that file;
#: "file-map" = the constant is {basename: sha256} and ``path`` is the directory holding them.
FILE_PINS = (
    ("dflash2_experimental_runtime", "PRODUCER_SHA256", "research", "scripts/benchmark/dflash2_beliefs.py", "file"),
    ("ds41_1017_validation", "PRODUCER_SHA256", "research", "scripts/benchmark/ds41_1017_capture.py", "file"),
    ("embedder_placement_gate", "PRODUCER_SHA256", "orchestrator", "scripts/server/embedder_placement_capture.py", "file"),
    ("gfx90a_static_register", "PRODUCER_SHA256", "research", "scripts/kernel_rnd/gfx90a_isa_audit.py", "file"),
    ("kv_quant_27b_v10", "PRODUCER_SHA256", "research", "scripts/benchmark/kv_quant_27b_v10_sweep.py", "file"),
    ("repl_retrieval_eval", "PRODUCER_SHA256", "orchestrator", "scripts/benchmark/repl_retrieval_capture.py", "file"),
    ("speech_cpu_measurement", "PRODUCER_SHA256", "research",
     "artifacts/speech_cpu_realtime_20260924/speech_cpu_capture.py", "file"),
)
#: ``kind`` "file-map" (a {basename: sha256} constant whose files sit in one directory of the repo) is supported by
#: ``check`` for a future live-read pin; no adapter has one today (dtap's map pins receipt-embedded copies).
#: sha256-shaped pin constants that are NOT a moving producer file on a repo main, each with the reason. A new pin
#: constant that is in neither FILE_PINS nor here fails ``check`` (UNMAPPED): a pin nobody watches goes stale unseen.
EXEMPT = {
    ("_pb_hol_m42b", "PRIOR_VERDICT_SHA"): "immutable native prior-verdict anchor, not a moving producer file; "
                                               "the paired reader checks the recorded path and digest",
    ("c6_q4_microbench", "OUTER_CAPTURE_MANIFEST_SHA256"): "immutable archived outer-custody manifest; "
                                                          "the reader re-hashes its exact captured bytes",
    ("c6_q4_microbench", "OUTER_CAPTURE_SUMS_SHA256"): "immutable archived outer-custody checksum seal; "
                                                      "the reader re-hashes it and verifies each sealed member",
    ("contextbench_score", "TRUSTED_PRODUCER_SHA256"): "producer bytes ship inside each run dir (producer-source.bin)",
    ("contextbench_score", "TRUSTED_SCORER_SHA256"): "scorer bytes ship inside each run dir",
    ("contextbench_score", "TRUSTED_PACKER_SHA256"): "packer bytes ship inside each run dir",
    ("contextbench_score", "TRUSTED_PACKAGE_SHA256"): "package bytes ship inside each run dir",
    ("managed_tooling_check", "TRUSTED_PRODUCER_SHA256"): "producer bytes ship inside each receipt",
    ("managed_tooling_check", "TRUSTED_DRIVER_SHA256"): "driver bytes ship inside each receipt",
    ("strategy_projection_report", "TRUSTED_PRODUCER_SHA256"): "producer bytes ship inside each run dir",
    ("hg5_request_event", "SCHEMA_SHA256"): "schema/producer bytes ship inside each sealed event",
    ("hg5_request_event", "PRODUCER_SHA256"): "producer bytes ship inside each sealed event",
    ("hg5_request_event", "PRODUCER_V2_SHA256"): "producer bytes ship inside each sealed event",
    ("hg5_request_event", "SCHEMA_V2_SHA256"): "schema bytes ship inside each sealed event",
    ("ch19_t3_screen", "PRODUCER_SHA256"): "producer is a /mnt/raid0/llm/tmp script, not a file on a repo main; "
                                           "the adapter re-hashes it live and refuses a different script",
    ("oolong", "VENDORED_SHA256"): "vendored upstream file, pinned on purpose",
    ("qwen4exp_quality", "READER_SHA256"): "in-tree reader (this repo), changes ride with the adapter commit",
    ("weight_handoff", "READER_SHA256"): "in-tree reader (this repo), changes ride with the adapter commit",
    ("dtap_timeout_report", "REGISTRY_SHA"): "registry digest of a captured run, not a file on main",
    ("dtap_timeout_report", "PRODUCERS"): "allow-list of the harness copies a captured run carries; the reader "
                                          "compares the run's own bytes, never main's",
    ("autokernel_real_mask", "PRODUCERS"): "allow-list of source bytes carried inside each run; never main's",
    **{("autokernel_profile", name): "historical closure digest of a pinned legacy producer (allow-list entry; the "
       "live sampled-CPU pin is tracked by SAMPLED_CPU_ROLLING_PINS)" for name in (
           "DIRECT_CPU_SOURCE_DIGEST", "FACTUAL_CPU_SOURCE_DIGEST", "CURRENT_CPU_SOURCE_DIGEST",
           "RUNTIME_CPU_SOURCE_DIGEST", "MATCHED_CPU_SOURCE_DIGEST", "CPU_SOURCE_DIGEST",
           "SAMPLED_CPU_SOURCE_DIGEST_07333B884", "SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9")},
}
#: The sampled-CPU closure (``cpu_profile.source_identity()["files"]``), from the research repo.
CLOSURE_FILES = (
    "scripts/kernel_rnd/autokernel/loop/cpu_profile.py", "scripts/kernel_rnd/autokernel/loop/serving.py",
    "scripts/kernel_rnd/autokernel/evaluator/c3_epyc_tensor_capture.py",
    "scripts/kernel_rnd/autokernel/loop/lifecycle_observation.py", "scripts/kernel_rnd/autokernel/loop/planned_serving.py",
    "scripts/kernel_rnd/autokernel/loop/native_server_response.py",
    "scripts/kernel_rnd/autokernel/loop/observation_binding.py", "scripts/kernel_rnd/autokernel/loop/resolved_recipe.py",
    "scripts/kernel_rnd/autokernel/loop/native_model_preparation.py",
    "scripts/kernel_rnd/autokernel/loop/measurement_capture.py", "scripts/kernel_rnd/autokernel/loop/worker_lifecycle.py",
    "scripts/benchmark/run_autokernel_cpu_profile.py",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PinError(RuntimeError):
    pass


def _eval(node: ast.AST, env: dict):
    """Evaluate the literal shapes pins are written in (str, dict, tuple, parenthesised str, earlier names)."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.Dict):
        return {_eval(k, env): _eval(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_eval(e, env) for e in node.elts)
    raise ValueError(f"unsupported pin expression {type(node).__name__}")


def module_constants(path: Path) -> dict:
    """Module-level ``NAME = <literal>`` assignments of an adapter, read from SOURCE (never imported: importing an
    adapter registers its projection, and a second registration under another module name is refused)."""
    env: dict = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                env[node.targets[0].id] = _eval(node.value, env)
            except (ValueError, TypeError):
                continue
    return env


def adapter_constant(module: str, const: str):
    return module_constants(HERE / "adapters" / f"{module}.py")[const]


def rolling_pins() -> dict:
    """``SAMPLED_CPU_ROLLING_PINS`` (research full sha -> closure digest), in file order; the last is the tracked pin."""
    return dict(module_constants(PROFILE_PATH)["SAMPLED_CPU_ROLLING_PINS"])


def _git(repo: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text, check=False, timeout=120)


def _blob(repo: Path, ref: str, path: str) -> bytes | None:
    done = _git(repo, "show", f"{ref}:{path}", text=False)
    return done.stdout if done.returncode == 0 else None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _commits_touching(repo: Path, ref: str, path: str) -> list[str]:
    done = _git(repo, "log", "--format=%H", "-n", str(HISTORY_CAP), ref, "--", path)
    return done.stdout.split() if done.returncode == 0 else []


def resolve_pinned_commit(repo: Path, ref: str, path: str, pinned: str) -> str | None:
    """The newest commit on ``ref`` whose blob of ``path`` hashes to ``pinned`` (None: no version reproduces it)."""
    for commit in _commits_touching(repo, ref, path):
        blob = _blob(repo, commit, path)
        if blob is not None and _sha(blob) == pinned:
            return commit
    return None


def changed_since(repo: Path, base: str, ref: str, paths: list[str] | tuple[str, ...]) -> list[dict]:
    """``git log <base>..<ref> -- <paths>``: the commits (newest first) that touched the pinned files."""
    done = _git(repo, "log", "--format=%H%x09%cs%x09%s", f"{base}..{ref}", "--", *paths)
    rows = []
    for line in done.stdout.splitlines():
        sha, date, subject = (line.split("\t", 2) + ["", ""])[:3]
        rows.append({"commit": sha, "date": date, "subject": subject})
    return rows


@dataclass
class Row:
    pin: str
    status: str  # CURRENT | STALE | UNRESOLVED | UNMAPPED | NO_REPO
    detail: str = ""
    pinned_commit: str | None = None
    ref_commit: str | None = None
    new_digest: str | None = None
    changed: tuple = ()

    def as_dict(self) -> dict:
        return {"pin": self.pin, "status": self.status, "detail": self.detail, "pinned_commit": self.pinned_commit,
                "ref_commit": self.ref_commit, "new_digest": self.new_digest, "changed_by": list(self.changed)}


def _repo_ref(repo_name: str, ref: str) -> tuple[Path, str | None]:
    repo = REPOS[repo_name]
    done = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return repo, (done.stdout.strip() if done.returncode == 0 else None)


def _file_row(label: str, repo_name: str, ref: str, path: str, pinned: str) -> Row:
    repo, ref_commit = _repo_ref(repo_name, ref)
    if ref_commit is None:
        return Row(label, "NO_REPO", f"{repo_name} repo {repo} has no ref {ref}")
    blob = _blob(repo, ref_commit, path)
    if blob is None:
        return Row(label, "UNRESOLVED", f"{path} absent at {ref} ({ref_commit[:9]})", ref_commit=ref_commit)
    now = _sha(blob)
    if now == pinned:
        return Row(label, "CURRENT", f"{path} at {ref_commit[:9]} hashes to the pin", ref_commit=ref_commit,
                   new_digest=now)
    pinned_commit = resolve_pinned_commit(repo, ref_commit, path, pinned)
    if pinned_commit is None:
        return Row(label, "UNRESOLVED", f"no committed version of {path} on {ref} hashes to the pin "
                   f"{pinned[:12]} (drift, or an uncommitted/other-branch producer)", ref_commit=ref_commit,
                   new_digest=now)
    changes = changed_since(repo, pinned_commit, ref_commit, [path])
    return Row(label, "STALE", f"{path}: pinned at {pinned_commit[:9]}, {len(changes)} commit(s) since on {ref}",
               pinned_commit=pinned_commit, ref_commit=ref_commit, new_digest=now, changed=tuple(changes))


def _closure_row(ref: str) -> Row:
    pins = rolling_pins()
    label = f"{PROFILE}.SAMPLED_CPU_ROLLING_PINS[-1]"
    if not pins:
        return Row(label, "UNRESOLVED", "no rolling pin recorded")
    last, digest = list(pins.items())[-1]
    repo, ref_commit = _repo_ref("research", ref)
    if ref_commit is None:
        return Row(label, "NO_REPO", f"research repo {repo} has no ref {ref}")
    if _git(repo, "cat-file", "-e", f"{last}^{{commit}}").returncode != 0:
        return Row(label, "UNRESOLVED", f"pinned commit {last[:9]} is not in {repo}", ref_commit=ref_commit)
    changes = changed_since(repo, last, ref_commit, CLOSURE_FILES)
    if not changes:
        return Row(label, "CURRENT", f"no closure file changed on {ref} since {last[:9]}", pinned_commit=last,
                   ref_commit=ref_commit, new_digest=digest)
    return Row(label, "STALE", f"{len(changes)} commit(s) touched the sampled-CPU closure on {ref} since {last[:9]}; "
               f"live producer captures will be refused until `repin --apply`", pinned_commit=last,
               ref_commit=ref_commit, changed=tuple(changes))


def discover_pin_constants() -> list[tuple[str, str]]:
    """Every (adapter module, NAME) in ``adapters/*.py`` whose NAME looks like a pinned sha256/digest literal."""
    found = []
    pat = re.compile(r'^([A-Z][A-Z0-9_]*(?:SHA256|SHA|DIGEST)[A-Z0-9_]*)\s*=\s*\(?\s*"[0-9a-f]{64}"', re.M)
    for path in sorted((HERE / "adapters").glob("*.py")):
        for name in pat.findall(path.read_text()):
            found.append((path.stem, name))
    for path in sorted((HERE / "adapters").glob("*.py")):
        if re.search(r"^PRODUCERS\s*=\s*\{", path.read_text(), re.M):
            found.append((path.stem, "PRODUCERS"))
    return found


def check(ref: str = "origin/main") -> list[Row]:
    rows: list[Row] = []
    mapped = {(m, c) for m, c, *_ in FILE_PINS}
    for module, const, repo_name, path, kind in FILE_PINS:
        label = f"{module}.{const}"
        try:
            value = adapter_constant(module, const)
        except Exception as exc:  # noqa: BLE001 -- a pin that cannot be read is itself the finding
            rows.append(Row(label, "UNRESOLVED", f"adapter pin unreadable: {exc!r}"))
            continue
        if kind == "file":
            rows.append(_file_row(label, repo_name, ref, path, value))
        else:
            for name, digest in sorted(value.items()):
                rows.append(_file_row(f"{label}[{name}]", repo_name, ref, f"{path}/{name}", digest))
    for module, const in discover_pin_constants():
        if (module, const) not in mapped and (module, const) not in EXEMPT:
            rows.append(Row(f"{module}.{const}", "UNMAPPED", "a pinned digest nobody watches: add it to FILE_PINS "
                            "or EXEMPT (with the reason) in scripts/vidya/producer_pins.py"))
    rows.append(_closure_row(ref))
    return rows


# ------------------------------------------------------------------------------------------------ digest / repin
_DIGEST_CODE = (
    "import json,sys\n"
    "sys.dont_write_bytecode=True\n"
    "from autokernel.loop import cpu_profile as c, lifecycle_observation as lo\n"
    "si=c.source_identity()\n"
    "print(json.dumps({'digest': lo._digest(si), 'files': [f['relative_path'] for f in si['files']],\n"
    "                  'python': si['python']['sha256']}))\n")


def closure_digest(ref: str) -> dict:
    """The producer's own ``_digest(cpu_profile.source_identity())`` on a ``git archive`` of ``ref`` (research)."""
    repo, commit = _repo_ref("research", ref)
    if commit is None:
        raise PinError(f"research repo {repo} has no ref {ref}")
    with tempfile.TemporaryDirectory(prefix="producer-pins-") as tmp:
        archive = subprocess.run(["git", "-C", str(repo), "archive", commit, "scripts"], capture_output=True,
                                 check=False, timeout=300)
        if archive.returncode != 0:
            raise PinError(f"git archive {commit[:9]} failed: {archive.stderr[-300:]!r}")
        done = subprocess.run(["tar", "-x", "-C", tmp], input=archive.stdout, capture_output=True, check=False)
        if done.returncode != 0:
            raise PinError(f"tar failed: {done.stderr[-300:]!r}")
        env = {**os.environ, "PYTHONPATH": f"{tmp}/scripts/kernel_rnd", "PYTHONDONTWRITEBYTECODE": "1"}
        ran = subprocess.run([PYTHON313, "-c", _DIGEST_CODE], cwd=tmp, env=env, capture_output=True, text=True,
                             check=False, timeout=300)
        if ran.returncode != 0:
            raise PinError(f"source_identity failed at {commit[:9]}: {ran.stderr[-500:]}")
    out = json.loads(ran.stdout.strip().splitlines()[-1])
    out["commit"] = commit
    out["closure_files_match_manifest"] = out["files"] == list(CLOSURE_FILES)
    return out


_BLOCK = re.compile(r"(# --- ROLLING-PINS-BEGIN.*?\nSAMPLED_CPU_ROLLING_PINS = \{\n)(.*?)(\}\n# --- ROLLING-PINS-END)", re.S)


def apply_rolling_pin(source: str, commit: str, digest: str) -> str:
    """``source`` with ``commit -> digest`` appended to the ROLLING-PINS block (idempotent; refuses a conflict)."""
    if not (re.fullmatch(r"[0-9a-f]{40}", commit) and _HEX64.match(digest)):
        raise PinError("rolling pin needs a full 40-hex commit and a 64-hex digest")
    m = _BLOCK.search(source)
    if not m:
        raise PinError("ROLLING-PINS block not found in autokernel_profile.py")
    body = m.group(2)
    if f'"{commit}"' in body:
        raise PinError(f"{commit[:9]} is already pinned")
    line = f'    "{commit}": (\n        "{digest}"),\n'
    return source[:m.start(2)] + body + line + source[m.end(2):]


def repin(ref: str, apply: bool) -> int:
    info = closure_digest(ref)
    print(f"closure digest at research {ref} ({info['commit'][:9]}): {info['digest']}")
    if not info["closure_files_match_manifest"]:
        print("WARNING: source_identity()['files'] differs from CLOSURE_FILES in producer_pins.py; update the "
              f"manifest (now: {info['files']})", file=sys.stderr)
    if info["digest"] in set(rolling_pins().values()):
        print("already pinned: nothing to do")
        return 0
    if not apply:
        print(f"plan: append {info['commit']} -> {info['digest']} to SAMPLED_CPU_ROLLING_PINS in {PROFILE_PATH}")
    else:
        PROFILE_PATH.write_text(apply_rolling_pin(PROFILE_PATH.read_text(), info["commit"], info["digest"]))
        print(f"appended to {PROFILE_PATH}")
    print("then re-run the producer-backed tests BEFORE committing:\n"
          f"  EPYC_RESEARCH_ROOT={REPOS['research']} /usr/bin/python3 -m pytest "
          "tests/vidya/test_autokernel_profile_adapter.py tests/vidya/test_loop_cpu_profile_adapter.py -q")
    return 0


def render(rows: list[Row], ref: str) -> str:
    out = [f"producer pins vs {ref}"]
    for r in rows:
        out.append(f"  {r.status:<10} {r.pin}  -- {r.detail}")
        for c in r.changed[:8]:
            out.append(f"             {c['commit'][:9]} {c['date']} {c['subject'][:90]}")
        if len(r.changed) > 8:
            out.append(f"             ... {len(r.changed) - 8} more")
    bad = [r for r in rows if r.status != "CURRENT"]
    out.append(f"{len(rows) - len(bad)}/{len(rows)} current; {len(bad)} need attention" if bad else
               f"all {len(rows)} pins current")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--ref", default="origin/main")
    c.add_argument("--json", action="store_true")
    d = sub.add_parser("digest")
    d.add_argument("--ref", default="origin/main")
    r = sub.add_parser("repin")
    r.add_argument("--ref", default="origin/main")
    r.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "check":
            rows = check(a.ref)
            print(json.dumps([r.as_dict() for r in rows], indent=1) if a.json else render(rows, a.ref))
            return 0 if all(r.status == "CURRENT" for r in rows) else 3
        if a.cmd == "digest":
            print(json.dumps(closure_digest(a.ref), indent=1))
            return 0
        return repin(a.ref, a.apply)
    except PinError as exc:
        print(f"producer_pins: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
