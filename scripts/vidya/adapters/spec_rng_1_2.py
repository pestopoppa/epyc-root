"""SPEC-RNG.1.2 poskey DFlash2 depth-invariance run as decided, scoped OBSERVATIONS (VB-SPEC-RNG-1-2-WIRE).

Native record: one launcher directory of the SPEC-RNG.1.2 GPU run (``speculative-decoding-mtp-refresh.md``
SPEC-RNG.1.2), e.g. ``/mnt/raid0/llm/tmp/f8-launchers-20261023/spec-rng-1-2-gpu-run/``:

* ``PREDECLARATION.md``      the decision rule, written before any compute; re-hashed on read and refused unless it
                             equals ``RUN_RECORD.json``'s ``predeclaration_sha256``;
* ``out/records.jsonl``      one row per request (``phase`` main / probe / fill), re-hashed on read and refused unless
                             it equals ``out/verdict.json``'s ``records_sha256``;
* ``out/verdict.json``       the runner's ``analyze`` output (research ``f8/spec-rng-1-2-runner`` @ ``2f8af0e2d``,
                             ``scripts/benchmark/spec_rng_1_2/spec_rng_1_2.py``);
* ``VERDICT.json`` / ``RUN_RECORD.json``   the launcher's copies (verdict, gates, probe; argv, binary digests, pins);
* ``out/environ_proof.gen*.json``  ``/proc/<pid>`` readback per server generation (scope evidence only).

STRICT READER. The statistics are RE-DERIVED from the request rows exactly as the runner's ``analyze`` computes
them (two-sample chi-square homogeneity on token-id counts with ids of union count < 10 pooled, regularised upper
incomplete gamma for the survival function; Welch z-test on per-request accepted/drafted fractions; exact one-sided
sign test on the probe's discordant pairs; the gates and the verdict of the predeclared rule) and compared with
``out/verdict.json`` and the launcher copies. Any difference beyond float re-summation noise is REFUSED
(``ProjectionError``), never repaired. This mirror decides nothing: it is a check that the producer's printed
numbers are the numbers its own rows imply.

PROJECTION ONLY. ``claim_tuple.grade()`` decides every grade; this module registers no ladder. Eight tuples per run:

* one per distribution comparison -- primary ``P3`` (p3 vs p0), ``P7`` (p7 vs p0); controls ``C3``, ``C7``, ``X0``:
  value = the minimum chi-square p over the 33 (prompt x position) tests, ``anchor_value`` = the Bonferroni
  threshold 0.01/33, ``reps`` = the smallest (prompt, arm) cell n of the two arms;
* one per acceptance depth (3, 7): value = poskey mean per-request acceptance fraction, ``anchor_value`` = the
  stateful mean, ``effect_rel`` = poskey/stateful - 1, Welch p in ``extra``;
* the benefit probe: value = ``net_gain`` (seeds), ``n_pairs`` = paired seeds, sign p in ``extra``.

Class: ``verifier`` (unbound). Each tuple carries ``decided_proposition`` = what the predeclared rule decided for
that component, naming the run's verdict word VERBATIM and the PREDECLARATION.md sha256. Nothing binds that
proposition to a reuse elsewhere, so the SC56 cap holds it at ``Judged``; ``protocol_id`` is EMPTY in any case
(the run is INDICATIVE correctness, host not quiet), so the shared measurement ladder already reads it as an
OBSERVATION (Judged / Located). No throughput number is projected: the records carry request wall times only
and none is a claim of this run.

Absence: an ``INCONCLUSIVE`` run (validity failed) projects nothing -- a re-grant re-runs it. A directory that
holds ``VERDICT.json`` but is not a SPEC-RNG.1.2 launcher is declined (``[]``).

Write side (research ``f8/spec-rng-1-2-write-20261024``): the runner's ``analyze`` now stamps ``out/verdict.json`` (and the
top-level ``VERDICT.json`` it writes with ``--summary``) with the rule sha256 (``predeclaration_sha256``) and an ISO-8601
UTC ``analyzed_at``, and writes ``out/belief_measurements.jsonl`` (schema ``epyc.spec_rng_1_2.belief_measurement.v1``,
one self-hashed row per component). When those fields are present they must equal what this reader re-hashes (the rule
digest, the records digest, the out/verdict.json digest) or the run is refused. When the sidecar is present it is
CROSS-VERIFIED: row content hashes, input-file hashes, exactly the eight components, and per component the metric, unit,
category, reps, value, anchor and the decided proposition this reader builds from its own re-derivation. A verified
sidecar clears ``observation.retrofit``. A legacy run without these fields or file still reads exactly as before and
says ``observation.retrofit``.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters import _native_sidecar as ns  # noqa: E402
from adapters._argv_scope import flag, scope_from_argv  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.spec_rng_1_2/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "spec-rng-1-2"
SCHEMA = "epyc.spec_rng_1_2.launcher.v1"   # this reader's name for the launcher layout (the producer names none)
KNOB_FAMILY = "speculative_decoding"
HANDOFF_TAG = "SPEC-RNG.1.2"
RECORDS = "out/records.jsonl"
VERDICT_OUT = "out/verdict.json"
SIDECAR = "out/belief_measurements.jsonl"
SIDECAR_SCHEMA = "epyc.spec_rng_1_2.belief_measurement.v1"
_MAX_BYTES = 64 << 20

# --- the runner's predeclared constants (spec_rng_1_2.py @ 2f8af0e2d) ----------------------------------------
K_TOKENS = 12
N_PROMPTS = 3
MIN_N_CELL = 300
DEPTHS = (0, 3, 7)
RNGS = ("stateful", "poskey")
ARMS = [("s" if r == "stateful" else "p") + str(d) for r in RNGS for d in DEPTHS]
ALPHA = 0.01
ALPHA_ACC = 0.01
MIN_DRAFTED_FRAC = 0.95
MIN_REJECT_FRAC = 0.05
POOL_MIN = 10
BENEFIT_MIN_GAIN = 6
BENEFIT_ALPHA = 0.05
MIN_PROBE_PAIRS = 40
COMPARISONS = [("P3", "p3", "p0", "primary"), ("P7", "p7", "p0", "primary"),
               ("C3", "s3", "s0", "control"), ("C7", "s7", "s0", "control"), ("X0", "p0", "s0", "control")]
_VARIED = {"P3": ["request_speculative_n_max"], "P7": ["request_speculative_n_max"],
           "C3": ["request_speculative_n_max"], "C7": ["request_speculative_n_max"], "X0": ["rng_mode"]}
_REL = 1e-9


# --- statistics: a mirror of the runner, used only to REFUSE a record that does not re-derive ------------------
def _gammainc_q(a: float, x: float) -> float:
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1.0:
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(1000):
            ap += 1.0
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return max(0.0, 1.0 - s * math.exp(-x + a * math.log(x) - gln))
    tiny = 1e-300
    b = x + 1.0 - a
    c, d = 1.0 / tiny, 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return min(1.0, math.exp(-x + a * math.log(x) - gln) * h)


def _chi2_sf(stat: float, dof: int) -> float:
    return 1.0 if dof <= 0 else _gammainc_q(dof / 2.0, stat / 2.0)


def _homogeneity(ca_: dict, cb_: dict) -> tuple[float, int, float, float]:
    na, nb = sum(ca_.values()), sum(cb_.values())
    if na == 0 or nb == 0:
        return 0.0, 0, 1.0, 0.0
    ids = sorted(set(ca_) | set(cb_))
    bins, oa, ob = [], 0, 0
    for t in ids:
        ca, cb = ca_.get(t, 0), cb_.get(t, 0)
        if ca + cb < POOL_MIN:
            oa += ca
            ob += cb
        else:
            bins.append((ca, cb))
    if oa + ob > 0:
        bins.append((oa, ob))
    tv = 0.5 * sum(abs(ca_.get(t, 0) / na - cb_.get(t, 0) / nb) for t in ids)
    if len(bins) < 2:
        return 0.0, 0, 1.0, tv
    n = na + nb
    stat = 0.0
    for ca, cb in bins:
        tot = ca + cb
        ea, eb = tot * na / n, tot * nb / n
        stat += (ca - ea) ** 2 / ea + (cb - eb) ** 2 / eb
    dof = len(bins) - 1
    return stat, dof, _chi2_sf(stat, dof), tv


def _welch_p(xs: list, ys: list) -> float:
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return 1.0
    mx, my = sum(xs) / nx, sum(ys) / ny
    vx = sum((x - mx) ** 2 for x in xs) / (nx - 1)
    vy = sum((y - my) ** 2 for y in ys) / (ny - 1)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return 1.0 if mx == my else 0.0
    return math.erfc(abs(mx - my) / se / math.sqrt(2.0))


def _sign_p(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2.0 ** n


def _int(v: Any) -> bool:
    return type(v) is int


def _parse_records(raw: bytes) -> list[dict]:
    out = []
    for i, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{RECORDS} line {i} is torn: {exc}") from exc
        if not isinstance(row, dict):
            raise ProjectionError(f"{RECORDS} line {i} is not an object")
        phase = row.get("phase")
        if phase in ("main", "probe") and row.get("ok") is True:
            toks = row.get("tokens")
            if not (isinstance(toks, list) and all(_int(t) for t in toks)):
                raise ProjectionError(f"{RECORDS} line {i}: an ok {phase} row carries no integer token list")
            if not (_int(row.get("draft_n")) and _int(row.get("draft_n_accepted"))):
                raise ProjectionError(f"{RECORDS} line {i}: an ok {phase} row carries no draft counts")
        if phase == "main" and (row.get("arm") not in ARMS or not _int(row.get("prompt"))
                                or not 0 <= row["prompt"] < N_PROMPTS):
            raise ProjectionError(f"{RECORDS} line {i}: a main row names no known arm / prompt")
        if phase == "probe" and (row.get("rng") not in RNGS or row.get("cond") not in ("alone", "batched")
                                 or not _int(row.get("seed"))):
            raise ProjectionError(f"{RECORDS} line {i}: a probe row names no rng / cond / seed")
        out.append(row)
    return out


def rederive(records: list[dict]) -> dict:
    """The runner's ``analyze`` over the request rows (same keys, same rule)."""
    cells: dict = {}
    n_all: dict = {}
    for r in records:
        if r.get("phase") != "main":
            continue
        key = (r["arm"], r["prompt"])
        n_all[key] = n_all.get(key, 0) + 1
        if r.get("ok") is True and len(r["tokens"]) == K_TOKENS:
            cells.setdefault(key, []).append(r)
    n_cell = {f"{a}/{p}": len(cells.get((a, p), [])) for a in ARMS for p in range(N_PROMPTS)}
    res: dict = {"n_cell": n_cell, "gates": {}, "comparisons": {}, "acceptance": {}, "probe": {}}
    g = res["gates"]
    g["V1_cells_n_ge_min"] = all(v >= MIN_N_CELL for v in n_cell.values())
    tot_all, tot_ok = sum(n_all.values()), sum(len(v) for v in cells.values())
    g["V1b_ok_fraction_ge_99"] = tot_all > 0 and tot_ok / tot_all >= 0.99
    eng: dict = {}
    ok_eng = True
    for a in ARMS:
        d = int(a[1:])
        recs = [r for p in range(N_PROMPTS) for r in cells.get((a, p), [])]
        if d == 0:
            eng[a] = {"draft_n_total": sum(r["draft_n"] for r in recs), "n": len(recs)}
            ok_eng = ok_eng and eng[a]["draft_n_total"] == 0
            continue
        drafted = [r for r in recs if r["draft_n"] > 0]
        dn, da = sum(r["draft_n"] for r in recs), sum(r["draft_n_accepted"] for r in recs)
        eng[a] = {"n": len(recs), "drafted_frac": len(drafted) / len(recs) if recs else 0.0, "draft_n": dn,
                  "accepted": da, "reject_frac": (1 - da / dn) if dn else 0.0}
        ok_eng = ok_eng and eng[a]["drafted_frac"] >= MIN_DRAFTED_FRAC and eng[a]["reject_frac"] >= MIN_REJECT_FRAC
    res["engagement"] = eng
    g["V2_rejection_path_engaged"] = ok_eng

    def counts(arm: str, p: int, j: int) -> dict:
        c: dict = {}
        for r in cells.get((arm, p), []):
            c[r["tokens"][j]] = c.get(r["tokens"][j], 0) + 1
        return c

    for name, a_, b_, role in COMPARISONS:
        tests = []
        for p in range(N_PROMPTS):
            for j in range(1, K_TOKENS):
                stat, dof, pv, tv = _homogeneity(counts(a_, p, j), counts(b_, p, j))
                tests.append({"prompt": p, "pos": j, "stat": stat, "dof": dof, "p": pv, "tv": tv})
        m = len(tests)
        worst = min(tests, key=lambda t: t["p"])
        n0 = [_homogeneity(counts(a_, p, 0), counts(b_, p, 0))[2] for p in range(N_PROMPTS)]
        res["comparisons"][name] = {
            "A": a_, "B": b_, "role": role, "n_tests": m, "bonferroni_threshold": ALPHA / m,
            "min_p": worst["p"], "argmin": {k: worst[k] for k in ("prompt", "pos", "dof")},
            "mean_tv": sum(t["tv"] for t in tests) / m, "pass": worst["p"] >= ALPHA / m,
            "pos0_null_min_p": min(n0), "pos0_null_pass": min(n0) >= ALPHA / len(n0)}

    acc_ok = True
    for d in (3, 7):
        def fr(arm: str) -> list:
            return [r["draft_n_accepted"] / r["draft_n"] for p in range(N_PROMPTS)
                    for r in cells.get((arm, p), []) if r["draft_n"] > 0]
        xs, ys = fr(f"p{d}"), fr(f"s{d}")
        pv = _welch_p(xs, ys)
        res["acceptance"][f"depth{d}"] = {
            "poskey_mean": sum(xs) / len(xs) if xs else None, "stateful_mean": sum(ys) / len(ys) if ys else None,
            "n_poskey": len(xs), "n_stateful": len(ys), "p": pv, "pass": pv >= ALPHA_ACC}
        acc_ok = acc_ok and pv >= ALPHA_ACC
    g["acceptance_unchanged"] = acc_ok
    comps = res["comparisons"].values()
    controls_ok = (all(c["pass"] and c["pos0_null_pass"] for c in comps if c["role"] == "control")
                   and all(c["pos0_null_pass"] for c in comps if c["role"] == "primary"))
    g["controls_pass"] = controls_ok
    primary_ok = all(c["pass"] for c in comps if c["role"] == "primary")
    g["primary_poskey_invariant"] = primary_ok

    pr: dict = {}
    for r in records:
        if r.get("phase") == "probe" and r.get("ok") is True:
            pr.setdefault((r["rng"], r["seed"]), {})[r["cond"]] = r["tokens"]
    seeds = sorted({s for (_, s) in pr})
    ident: dict = {"stateful": {}, "poskey": {}}
    for s in seeds:
        for rng in RNGS:
            d_ = pr.get((rng, s), {})
            if "alone" in d_ and "batched" in d_:
                ident[rng][s] = d_["alone"] == d_["batched"]
    paired = [s for s in seeds if s in ident["stateful"] and s in ident["poskey"]]
    gain = sum(1 for s in paired if ident["poskey"][s] and not ident["stateful"][s])
    loss = sum(1 for s in paired if ident["stateful"][s] and not ident["poskey"][s])
    p_sign = _sign_p(gain, gain + loss)
    res["probe"] = {"paired_seeds": len(paired), "identical_poskey": sum(ident["poskey"][s] for s in paired),
                    "identical_stateful": sum(ident["stateful"][s] for s in paired), "poskey_only": gain,
                    "stateful_only": loss, "sign_p_one_sided": p_sign, "net_gain": gain - loss}
    g["V3_probe_paired_ge_40"] = len(paired) >= MIN_PROBE_PAIRS
    benefit = (gain - loss) >= BENEFIT_MIN_GAIN and p_sign < BENEFIT_ALPHA
    valid = g["V1_cells_n_ge_min"] and g["V1b_ok_fraction_ge_99"] and g["V2_rejection_path_engaged"] and controls_ok
    if not valid:
        verdict = "INCONCLUSIVE"
    elif not (primary_ok and acc_ok):
        verdict = "POSKEY-BIASED"
    elif not g["V3_probe_paired_ge_40"]:
        verdict = "INCONCLUSIVE"
    elif benefit:
        verdict = "CARRY"
    else:
        verdict = "DO-NOT-CARRY"
    res["verdict"] = verdict
    return res


# --- comparison of stated vs re-derived --------------------------------------------------------------------
def _same(stated: Any, derived: Any, where: str) -> None:
    if isinstance(derived, dict):
        if not isinstance(stated, dict):
            raise ProjectionError(f"{where}: stated value is not a mapping")
        for k, v in derived.items():
            if k not in stated:
                raise ProjectionError(f"{where}.{k}: absent from the stated record")
            _same(stated[k], v, f"{where}.{k}")
        return
    if type(derived) is bool or derived is None or isinstance(derived, str):
        if stated != derived or type(stated) is not type(derived):
            raise ProjectionError(f"{where}: stated {stated!r}, re-derived {derived!r}")
        return
    if type(stated) not in (int, float) or type(stated) is bool:
        raise ProjectionError(f"{where}: stated {stated!r} is not a number")
    if isinstance(derived, int) and isinstance(stated, int):
        if stated != derived:
            raise ProjectionError(f"{where}: stated {stated}, re-derived {derived}")
        return
    if not math.isclose(float(stated), float(derived), rel_tol=_REL, abs_tol=1e-15):
        raise ProjectionError(f"{where}: stated {stated!r}, re-derived {derived!r}")


def _read(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ProjectionError(f"{path.name} is not a bounded regular file")
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> tuple[dict, str]:
    raw, digest = _read(path)
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"{path.name} is not JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ProjectionError(f"{path.name} is not an object")
    return doc, digest


def _is_spec_rng(unit: Path) -> bool:
    rr = unit / "RUN_RECORD.json"
    if not rr.is_file():
        return False
    try:
        doc = json.loads(rr.read_bytes()[:_MAX_BYTES])
    except (ValueError, RecursionError):
        return False
    return isinstance(doc, dict) and HANDOFF_TAG in str(doc.get("handoff") or "")


def _scope_inputs(unit: Path, run_record: dict) -> tuple[list | None, str | None, bool]:
    """(argv, binary, readback_ok): the argv the launcher recorded, proven by every generation's environ proof."""
    argv = run_record.get("argv")
    if not (isinstance(argv, list) and all(isinstance(t, str) for t in argv)):
        return None, None, False
    idx = next((i for i, t in enumerate(argv) if t.endswith("/llama-server")), None)
    if idx is None:
        return argv, None, False
    binary = argv[idx]
    ok = str(Path(str(run_record.get("binary_dir") or "")) / "llama-server") == binary
    gens = run_record.get("server_generations")
    proofs = sorted((unit / "out").glob("environ_proof.gen*.json"))
    ok = ok and _int(gens) and gens >= 1 and len(proofs) == gens
    for proof in proofs:
        try:
            doc = json.loads(proof.read_bytes()[:_MAX_BYTES])
        except (ValueError, RecursionError):
            return argv, binary, False
        ok = ok and isinstance(doc, dict) and doc.get("cmdline") == " ".join(argv[idx:]) \
            and doc.get("graphs") == "ON" and doc.get("LLAMA_RNG_POSKEY_in_environ") is None \
            and doc.get("rng_poskey_on_cmdline") is False
    return argv, binary, bool(ok)


def _iso(epoch: Any) -> str:
    if type(epoch) not in (int, float) or not math.isfinite(epoch) or epoch <= 0:
        return ""
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _g(x: float) -> str:
    return f"{x:.4g}"


def _proposition(component: str, run: dict) -> str:
    """What the predeclared rule decided for this component, with the verdict word and the rule digest."""
    head = (f"SPEC-RNG.1.2 rule PREDECLARATION.md sha256 {run['predeclaration_sha256']}, run verdict "
            f"{run['verdict']}: ")
    if component.startswith("acceptance_depth"):
        a = run["derived"]["acceptance"][component.split("_", 1)[1]]
        body = (f"at draft depth {component[-1]} the per-request acceptance fraction poskey vs stateful has Welch "
                f"p {_g(a['p'])} {'>=' if a['pass'] else '<'} {ALPHA_ACC} (acceptance "
                f"{'unchanged' if a['pass'] else 'changed'})")
    elif component == "probe":
        p = run["derived"]["probe"]
        body = (f"the benefit probe has net_gain {p['net_gain']} of {p['paired_seeds']} paired seeds, one-sided sign "
                f"p {_g(p['sign_p_one_sided'])}; a gain needs net_gain >= {BENEFIT_MIN_GAIN} and p < {BENEFIT_ALPHA}")
    else:
        c = run["derived"]["comparisons"][component]
        body = (f"{component} ({c['A']} vs {c['B']}, {c['role']}) has minimum chi-square p {_g(c['min_p'])} over "
                f"{c['n_tests']} tests {'>=' if c['pass'] else '<'} Bonferroni {ALPHA}/{c['n_tests']} "
                f"(token distribution {'invariant' if c['pass'] else 'differs'}), index-0 null "
                f"{'passes' if c['pos0_null_pass'] else 'fails'}")
    return head + body


def _core(comp: str, d: dict) -> dict:
    """metric / value / unit / reps / category / anchor for one component, from the re-derived run (one definition for
    the projection and the sidecar cross-check)."""
    if comp in _VARIED:
        c = d["comparisons"][comp]
        cells = _cell_ns(d, c["A"], c["B"])
        return {"metric": "spec_rng_chi2_min_p", "value": c["min_p"], "unit": "p", "reps": min(cells.values()),
                "reps_basis": "scored:ok requests per (prompt, arm) cell, smallest of the compared cells",
                "category": "CANDIDATE" if c["role"] == "primary" else "BASELINE",
                "anchor_value": c["bonferroni_threshold"]}
    if comp.startswith("acceptance_depth"):
        a = d["acceptance"][comp.split("_", 1)[1]]
        return {"metric": "spec_rng_acceptance_fraction_poskey", "value": a["poskey_mean"], "unit": "fraction",
                "reps": min(a["n_poskey"], a["n_stateful"]),
                "reps_basis": "scored:drafted requests per RNG arm at this depth, smaller arm", "category": "CANDIDATE",
                "anchor_value": a["stateful_mean"]}
    if comp == "probe":
        p = d["probe"]
        return {"metric": "spec_rng_probe_net_gain", "value": p["net_gain"], "unit": "seeds", "reps": p["paired_seeds"],
                "reps_basis": "scored:paired probe seeds (alone vs batched, both RNG modes)", "category": "CANDIDATE",
                "anchor_value": None}
    raise ProjectionError(f"SPEC-RNG.1.2 component {comp!r} is unknown")


def _stamp(doc: dict, where: str, *, pre_digest: str, rec_digest: str, ov_digest: str | None) -> None:
    """The write-side fields, when a verdict file carries them, must be what this reader re-hashes."""
    if "predeclaration_sha256" in doc and doc["predeclaration_sha256"] != pre_digest:
        raise ProjectionError(f"{where} predeclaration_sha256 {doc['predeclaration_sha256']!r} is not the "
                              f"PREDECLARATION.md digest {pre_digest}")
    if "analyzed_at" in doc and not ns.utc_timestamp(doc["analyzed_at"]):
        raise ProjectionError(f"{where} analyzed_at {doc['analyzed_at']!r} is not an ISO-8601 UTC timestamp")
    if "records_sha256" in doc and doc["records_sha256"] != rec_digest:
        raise ProjectionError(f"{where} records_sha256 does not match {RECORDS}")
    if ov_digest is not None and "verdict_sha256" in doc and doc["verdict_sha256"] != ov_digest:
        raise ProjectionError(f"{where} verdict_sha256 does not match {VERDICT_OUT}")


def _cross_verify(unit: Path, run: dict, components: list[str]) -> dict:
    """Refuse unless the runner's sidecar states exactly what this reader re-derived; return its identity."""
    raw, file_sha = _read(unit / SIDECAR)
    rows = []
    for i, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{SIDECAR} line {i} is torn: {exc}") from exc
        if not isinstance(row, dict) or row.get("schema") != SIDECAR_SCHEMA:
            raise ProjectionError(f"{SIDECAR} line {i} is not a {SIDECAR_SCHEMA} row")
        try:
            sealed = ns.content_hash({k: v for k, v in row.items() if k != "content_sha256"}) == row.get("content_sha256")
        except ns.CaptureError:
            sealed = False
        if not sealed:
            raise ProjectionError(f"{SIDECAR} line {i}: content_sha256 does not bind the row")
        if not (ns.utc_timestamp(row.get("emitted_at")) and ns.utc_timestamp(row.get("analyzed_at"))):
            raise ProjectionError(f"{SIDECAR} line {i}: emitted_at / analyzed_at is not an ISO-8601 UTC timestamp")
        rows.append(row)
    by = {}
    for row in rows:
        if row.get("component") in by:
            raise ProjectionError(f"{SIDECAR} states {row.get('component')!r} twice")
        by[row.get("component")] = row
    if set(by) != set(components):
        raise ProjectionError(f"{SIDECAR} components {sorted(map(str, by))} are not the eight this run decides")
    inputs = rows[0].get("inputs")
    if not isinstance(inputs, dict) or any(r.get("inputs") != inputs for r in rows):
        raise ProjectionError(f"{SIDECAR} rows do not share one input-file manifest")
    if inputs.get(RECORDS) != run["records_sha256"] or inputs.get("PREDECLARATION.md") != run["predeclaration_sha256"]:
        raise ProjectionError(f"{SIDECAR} was not emitted from this run's records and rule")
    for rel, digest in inputs.items():
        if unit.resolve() not in (unit / rel).resolve().parents or _read(unit / rel)[1] != digest:
            raise ProjectionError(f"{SIDECAR} input {rel} does not hash to the stated sha256")
    want = {"run_name": run["run_name"], "verdict": run["verdict"], "reason": run["reason"],
            "predeclaration_sha256": run["predeclaration_sha256"], "records_sha256": run["records_sha256"],
            "verdict_sha256": run["verdict_sha256"]}
    if run.get("analyzed_at"):
        want["analyzed_at"] = run["analyzed_at"]
    for comp in components:
        row, core = by[comp], _core(comp, run["derived"])
        for key, val in want.items():
            if row.get(key) != val:
                raise ProjectionError(f"{SIDECAR} {comp}: {key} {row.get(key)!r} differs from the run's {val!r}")
        for key in ("metric", "unit", "category", "reps", "reps_basis"):
            if row.get(key) != core[key]:
                raise ProjectionError(f"{SIDECAR} {comp}: {key} {row.get(key)!r} differs from the reader's {core[key]!r}")
        for key in ("value", "anchor_value"):
            _same(row.get(key), core[key], f"{SIDECAR} {comp}.{key}")
        if row.get("decided_proposition") != _proposition(comp, run):
            raise ProjectionError(f"{SIDECAR} {comp}: decided_proposition differs from the reader's re-derivation")
    return {"path": str(unit / SIDECAR), "sha256": file_sha, "emitted_at": rows[0]["emitted_at"],
            "analyzed_at": rows[0]["analyzed_at"], "runner": rows[0].get("runner")}


def native_rows(unit_dir: str | Path) -> list[dict]:
    """Eight native rows for a valid SPEC-RNG.1.2 launcher dir; ``[]`` for a foreign dir or an INCONCLUSIVE run."""
    unit = Path(unit_dir)
    if unit.is_file():
        unit = unit.parent
    if not (unit / "VERDICT.json").is_file() or not _is_spec_rng(unit):
        return []
    run_record, rr_digest = _json(unit / "RUN_RECORD.json")
    launcher_verdict, lv_digest = _json(unit / "VERDICT.json")
    out_verdict, ov_digest = _json(unit / VERDICT_OUT)
    _pre_raw, pre_digest = _read(unit / "PREDECLARATION.md")
    if run_record.get("predeclaration_sha256") != pre_digest:
        raise ProjectionError("PREDECLARATION.md does not hash to RUN_RECORD.json predeclaration_sha256")
    rec_raw, rec_digest = _read(unit / RECORDS)
    if out_verdict.get("records_sha256") != rec_digest:
        raise ProjectionError(f"{RECORDS} does not hash to {VERDICT_OUT} records_sha256")
    _stamp(out_verdict, VERDICT_OUT, pre_digest=pre_digest, rec_digest=rec_digest, ov_digest=None)
    _stamp(launcher_verdict, "VERDICT.json", pre_digest=pre_digest, rec_digest=rec_digest, ov_digest=ov_digest)
    if "analyzed_at" in launcher_verdict and launcher_verdict["analyzed_at"] != out_verdict.get("analyzed_at"):
        raise ProjectionError("VERDICT.json and out/verdict.json disagree on analyzed_at")
    pin = unit / "PINSHA"
    if pin.is_file() and pin.read_text().strip() != str(run_record.get("runner_pin") or ""):
        raise ProjectionError("PINSHA and RUN_RECORD.json runner_pin disagree")
    claim_class = str(run_record.get("claim_class") or "")
    if not claim_class.startswith("INDICATIVE"):
        raise ProjectionError(f"RUN_RECORD.json claim_class {claim_class!r} is not the INDICATIVE class this "
                              "reader projects")

    records = _parse_records(rec_raw)
    derived = rederive(records)
    keys = ("n_cell", "gates", "comparisons", "acceptance", "probe", "engagement", "verdict")
    _same(out_verdict, {k: derived[k] for k in keys}, VERDICT_OUT)
    _same(launcher_verdict, {k: derived[k] for k in ("verdict", "gates", "probe")}, "VERDICT.json")
    stated_rr = {k: derived[k] for k in ("verdict", "gates", "acceptance", "probe", "n_cell")}
    stated_rr["comparisons"] = {n: {k: c[k] for k in ("A", "B", "role", "min_p", "bonferroni_threshold", "mean_tv",
                                                       "pass", "pos0_null_pass")}
                                for n, c in derived["comparisons"].items()}
    _same(run_record, stated_rr, "RUN_RECORD.json")
    reason = out_verdict.get("reason")
    if reason != launcher_verdict.get("reason") or reason != run_record.get("reason"):
        raise ProjectionError("the verdict reason differs between out/verdict.json, VERDICT.json and RUN_RECORD.json")
    if derived["verdict"] == "INCONCLUSIVE":
        return []   # void: validity failed, a re-grant re-runs it; no grade, no outcome

    t1 = max((r["t1"] for r in records if type(r.get("t1")) in (int, float)), default=None)
    argv, binary, readback_ok = _scope_inputs(unit, run_record)
    run = {"unit_dir": str(unit), "run_name": unit.name, "derived": derived, "verdict": derived["verdict"],
           "reason": reason if isinstance(reason, str) else "", "predeclaration_sha256": pre_digest,
           "records_sha256": rec_digest, "verdict_sha256": ov_digest, "launcher_verdict_sha256": lv_digest,
           "run_record_sha256": rr_digest, "date": _iso(t1), "argv": argv, "binary": binary,
           "readback_ok": readback_ok, "binary_sha256": run_record.get("llama_server_sha256"),
           "runner_pin": run_record.get("runner_pin"), "branch": run_record.get("branch"),
           "head": run_record.get("head"), "claim_class": claim_class,
           "analyzed_at": out_verdict.get("analyzed_at") if isinstance(out_verdict.get("analyzed_at"), str) else "",
           "verdict_carries_rule_sha": out_verdict.get("predeclaration_sha256") == pre_digest}
    components = [c[0] for c in COMPARISONS] + ["acceptance_depth3", "acceptance_depth7", "probe"]
    if (unit / SIDECAR).is_file():
        run["write_side"] = _cross_verify(unit, run, components)
    return [{"schema": SCHEMA, "component": c, "run": run, "decided_proposition": _proposition(c, run)}
            for c in components]


def _scope(run: dict, varied: list[str]) -> dict:
    argv = run.get("argv")
    spec = flag(argv, "--spec-type") if isinstance(argv, list) else None
    return scope_from_argv(argv, binary=run.get("binary"), binary_sha256=run.get("binary_sha256"),
                           family=KNOB_FAMILY, varied=varied,
                           dflash2=(spec == "draft-dflash") if spec else None,
                           readback_ok=bool(run.get("readback_ok")))


def _cell_ns(d: dict, *arms: str) -> dict:
    return {f"{a}/{p}": d["n_cell"][f"{a}/{p}"] for a in arms for p in range(N_PROMPTS)}


@register(SOURCE_KIND, source_class="verifier", decided_proposition_field="decided_proposition")
def project(native: dict) -> ClaimTuple:
    run = native.get("run")
    comp = native.get("component")
    if native.get("schema") != SCHEMA or not isinstance(run, dict) or not isinstance(run.get("derived"), dict):
        raise ProjectionError("SPEC-RNG.1.2 native row must retain its re-derived run")
    if native.get("decided_proposition") != _proposition(comp, run):
        raise ProjectionError("SPEC-RNG.1.2 decided_proposition does not re-derive from the run")
    d, verdict = run["derived"], run["verdict"]
    if verdict not in ("CARRY", "DO-NOT-CARRY", "POSKEY-BIASED"):
        raise ProjectionError(f"SPEC-RNG.1.2 verdict {verdict!r} is not a projectable verdict")
    side = run.get("write_side") if isinstance(run.get("write_side"), dict) else None
    obs: dict = {"retrofit": side is None, "outcome_reason": (run["reason"] or verdict)[:300]}
    extra: dict = {"schema": SCHEMA, "component": comp, "rule": "PREDECLARATION.md",
                   "predeclaration_sha256": run["predeclaration_sha256"], "verdict": verdict,
                   "reason": run["reason"], "gates": d["gates"], "records_sha256": run["records_sha256"],
                   "verdict_sha256": run["verdict_sha256"], "run_record_sha256": run["run_record_sha256"],
                   "runner_pin": run["runner_pin"], "branch": run["branch"], "head": run["head"],
                   "claim_class": run["claim_class"], "unit_dir": run["unit_dir"]}
    if run.get("analyzed_at"):
        extra["analyzed_at"] = run["analyzed_at"]
    if side:
        extra["write_side"] = side
    else:
        extra["write_side_gap"] = "the runner wrote no out/belief_measurements.jsonl; retrofit projection"
    core = _core(comp, d)
    if comp in _VARIED:
        c = d["comparisons"][comp]
        cells = _cell_ns(d, c["A"], c["B"])
        obs.update(anchor_value=c["bonferroni_threshold"], outcome_native=f"{comp} pass={str(c['pass']).lower()}; "
                   f"run verdict {verdict}"[:120])
        obs["outcome"] = "null" if c["pass"] else "refused_correctness"
        extra.update({k: c[k] for k in ("A", "B", "role", "n_tests", "bonferroni_threshold", "argmin", "mean_tv",
                                        "pass", "pos0_null_min_p", "pos0_null_pass")}, n_cell=cells)
        varied = _VARIED[comp]
        claim = (f"SPEC-RNG.1.2 {comp} ({c['A']} vs {c['B']}, {c['role']}): DFlash2 token-distribution chi-square "
                 f"min p {_g(c['min_p'])} over {c['n_tests']} (prompt x position) tests vs Bonferroni "
                 f"{_g(c['bonferroni_threshold'])} -> {'pass' if c['pass'] else 'fail'}; mean TV {_g(c['mean_tv'])}; "
                 f"n per cell {min(cells.values())}-{max(cells.values())}; Qwen3.8-27B Q8_0 + DFlash2, MI210, np 4; "
                 f"INDICATIVE; run verdict {verdict}")
    elif comp.startswith("acceptance_depth"):
        depth = comp.split("_", 1)[1]
        a = d["acceptance"][depth]
        if a["poskey_mean"] is None or a["stateful_mean"] is None or not a["stateful_mean"]:
            raise ProjectionError(f"SPEC-RNG.1.2 {comp} has no acceptance samples")
        obs.update(anchor_value=a["stateful_mean"], effect_rel=a["poskey_mean"] / a["stateful_mean"] - 1.0,
                   outcome_native=f"{depth} pass={str(a['pass']).lower()}; run verdict {verdict}"[:120],
                   outcome="null" if a["pass"] else "refused_correctness")
        extra.update(depth=int(depth[-1]), welch_p=a["p"], n_poskey=a["n_poskey"], n_stateful=a["n_stateful"],
                     **{"pass": a["pass"]}, alpha=ALPHA_ACC)
        varied = ["rng_mode"]
        claim = (f"SPEC-RNG.1.2 acceptance at draft depth {depth[-1]}: per-request accepted/drafted fraction poskey "
                 f"{_g(a['poskey_mean'])} vs stateful {_g(a['stateful_mean'])} (n {a['n_poskey']} vs "
                 f"{a['n_stateful']}), Welch p {_g(a['p'])} -> {'unchanged' if a['pass'] else 'changed'}; "
                 f"INDICATIVE; run verdict {verdict}")
    elif comp == "probe":
        p = d["probe"]
        if p["paired_seeds"] < 1:
            raise ProjectionError("SPEC-RNG.1.2 probe has no paired seeds")
        obs.update(n_pairs=p["paired_seeds"], outcome_native=f"probe net_gain={p['net_gain']}; run verdict "
                   f"{verdict}"[:120])
        if verdict in ("CARRY", "DO-NOT-CARRY"):
            obs["outcome"] = "improved" if verdict == "CARRY" else "null"
        extra.update({k: p[k] for k in ("identical_poskey", "identical_stateful", "poskey_only", "stateful_only",
                                        "sign_p_one_sided", "paired_seeds")},
                     benefit_min_gain=BENEFIT_MIN_GAIN, benefit_alpha=BENEFIT_ALPHA)
        varied = ["rng_mode", "batch_cohort"]
        claim = (f"SPEC-RNG.1.2 reproducibility probe (depth 7, seeded request alone vs in a batch of 4): poskey "
                 f"identical {p['identical_poskey']}/{p['paired_seeds']}, stateful identical "
                 f"{p['identical_stateful']}/{p['paired_seeds']}, net_gain {p['net_gain']}, one-sided sign p "
                 f"{_g(p['sign_p_one_sided'])}; INDICATIVE; run verdict {verdict}")
    else:
        raise ProjectionError(f"SPEC-RNG.1.2 component {comp!r} is unknown")
    value, unit, metric, reps = core["value"], core["unit"], core["metric"], core["reps"]
    reps_basis, category = core["reps_basis"], core["category"]
    digest = run["records_sha256"]
    return ClaimTuple(
        measurement_id=f"specrng12:v1:{run['run_name']}:{digest[:16]}:{comp}",
        metric=metric, value=value, unit=unit, date=run["date"], category=category, claim=claim,
        metric_direction="higher_better", protocol_id="", reps=reps, reps_basis=reps_basis,
        attestation_locator=f"spec-rng-1-2:{run['run_name']}:{RECORDS}#{comp}", attestation_sha256=digest,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        decided_proposition=native["decided_proposition"], source_class="verifier", binding_kind="",
        extra=extra, applicability=_scope(run, varied), observation=obs)


__all__ = ["ADAPTER_ID", "AUTHORITY", "COMPARISONS", "KNOB_FAMILY", "SOURCE_KIND", "native_rows", "project",
           "rederive"]
