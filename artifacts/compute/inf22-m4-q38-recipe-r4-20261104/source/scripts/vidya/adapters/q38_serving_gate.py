"""VB-Q38-T10-1-GATE-WIRE: Q38-T10.1 serving-gate per-prompt outcome statistics as measurement OBSERVATIONS.

Source: one serving-gate PHASE run dir (``serving_gate.py`` output: ``summary.json``, ``<tag>_off_A/_off_B/<spec>.records.jsonl``,
``per_prompt.tsv``, ``config_echo.<phase>.json``, ``phase.<phase>.json``) plus the gate directory above it
(``corpus.sha256``, ``PREDECLARED_RULE.md``). Read-side post-processor: no producer change, no inference.

One sidecar ``q38_serving_gate.beliefs.jsonl`` per phase run, five rows over the CLEAN prompts (truncated prompts stay LISTED in
the recorded per-prompt payload and counted in ``extra.n_excluded_truncated``; they are excluded from the statistics exactly
as the gate does, never dropped silently):

* ``q38_sg_net_regressions_R``  prompts that pass spec-off and fail spec-on        (lower_better, count)
* ``q38_sg_net_gains_G``        prompts that fail spec-off and pass spec-on        (higher_better, count)
* ``q38_sg_net_p_one_sided``    exact one-sided sign test P(X >= R | n=R+G, p=.5)   (the predeclared rule's own statistic)
* ``q38_sg_token_identical_fraction``  clean prompts whose spec-off and spec-on token streams are identical
* ``q38_sg_pass_concordance``   (both-pass + both-fail) / clean

Doctrine: PROJECTION ONLY. The pass/fail bit per prompt is the gate's own grade (``summary.json`` rows, cross-checked against
``per_prompt.tsv`` and re-checked against the per-arm records for truncation, token counts and first divergence); the
reader re-derives R, G, both-pass, both-fail, p, token-identity, concordance and the A/A identical count from the recorded
per-prompt payload and refuses any difference. The predeclared rule's PASS/FAIL word is carried as ``outcome_native`` after
being re-derived from p (the rule's own sentence), not a new grading rule. Validity preconditions (A/A all identical, pids
dead, residency/guards, spec arm live, off arms drafted zero, n_clean >= min_n, phase COMPLETE) not met => NO rows.
``protocol_id`` is empty (a predeclared one-window gate is not a codified protocol), so the ladder caps the tuples.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._argv_scope import scope_from_argv  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.q38_serving_gate_capture.v1"
SIDECAR_NAME = "q38_serving_gate.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.q38_serving_gate/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "q38-serving-gate"
RULE_PREFIX, RULE_SUFFIX = "350a2a20", "ffb3"
PHASES = {"gpu": ("gpu_off_A", "gpu_off_B", "gpu_dflash2"), "cpu": ("cpu_off_A", "cpu_off_B", "cpu_mtp")}
M_R, M_G, M_P = "q38_sg_net_regressions_R", "q38_sg_net_gains_G", "q38_sg_net_p_one_sided"
M_TOK, M_CONC = "q38_sg_token_identical_fraction", "q38_sg_pass_concordance"
METRICS = frozenset({M_R, M_G, M_P, M_TOK, M_CONC})
ALPHA = 0.05
REL = 1e-9
OUTCOMES = ("SAME_PASS", "SAME_FAIL", "REGRESSION", "GAIN", "EXCLUDED_TRUNCATED")
PROMPT_KEYS = ("id", "kind", "base_pass", "spec_pass", "truncated_any", "n_tok_base", "n_tok_spec", "first_divergence",
               "aa_identical", "outcome")


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL, abs_tol=1e-12)


def _sha(path: Path) -> str:
    return ns.file_sha256(path)


def _p_one(r: int, g: int) -> float:
    nd = r + g
    return sum(math.comb(nd, i) for i in range(r, nd + 1)) / 2 ** nd if nd else 1.0


def _outcome(base: bool, spec: bool, trunc: bool) -> str:
    if trunc:
        return "EXCLUDED_TRUNCATED"
    if base and not spec:
        return "REGRESSION"
    if spec and not base:
        return "GAIN"
    return "SAME_PASS" if base else "SAME_FAIL"


def _first_div(a: list, b: list):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def derive(prompts: list[dict]) -> dict:
    """Every statistic the reader/writer share, from the per-prompt payload alone."""
    clean = [p for p in prompts if p["outcome"] != "EXCLUDED_TRUNCATED"]
    cnt = {o: sum(1 for p in clean if p["outcome"] == o) for o in OUTCOMES}
    n = len(clean)
    r, g = cnt["REGRESSION"], cnt["GAIN"]
    ident = sum(1 for p in clean if p["first_divergence"] is None)
    return {"n_listed": len(prompts), "n_clean": n, "n_excluded": len(prompts) - n, "R": r, "G": g,
            "both_pass": cnt["SAME_PASS"], "both_fail": cnt["SAME_FAIL"], "token_identical": ident,
            "p_one": _p_one(r, g), "aa_identical": sum(1 for p in prompts if p["aa_identical"]),
            "rule_verdict": "FAIL" if _p_one(r, g) < ALPHA else "PASS"}


def prompt_problems(prompts: Any) -> list[str]:
    if not isinstance(prompts, list) or not prompts:
        return ["extra.prompts must list every corpus prompt"]
    out: list[str] = []
    seen: set[str] = set()
    for i, p in enumerate(prompts):
        if not isinstance(p, dict) or set(p) != set(PROMPT_KEYS):
            return [f"prompts[{i}] must have exactly the keys {list(PROMPT_KEYS)}"]
        if not ns.text(p["id"]) or p["id"] in seen:
            out.append(f"prompts[{i}].id missing or duplicated")
        seen.add(str(p["id"]))
        if not (isinstance(p["base_pass"], bool) and isinstance(p["spec_pass"], bool)
                and isinstance(p["truncated_any"], bool) and isinstance(p["aa_identical"], bool)):
            out.append(f"prompts[{i}] pass/truncated/aa flags must be booleans")
            continue
        if p["outcome"] != _outcome(p["base_pass"], p["spec_pass"], p["truncated_any"]):
            out.append(f"prompts[{i}].outcome does not re-derive from its pass bits and truncation")
        if not (ns.nonneg_int(p["n_tok_base"]) and ns.nonneg_int(p["n_tok_spec"])):
            out.append(f"prompts[{i}] token counts must be non-negative ints")
        fd = p["first_divergence"]
        if not (fd is None or ns.nonneg_int(fd)):
            out.append(f"prompts[{i}].first_divergence must be null or a non-negative int")
        elif fd is None and p["n_tok_base"] != p["n_tok_spec"]:
            out.append(f"prompts[{i}] has no divergence but unequal token counts")
    return out


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: a predeclared one-window gate, no codified protocol")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    if e.get("phase") not in PHASES:
        p.append("extra.phase must be gpu or cpu")
    rule = str(e.get("rule_sha256", ""))
    if not (ns.SHA256.match(rule) and rule.startswith(RULE_PREFIX) and rule.endswith(RULE_SUFFIX)):
        p.append("extra.rule_sha256 must be the predeclared rule (350a2a20...ffb3)")
    if not ns.SHA256.match(str(e.get("corpus_sha256", ""))):
        p.append("extra.corpus_sha256 must be a 64-hex digest")
    if not ns.text(e.get("model_file")) or not ns.text(e.get("bin_dir")) or not isinstance(e.get("spec_argv"), list) \
            or not isinstance(e.get("off_argv"), list):
        p.append("extra must carry model_file, bin_dir and both argvs from the config echo")
    if not (ns.nonneg_int(e.get("n_predict")) and e["n_predict"] > 0):
        p.append("extra.n_predict must be a positive int")
    pp = prompt_problems(e.get("prompts"))
    p += pp
    if not pp:
        d = derive(e["prompts"])
        if d["aa_identical"] != d["n_listed"] or e.get("aa_identical") != f"{d['aa_identical']}/{d['n_listed']}":
            p.append("A/A not identical on every prompt (or extra.aa_identical does not re-derive): validity precondition unmet")
        if not (ns.nonneg_int(e.get("min_n")) and d["n_clean"] >= e["min_n"]):
            p.append("clean prompts below the gate's min_n")
        for k, key in (("n_clean", "n_clean"), ("n_excluded_truncated", "n_excluded"), ("R", "R"), ("G", "G"),
                       ("both_pass", "both_pass"), ("both_fail", "both_fail"), ("token_identical", "token_identical")):
            if e.get(k) != d[key]:
                p.append(f"extra.{k} does not re-derive from extra.prompts")
        if not (ns.finite(e.get("p_one_sided")) and _close(e["p_one_sided"], d["p_one"])):
            p.append("extra.p_one_sided does not re-derive from R and G")
        if e.get("rule_verdict") != d["rule_verdict"]:
            p.append("extra.rule_verdict does not re-derive from p (alpha 0.05)")
        want = {M_R: float(d["R"]), M_G: float(d["G"]), M_P: d["p_one"],
                M_TOK: d["token_identical"] / d["n_clean"] if d["n_clean"] else None,
                M_CONC: (d["both_pass"] + d["both_fail"]) / d["n_clean"] if d["n_clean"] else None}[row["metric"]]
        if want is None or not ns.finite(row.get("value")) or not _close(row["value"], want):
            p.append("value does not re-derive from extra.prompts")
        if row.get("reps") != d["n_clean"]:
            p.append("reps must be the clean prompt count")
    g = e.get("guards")
    if not isinstance(g, dict) or not (g.get("all_pids_dead") is True and g.get("spec_arm_live") is True
                                       and g.get("off_arms_drafted_zero") is True
                                       and (g.get("hip_resident") is True if e.get("phase") == "gpu" else g.get("cpu_only") is True)):
        p.append("extra.guards must show pids dead, spec arm live, off arms drafted zero and device residency")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "metric": row["metric"], "phase": e["phase"],
                                     "results": row["results_sha256"]}, "q38sg")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


# --------------------------------------------------------------------------- write side (read-side post-processor)
def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"{path.name} unreadable: {exc}") from exc


def _records(path: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except (OSError, ValueError) as exc:
        raise CaptureError(f"{path.name} unreadable: {exc}") from exc


def _detect_phase(run: Path) -> str:
    found = [ph for ph in PHASES if (run / f"config_echo.{ph}.json").is_file() and (run / f"phase.{ph}.json").is_file()]
    if len(found) != 1:
        raise CaptureError(f"run dir must hold exactly one phase's config_echo + phase files (found {found}); pass phase=")
    return found[0]


def _rule_sha(gate_dir: Path) -> str:
    path = gate_dir / "PREDECLARED_RULE.md"
    if not path.is_file():
        raise CaptureError("PREDECLARED_RULE.md missing: the rule must be on disk to bind the claim")
    sha = _sha(path)
    if not (sha.startswith(RULE_PREFIX) and sha.endswith(RULE_SUFFIX)):
        raise CaptureError(f"PREDECLARED_RULE.md sha256 {sha} is not the predeclared rule (350a2a20...ffb3)")
    return sha


def _corpus_sha(gate_dir: Path, summary: dict) -> str:
    path = gate_dir / "corpus.sha256"
    if not path.is_file():
        raise CaptureError("corpus.sha256 missing")
    sha = path.read_text().split()[0] if path.read_text().split() else ""
    if not ns.SHA256.match(sha) or sha != summary.get("corpus_sha256"):
        raise CaptureError("corpus.sha256 does not equal summary.json corpus_sha256")
    corpus = gate_dir / "corpus.jsonl"
    if corpus.is_file() and _sha(corpus) != sha:
        raise CaptureError("corpus.jsonl no longer hashes to corpus.sha256")
    return sha


def _build_prompts(run: Path, role: dict, tag: tuple[str, str, str], tsv: Path) -> list[dict]:
    a, b, s = (_records(run / f"{t}.records.jsonl") for t in tag)
    rows = role.get("rows")
    n = role.get("n_corpus")
    if not (isinstance(rows, list) and isinstance(n, int) and len(a) == len(b) == len(s) == len(rows) == n > 0):
        raise CaptureError("arm records and summary rows must all cover the corpus (INCOMPLETE run)")
    tsv_rows = {}
    for line in tsv.read_text().splitlines()[1:]:
        f = line.split("\t")
        if len(f) >= 6:
            tsv_rows[(f[0], f[1])] = f
    out: list[dict] = []
    for ra, rb, rs, row in zip(a, b, s, rows):
        if not (ra["id"] == rb["id"] == rs["id"] == row.get("id")):
            raise CaptureError(f"prompt order disagrees between records and summary at {row.get('id')}")
        trunc = bool(ra["truncated"] or rb["truncated"] or rs["truncated"])
        fd = _first_div(ra["tokens"], rs["tokens"])
        mine = {"id": row["id"], "kind": row["kind"], "base_pass": row["base_pass"], "spec_pass": row["spec_pass"],
                "truncated_any": trunc, "n_tok_base": len(ra["tokens"]), "n_tok_spec": len(rs["tokens"]),
                "first_divergence": fd, "aa_identical": _first_div(ra["tokens"], rb["tokens"]) is None,
                "outcome": _outcome(row["base_pass"], row["spec_pass"], trunc)}
        for k in ("truncated_any", "n_tok_base", "n_tok_spec", "first_divergence", "outcome"):
            if row.get(k) != mine[k]:
                raise CaptureError(f"summary row {row['id']}.{k}={row.get(k)!r} disagrees with the records ({mine[k]!r})")
        t = tsv_rows.get((run_phase := role["_phase"], row["id"]))
        if t is None or (t[3], t[4], t[5]) != (str(row["base_pass"]), str(row["spec_pass"]), row["outcome"]):
            raise CaptureError(f"per_prompt.tsv disagrees with summary.json at {row['id']} ({run_phase})")
        out.append(mine)
    return out


def write_belief_measurements(out_dir: str | Path, *, run_dir: str | Path, run_id: str, producer: str,
                              phase: str | None = None, gate_dir: str | Path | None = None,
                              emitted_at: str | None = None) -> Path:
    run = Path(run_dir)
    gate = Path(gate_dir) if gate_dir else run.parent
    phase = phase or _detect_phase(run)
    if phase not in PHASES:
        raise CaptureError(f"phase must be one of {sorted(PHASES)}")
    summary_path = run / "summary.json"
    summary = _json(summary_path)
    role = (summary.get("roles") or {}).get(phase)
    if not isinstance(role, dict) or role.get("verdict") in (None, "INCOMPLETE") or role.get("phase_status") not in (None, "RAN_rc0"):
        raise CaptureError(f"summary.json has no completed {phase} role: nothing to project")
    if role.get("verdict") in ("VOID_AA", "VOID_GUARDS", "INSUFFICIENT_N"):
        raise CaptureError(f"{phase} role verdict {role['verdict']}: validity precondition unmet, no rows")
    echo, info = _json(run / f"config_echo.{phase}.json"), _json(run / f"phase.{phase}.json")
    rule = _rule_sha(gate)
    corpus = _corpus_sha(gate, summary)
    if echo.get("corpus_sha256") != corpus or echo.get("n_predict") != summary.get("n_predict"):
        raise CaptureError("config echo corpus sha / n_predict disagree with summary.json")
    role = dict(role, _phase=phase)
    prompts = _build_prompts(run, role, PHASES[phase], run / "per_prompt.tsv")
    d = derive(prompts)
    # guards recomputed from the records + phase file with the gate's own formula (never trusting summary.json's copy)
    servers = info.get("servers") or []
    srv = {s.get("label"): s for s in servers}
    recs = {t: _records(run / f"{t}.records.jsonl") for t in PHASES[phase]}
    drafted = sum((x.get("draft_n") or 0) for x in recs[PHASES[phase][2]])
    off_drafted = sum((x.get("draft_n") or 0) for x in recs[PHASES[phase][0]] + recs[PHASES[phase][1]])
    guards = {"all_pids_dead": len(servers) == 2 and all(s.get("dead_after") for s in servers),
              "spec_arm_drafted_tokens": drafted, "spec_arm_live": drafted > 0,
              "off_arms_drafted_tokens": off_drafted, "off_arms_drafted_zero": off_drafted == 0}
    if phase == "gpu":
        guards["hip_resident"] = bool(srv) and all(s.get("child_in_kfd_samples", 0) > 0 and s.get("busy_nonzero_samples", 0) > 0
                                                  and s.get("vram_peak_gib", 0) >= 20 for s in srv.values())
    else:
        guards["cpu_only"] = bool(srv) and all(s.get("child_in_kfd_samples", 0) == 0 for s in srv.values())
    if info.get("status") != "COMPLETE":
        raise CaptureError(f"phase.{phase}.json status {info.get('status')!r}: not COMPLETE")
    spec_argv, off_argv = echo.get("spec_argv"), echo.get("off_argv")
    if not (isinstance(spec_argv, list) and isinstance(off_argv, list)):
        raise CaptureError("config echo carries no argv")
    model = next((spec_argv[i + 1] for i, t in enumerate(spec_argv[:-1]) if t in ("-m", "--model")), "")
    bin_dir = str(echo.get("bin_dir", ""))
    binary = Path(bin_dir) / "llama-server"
    bin_sha = _sha(binary) if binary.is_file() else None
    libs = sorted({lib for s in servers for lib in (s.get("libs") or [])})
    digest = _sha(summary_path)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n = d["n_clean"]
    extra_common = {
        "phase": phase, "role": role.get("role"), "corpus_sha256": corpus, "rule_sha256": rule,
        "n_predict": echo["n_predict"], "min_n": summary.get("min_n"), "model_file": model, "bin_dir": bin_dir,
        "binary_sha256": bin_sha, "build_id": Path(bin_dir).parent.name if bin_dir else "", "libs": libs,
        "spec_argv": spec_argv, "off_argv": off_argv, "argv_source": echo.get("argv_source"),
        "aa_identical": f"{d['aa_identical']}/{d['n_listed']}", "guards": guards,
        "n_clean": n, "n_excluded_truncated": d["n_excluded"],
        "excluded_truncated": [p["id"] for p in prompts if p["outcome"] == "EXCLUDED_TRUNCATED"],
        "R": d["R"], "G": d["G"], "both_pass": d["both_pass"], "both_fail": d["both_fail"],
        "token_identical": d["token_identical"], "p_one_sided": d["p_one"], "rule_verdict": d["rule_verdict"],
        "files_sha256": {name: _sha(run / name) for name in sorted(
            [f"{t}.records.jsonl" for t in PHASES[phase]] + ["per_prompt.tsv", f"config_echo.{phase}.json", f"phase.{phase}.json"])},
        "prompts": prompts,
    }
    spec = (f"{role.get('role')}, spec-on vs spec-off, {n} clean of {d['n_listed']} prompts "
            f"({d['n_excluded']} truncated listed and excluded), A/A {extra_common['aa_identical']} identical, "
            f"corpus {corpus[:8]}, rule {rule[:8]}..{rule[-4:]}")
    specs = (
        (M_R, d["R"], "prompts (spec-off pass -> spec-on fail)", "lower_better",
         f"Q38-T10.1 serving gate {phase}: regressions R={d['R']} vs gains G={d['G']} ({spec})"),
        (M_G, d["G"], "prompts (spec-off fail -> spec-on pass)", "higher_better",
         f"Q38-T10.1 serving gate {phase}: gains G={d['G']} vs regressions R={d['R']} ({spec})"),
        (M_P, d["p_one"], "p (exact one-sided sign test, H1: R > G)", "higher_better",
         f"Q38-T10.1 serving gate {phase}: predeclared net-paired exact p={d['p_one']:.6g}, rule {d['rule_verdict']} at alpha 0.05 ({spec})"),
        (M_TOK, d["token_identical"] / n, "fraction of clean prompts", "higher_better",
         f"Q38-T10.1 serving gate {phase}: {d['token_identical']}/{n} clean prompts token-identical spec-on vs spec-off ({spec})"),
        (M_CONC, (d["both_pass"] + d["both_fail"]) / n, "fraction of clean prompts", "higher_better",
         f"Q38-T10.1 serving gate {phase}: pass/fail concordance {d['both_pass'] + d['both_fail']}/{n} ({spec})"),
    )
    rows = []
    for metric, value, unit, direction, claim in specs:
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when, "date": when,
               "metric": metric, "value": value, "unit": unit, "metric_direction": direction, "category": "CANDIDATE",
               "claim": claim, "protocol_id": "", "reps": n, "reps_basis": "clean paired prompts (one greedy generation per arm)",
               "results_path": str(summary_path), "results_sha256": digest, "extra": dict(extra_common)}
        row["measurement_id"] = "q38sg_" + ns.content_hash({"run_id": run_id, "metric": metric, "phase": phase,
                                                           "results": digest})[:24]
        ns.seal(row)
        bad = row_problems(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


# --------------------------------------------------------------------------- read side
def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("Q38 serving-gate native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("Q38 serving-gate row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"q38sg:{row['run_id']}:{e['phase']}:{row['metric']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    obs = {"outcome_native": f"{e['rule_verdict']} (net-paired rule, R={e['R']} G={e['G']}, n_clean={e['n_clean']})"[:120],
           "n_pairs": e["n_clean"]}
    spec_type = next((e["spec_argv"][i + 1] for i, t in enumerate(e["spec_argv"][:-1]) if t == "--spec-type"), "")
    applicability = scope_from_argv(
        e["spec_argv"], binary=(str(Path(e["bin_dir"]) / "llama-server") if e.get("binary_sha256") else None),
        binary_sha256=e.get("binary_sha256"), family="spec_serving_gate", varied=["spec_type"],
        dflash2=("dflash" in spec_type) if spec_type else None)
    if applicability:
        applicability["role"] = str(e.get("role") or "")[:120]
    return dataclasses.replace(tup, observation=obs, applicability=applicability)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the Q38-T10.1 serving-gate belief sidecar from a phase run dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--run-dir", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--phase", choices=sorted(PHASES))
    w.add_argument("--gate-dir")
    w.add_argument("--run-id")
    w.add_argument("--producer", default="q38t101-serving-gate/serving_gate.py")
    a = ap.parse_args(argv)
    run_id = a.run_id or f"q38-sg-{Path(a.run_dir).resolve().name}"
    try:
        path = write_belief_measurements(a.out_dir, run_dir=a.run_dir, run_id=run_id, producer=a.producer,
                                         phase=a.phase, gate_dir=a.gate_dir)
    except CaptureError as exc:
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
