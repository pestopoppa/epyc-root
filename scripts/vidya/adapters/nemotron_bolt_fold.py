"""VB-NEMOTRON-BOLT-FOLD-WIRE: Nemotron 3.5 Bolt pending-fold records as measurement OBSERVATIONS.

Source: the research artifact dir ``epyc-inference-research/artifacts/nemotron-bolt-champion-20261021/`` (a copy of the
scratch dir ``/mnt/raid0/llm/tmp/nemotron-bolt-champion-20261021/`` with a ``SHA256SUMS``). Build ``59c1b915f`` (candidate,
``champion-plus-nemotron-bolt-20261021``) on champion ``dd3d9721c``. Every source file is verified against ``SHA256SUMS``
before it is read; a file that is absent, unlisted or mismatching yields NO row.

Row families (``extra.ident`` names the member; all ``protocol_id`` empty, so the ladder caps them as observations):

* speed (INDICATIVE): MI210 llama-bench ``pp512`` / ``tg128`` (``bench_gpu.md`` + ``bench_load.txt``) and the three-run
  server recipe timings in ``gpu_coh.json``. Shared GPU claim, host load ~98, no A/B, no floor: the rows carry the caveat
  and NO ``noise_floor`` / ``decisive`` anywhere. NOTE: no CPU llama-bench exists in the record; none is invented.
* coherence: ``gpu_coh.json`` reasoning on / off clean fractions plus the VRAM / KFD residency sample fraction (the
  residency was sampled DURING the run, the sample counts are carried).
* identity: ``greedy_{ctl,cand}.json`` Qwen3.6 greedy byte identity (identical / total) vs the champion build.
* op test: ``tbo_*.log`` test-backend-ops pass / total per (arm, op), parsed from the log's own summary line.

PROJECTION ONLY: a strict reader re-derives every value from the counts / lines recorded in the row; the attestation is
the SHA256SUMS-verified source file (``results_path`` / ``results_sha256``, re-hashed on read).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.nemotron_bolt_fold_capture.v1"
SIDECAR_NAME = "nemotron_bolt_fold.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.nemotron_bolt_fold/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "nemotron-bolt-fold"
REL = 1e-6
ANSI = re.compile(r"\x1b\[[0-9;]*m")
GIB = 1 << 30

M_PP, M_TG = "nemotron_bolt_llamabench_pp512_ts", "nemotron_bolt_llamabench_tg128_ts"
M_RPP, M_RTG = "nemotron_bolt_server_recipe_pp_ts", "nemotron_bolt_server_recipe_tg_ts"
M_COH = "nemotron_bolt_gpu_coherence_clean_fraction"
M_RES = "nemotron_bolt_gpu_residency_sample_fraction"
M_IDENT = "nemotron_bolt_qwen36_greedy_byte_identity_fraction"
M_TBO = "nemotron_bolt_tbo_pass_fraction"
SPEED_METRICS = frozenset({M_PP, M_TG, M_RPP, M_RTG})
METRICS = SPEED_METRICS | {M_COH, M_RES, M_IDENT, M_TBO}
CAVEAT = ("INDICATIVE only: shared GPU claim (gpu-quiet taken shared), host load average ~98, no A/B arm, no noise "
          "floor; not a gating speed measurement")
FORBIDDEN_SPEED_EXTRA = ("noise_floor", "noise_floor_rel", "decisive", "effect_rel", "anchor_value")
TBO_ARMS = {"cpu": ("CPU", "cand"), "gpu_cand": ("ROCm0", "cand"), "gpu_ctl": ("ROCm0", "ctl")}
SHA_IN_PATH = re.compile(r"-(\d{8})-([0-9a-f]{7,40})(?:-[A-Za-z0-9_]+)?/")
TBO_SUMMARY = re.compile(r"^\s*(\d+)/(\d+) tests passed\s*$", re.M)
TBO_BACKEND = re.compile(r"^\s*Backend (\S+): (OK|FAILED|FAIL)\s*$", re.M)


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL, abs_tol=1e-9)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------------------------- source parsing
def _build_from_bin(path: Any) -> tuple[str, str] | None:
    m = SHA_IN_PATH.search(str(path)) if isinstance(path, str) else None
    return (m.group(1), m.group(2)) if m else None


def _parse_bench_line(line: str) -> dict | None:
    """``| model | size | params | backend | ngl | threads | fa | test | t/s ± sd |`` -> fields."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 9 or cells[7] not in ("pp512", "tg128"):
        return None
    m = re.fullmatch(r"([0-9.]+) ± ([0-9.]+)", cells[8])
    if not m or not all(re.fullmatch(r"\d+", cells[i]) for i in (4, 5, 6)):
        return None
    return {"model_arch": cells[0], "backend": cells[3], "ngl": int(cells[4]), "threads": int(cells[5]),
            "fa": int(cells[6]), "test": cells[7], "mean": float(m.group(1)), "sd": float(m.group(2))}


def _parse_load_line(line: str) -> float | None:
    m = re.search(r"load average:\s*([0-9.]+),", line)
    return float(m.group(1)) if m else None


def _parse_tbo(text: str) -> dict | None:
    t = ANSI.sub("", text)
    sm = TBO_SUMMARY.search(t)
    if not sm:
        return None
    passed, total = int(sm.group(1)), int(sm.group(2))
    bm = TBO_BACKEND.search(t, sm.end())
    if not bm or total <= 0:
        return None
    n_fail = len(re.findall(r"\): (?:FAIL|FAILED)\b", t))
    return {"summary_line": sm.group(0).strip(), "backend_line": bm.group(0).strip(), "passed": passed,
            "total": total, "backend": bm.group(1), "n_fail_lines": n_fail}


# ----------------------------------------------------------------------------------------------- SHA256SUMS
def _verified_sums(adir: Path) -> dict[str, str]:
    sums = adir / "SHA256SUMS"
    try:
        body = sums.read_text()
    except OSError as exc:
        raise CaptureError(f"SHA256SUMS unreadable in {adir}: {exc}") from exc
    out: dict[str, str] = {}
    for line in body.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and ns.SHA256.match(parts[0]):
            out[Path(parts[1].strip().lstrip("*")).name] = parts[0]
    if not out:
        raise CaptureError("SHA256SUMS lists no files")
    return out


class _Src:
    """A source file that is listed in SHA256SUMS and still hashes to the listed digest, else ``None``."""

    def __init__(self, adir: Path, listed: dict[str, str]):
        self.adir, self.listed, self.skipped = adir, listed, []

    def get(self, name: str) -> tuple[Path, str, str] | None:
        p = self.adir / name
        if name not in self.listed or not p.is_file():
            self.skipped.append(f"{name}: absent or unlisted")
            return None
        digest = ns.file_sha256(p)
        if digest != self.listed[name]:
            self.skipped.append(f"{name}: sha256 mismatch against SHA256SUMS")
            return None
        return p, digest, p.read_text(errors="replace")


# ----------------------------------------------------------------------------------------------- reader
def _num_list(xs: Any, n: int | None = None) -> bool:
    return isinstance(xs, list) and bool(xs) and all(ns.finite(x) for x in xs) and (n is None or len(xs) == n)


def _speed_problems(row: dict, e: dict) -> list[str]:
    p: list[str] = []
    if e.get("caveat") != CAVEAT:
        p.append("extra.caveat must carry the indicative-only caveat verbatim")
    for k in FORBIDDEN_SPEED_EXTRA:
        if k in e:
            p.append(f"extra.{k} must be absent: a speed row can never carry a floor / decisive field")
    if row["metric"] in (M_PP, M_TG):
        want = "pp512" if row["metric"] == M_PP else "tg128"
        parsed = _parse_bench_line(e.get("source_line", "")) if ns.text(e.get("source_line")) else None
        if not parsed or parsed["test"] != want:
            p.append("extra.source_line must be the llama-bench markdown row for this test")
        else:
            if not _close(parsed["mean"], row["value"]):
                p.append("value must equal the t/s mean in extra.source_line")
            if not (ns.finite(e.get("sd")) and _close(parsed["sd"], e["sd"])):
                p.append("extra.sd must re-derive from extra.source_line")
            for k in ("threads", "ngl", "fa"):
                if e.get(k) != parsed[k]:
                    p.append(f"extra.{k} must re-derive from extra.source_line")
        load = _parse_load_line(e.get("load_line", "")) if ns.text(e.get("load_line")) else None
        if load is None or not (ns.finite(e.get("load1")) and _close(load, e["load1"])):
            p.append("extra.load1 must re-derive from extra.load_line (bench_load.txt)")
        elif load < 50:
            p.append("extra.load1 below 50: not the shared-host case this caveat describes")
        b = re.search(r"build: ([0-9a-f]{7,40}) \(", e.get("build_line", "") or "")
        if not b or e.get("build_sha") != b.group(1):
            p.append("extra.build_sha must re-derive from extra.build_line")
        m = re.search(r" -r (\d+) ", e.get("bench_cmd", "") or "")
        if not m or row.get("reps") != int(m.group(1)):
            p.append("reps must re-derive from the -r argument in extra.bench_cmd")
    else:
        vals = e.get("values")
        if not _num_list(vals, 3) or any(v <= 0 for v in vals):
            p.append("extra.values must be the three recipe timings")
        elif not _close(sum(vals) / len(vals), row["value"]):
            p.append("value must equal the mean of extra.values")
        if row.get("reps") != 3:
            p.append("reps must be the three recipe requests")
        if _build_from_bin(e.get("bin")) is None or e.get("build_sha") != (_build_from_bin(e.get("bin")) or ("", ""))[1]:
            p.append("extra.build_sha must re-derive from extra.bin")
    return p


def _coh_problems(row: dict, e: dict) -> list[str]:
    p: list[str] = []
    pr = e.get("prompts")
    if e.get("reasoning") not in ("on", "off"):
        p.append("extra.reasoning must be on or off")
    if not isinstance(pr, list) or not pr or not all(
            isinstance(x, dict) and ns.text(x.get("prompt_sha256")) and isinstance(x.get("rep_loop"), bool)
            and ns.nonneg_int(x.get("content_len")) and ns.nonneg_int(x.get("n")) and ns.text(x.get("finish"))
            for x in pr):
        return p + ["extra.prompts must record per-prompt finish / n / rep_loop / content_len"]
    clean = sum(1 for x in pr if not x["rep_loop"] and x["content_len"] > 0)
    if e.get("n_clean") != clean or e.get("n_total") != len(pr):
        p.append("extra.n_clean / n_total must re-derive from extra.prompts")
    if not _close(clean / len(pr), row["value"]):
        p.append("value must equal clean / total of extra.prompts")
    if row.get("reps") != len(pr):
        p.append("reps must equal the prompt count")
    if e.get("n_finish_length") != sum(1 for x in pr if x["finish"] == "length"):
        p.append("extra.n_finish_length must re-derive from extra.prompts")
    thinking = e.get("reasoning") == "on"
    if any((x.get("reasoning_len", 0) > 0) != thinking for x in pr):
        p.append("reasoning on/off must agree with the per-prompt reasoning_len")
    return p


def _res_problems(row: dict, e: dict) -> list[str]:
    s = e.get("samples")
    if not isinstance(s, list) or not s or not all(
            isinstance(x, dict) and ns.nonneg_int(x.get("vram0")) and isinstance(x.get("kfd"), bool) for x in s):
        return ["extra.samples must record per-sample vram0 / kfd"]
    p: list[str] = []
    res = sum(1 for x in s if x["vram0"] >= GIB and x["kfd"])
    if e.get("n_samples") != len(s) or e.get("n_resident") != res:
        p.append("extra.n_samples / n_resident must re-derive from extra.samples")
    if not _close(res / len(s), row["value"]):
        p.append("value must equal n_resident / n_samples")
    if e.get("vram_max_bytes") != max(x["vram0"] for x in s):
        p.append("extra.vram_max_bytes must re-derive from extra.samples")
    if row.get("reps") != len(s):
        p.append("reps must equal the sample count")
    return p


def _ident_problems(row: dict, e: dict) -> list[str]:
    pr = e.get("prompts")
    if not isinstance(pr, list) or not pr or not all(
            isinstance(x, dict) and all(ns.text(x.get(k)) for k in ("prompt_sha256", "ctl_content_sha256", "cand_content_sha256"))
            and ns.nonneg_int(x.get("ctl_tokens")) and ns.nonneg_int(x.get("cand_tokens")) for x in pr):
        return ["extra.prompts must record per-prompt content digests and token counts"]
    p: list[str] = []
    ident = sum(1 for x in pr if x["ctl_content_sha256"] == x["cand_content_sha256"] and x["ctl_tokens"] == x["cand_tokens"])
    if e.get("n_identical") != ident or e.get("n_total") != len(pr):
        p.append("extra.n_identical / n_total must re-derive from extra.prompts")
    if not _close(ident / len(pr), row["value"]):
        p.append("value must equal n_identical / n_total")
    if row.get("reps") != len(pr):
        p.append("reps must equal the prompt count")
    cb, kb = _build_from_bin(e.get("ctl_bin")), _build_from_bin(e.get("cand_bin"))
    if not cb or e.get("champion_sha") != cb[1]:
        p.append("extra.champion_sha must re-derive from extra.ctl_bin")
    if not kb or e.get("build_sha") != kb[1]:
        p.append("extra.build_sha must re-derive from extra.cand_bin")
    if not ns.SHA256.match(str(e.get("ctl_results_sha256", ""))):
        p.append("extra.ctl_results_sha256 must bind the control arm's file")
    return p


def _tbo_problems(row: dict, e: dict) -> list[str]:
    p: list[str] = []
    if e.get("arm") not in TBO_ARMS or not ns.text(e.get("op")):
        return ["extra.arm / extra.op must name the test-backend-ops cell"]
    sm = TBO_SUMMARY.fullmatch(e.get("summary_line", "")) if isinstance(e.get("summary_line"), str) else None
    bm = TBO_BACKEND.fullmatch(e.get("backend_line", "")) if isinstance(e.get("backend_line"), str) else None
    if not sm or not bm:
        return ["extra.summary_line / backend_line must be the log's own lines"]
    passed, total = int(sm.group(1)), int(sm.group(2))
    if e.get("passed") != passed or e.get("total") != total or total <= 0:
        p.append("extra.passed / total must re-derive from extra.summary_line")
    if not _close(passed / total, row["value"]):
        p.append("value must equal passed / total")
    want_backend = TBO_ARMS[e["arm"]][0]
    if bm.group(1) != want_backend or e.get("backend") != want_backend:
        p.append("backend must match the arm")
    if (bm.group(2) == "OK") != (passed == total and e.get("n_fail_lines") == 0):
        p.append("backend verdict word must agree with the counts and fail lines")
    if row.get("reps") != total:
        p.append("reps must equal the test count")
    if row.get("category") != ("BASELINE" if TBO_ARMS[e["arm"]][1] == "ctl" else "CANDIDATE"):
        p.append("category must be BASELINE for the control arm and CANDIDATE otherwise")
    return p


_FAMILY = {M_PP: _speed_problems, M_TG: _speed_problems, M_RPP: _speed_problems, M_RTG: _speed_problems,
           M_COH: _coh_problems, M_RES: _res_problems, M_IDENT: _ident_problems, M_TBO: _tbo_problems}


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: an observation, no codified protocol")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    if not ns.text(e.get("ident")):
        p.append("extra.ident must name the row member")
    if not ns.text(e.get("build_sha")) and row["metric"] != M_TBO:
        p.append("extra.build_sha must name the build")
    if not p:
        p += _FAMILY[row["metric"]](row, e)
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "metric": row["metric"], "ident": e["ident"],
                                     "results": row["results_sha256"]}, "nbfold")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


# ----------------------------------------------------------------------------------------------- writer
def _row(run_id, producer, when, path, digest, *, metric, value, unit, direction, category, claim, reps, basis, extra):
    row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when, "date": when,
           "metric": metric, "value": value, "unit": unit, "metric_direction": direction, "category": category,
           "claim": claim, "protocol_id": "", "reps": reps, "reps_basis": basis, "results_path": str(path),
           "results_sha256": digest, "extra": extra}
    row["measurement_id"] = "nbfold_" + ns.content_hash({"run_id": run_id, "metric": metric, "ident": extra["ident"],
                                                        "results": digest})[:24]
    ns.seal(row)
    bad = row_problems(row)
    if bad:
        raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
    return row


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, artifact_dir: str | Path,
                              emitted_at: str | None = None) -> Path:
    adir = Path(artifact_dir).resolve()
    src = _Src(adir, _verified_sums(adir))
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    common = dict(run_id=run_id, producer=producer, when=when)

    # speed: llama-bench + load
    bench, load, err = src.get("bench_gpu.md"), src.get("bench_load.txt"), src.get("bench_gpu.err")
    if bench and load and err:
        path, digest, text = bench
        build_line = next((ln.strip() for ln in text.splitlines() if ln.startswith("build:")), "")
        load_line = next((ln.strip() for ln in load[2].splitlines() if "load average" in ln), "")
        cmd = re.search(r"running: .*?(\S*llama-bench\b.*)$", err[2], re.M)
        bm = re.search(r"build: ([0-9a-f]{7,40}) \(", build_line)
        if build_line and load_line and cmd and bm:
            for ln in text.splitlines():
                f = _parse_bench_line(ln)
                if not f:
                    continue
                metric, unit = (M_PP, "t/s (llama-bench avg_ts)") if f["test"] == "pp512" else (M_TG, "t/s (llama-bench avg_ts)")
                rows.append(_row(
                    run_id, producer, when, path, digest, metric=metric, value=f["mean"], unit=unit,
                    direction="higher_better", category="CANDIDATE", reps=int(re.search(r" -r (\d+) ", cmd.group(1)).group(1)),
                    basis="llama-bench repetitions (-r)",
                    claim=(f"Nemotron 3.5 Bolt IQ2_XXS 74B-A9B on MI210, {f['test']}: {f['mean']:.2f} t/s (sd {f['sd']:.2f}), build "
                           f"{bm.group(1)}; {CAVEAT}"),
                    extra={"ident": f"llamabench:{f['test']}", "kind": "speed", "caveat": CAVEAT, "device": "MI210",
                           "source_line": ln.strip(), "sd": f["sd"], "threads": f["threads"], "ngl": f["ngl"], "fa": f["fa"],
                           "build_line": build_line, "build_sha": bm.group(1), "load_line": load_line,
                           "load1": _parse_load_line(load_line), "bench_cmd": cmd.group(1).strip(),
                           "load_file": "bench_load.txt", "load_file_sha256": load[1],
                           "model_file": Path(re.search(r"-m (\S+)", cmd.group(1)).group(1)).name
                           if re.search(r"-m (\S+)", cmd.group(1)) else "", "backend": "hip"}))

    # gpu_coh.json: coherence + residency + recipe timings
    coh = src.get("gpu_coh.json")
    if coh:
        path, digest, text = coh
        try:
            d = json.loads(text)
            argv = d["argv"]
            outs, vs = d["outputs"], d["vram_samples"]
        except (ValueError, KeyError, TypeError):
            d = None
            src.skipped.append("gpu_coh.json: not the recorded shape")
        if d:
            binp = argv[0] if argv else ""
            bsha = (_build_from_bin(binp) or ("", ""))[1]
            model = Path(argv[argv.index("-m") + 1]).name if "-m" in argv else ""
            base = {"bin": binp, "build_sha": bsha, "model_file": model, "backend": "hip", "device": "MI210"}
            for think, label in ((True, "on"), (False, "off")):
                grp = [o for o in outs if o.get("think") is think]
                if not grp or bsha == "":
                    continue
                prompts = [{"prompt_sha256": _sha(o["prompt"]), "finish": o["finish"], "n": o["n"], "rep_loop": o["rep_loop"],
                            "content_len": len(o["content"].strip()), "reasoning_len": o["reasoning_len"]} for o in grp]
                clean = sum(1 for x in prompts if not x["rep_loop"] and x["content_len"] > 0)
                rows.append(_row(
                    run_id, producer, when, path, digest, metric=M_COH, value=clean / len(prompts),
                    unit="fraction of prompts with non-empty content and no repetition loop", direction="higher_better",
                    category="CANDIDATE", reps=len(prompts), basis="prompts",
                    claim=(f"Nemotron 3.5 Bolt on MI210 build {bsha}, reasoning {label}: {clean}/{len(prompts)} prompts coherent "
                           f"(non-empty content, no repetition loop); a smoke-level check, not a quality eval"),
                    extra={"ident": f"coherence:{label}", "kind": "coherence", "reasoning": label, "prompts": prompts,
                           "n_clean": clean, "n_total": len(prompts),
                           "n_finish_length": sum(1 for x in prompts if x["finish"] == "length"), **base}))
            if vs and bsha:
                samples = [{"vram0": int((s.get("vram_used") or [0])[0]), "kfd": bool(s.get("srv_pid_in_kfd"))} for s in vs]
                res = sum(1 for x in samples if x["vram0"] >= GIB and x["kfd"])
                rows.append(_row(
                    run_id, producer, when, path, digest, metric=M_RES, value=res / len(samples),
                    unit="fraction of during-run samples with >=1 GiB VRAM on device 0 and the server pid in KFD",
                    direction="higher_better", category="CANDIDATE", reps=len(samples), basis="samples",
                    claim=(f"Nemotron 3.5 Bolt GPU residency, build {bsha}: {res}/{len(samples)} samples resident "
                           f"(max {max(x['vram0'] for x in samples)} B); the pre-load sample is counted as non-resident"),
                    extra={"ident": "residency", "kind": "residency", "samples": samples, "n_samples": len(samples),
                           "n_resident": res, "vram_max_bytes": max(x["vram0"] for x in samples),
                           "server_dead_at_end": bool(d.get("server_dead")), **base}))
            rt = d.get("recipe_timings") or []
            if len(rt) == 3 and bsha:
                for m, key, nm in ((M_RPP, "prompt_per_second", "pp"), (M_RTG, "predicted_per_second", "tg")):
                    vals = [float(r[key]) for r in rt]
                    rows.append(_row(
                        run_id, producer, when, path, digest, metric=m, value=sum(vals) / 3, unit="t/s (server timings)",
                        direction="higher_better", category="CANDIDATE", reps=3, basis="recipe requests",
                        claim=(f"Nemotron 3.5 Bolt server recipe {nm}: mean {sum(vals) / 3:.1f} t/s over 3 requests "
                               f"(prompt_n {rt[0].get('prompt_n')}, predicted_n {rt[0].get('predicted_n')}); {CAVEAT}"),
                        extra={"ident": f"recipe:{nm}", "kind": "speed", "caveat": CAVEAT, "values": vals, **base}))

    # greedy identity
    ctl, cand = src.get("greedy_ctl.json"), src.get("greedy_cand.json")
    if ctl and cand:
        try:
            dc, dk = json.loads(ctl[2]), json.loads(cand[2])
            oc, ok = dc["outputs"], dk["outputs"]
            if [o["prompt"] for o in oc] != [o["prompt"] for o in ok] or not oc:
                raise ValueError("prompt lists differ")
            margv = dk["argv"]
            cb, kb = _build_from_bin(dc["bin"]), _build_from_bin(dk["bin"])
            if not cb or not kb:
                raise ValueError("bin paths carry no build sha")
            prompts = [{"prompt_sha256": _sha(a["prompt"]), "ctl_content_sha256": _sha(a["content"]),
                        "cand_content_sha256": _sha(b["content"]), "ctl_tokens": a["tokens_predicted"],
                        "cand_tokens": b["tokens_predicted"], "ctl_draft_n": a.get("draft_n"),
                        "cand_draft_n": b.get("draft_n"), "ctl_draft_accepted": a.get("draft_n_accepted"),
                        "cand_draft_accepted": b.get("draft_n_accepted")} for a, b in zip(oc, ok)]
        except (ValueError, KeyError, TypeError) as exc:
            src.skipped.append(f"greedy identity: {exc}")
        else:
            nid = sum(1 for x in prompts if x["ctl_content_sha256"] == x["cand_content_sha256"] and x["ctl_tokens"] == x["cand_tokens"])
            rows.append(_row(
                run_id, producer, when, cand[0], cand[1], metric=M_IDENT, value=nid / len(prompts),
                unit="fraction of greedy prompts whose content and token count are byte-identical to the champion build",
                direction="higher_better", category="CANDIDATE", reps=len(prompts), basis="prompts",
                claim=(f"Qwen3.6-35B-A3B-MTP-Q8_0 greedy (CPU, draft-mtp) on build {kb[1]} vs champion {cb[1]}: "
                       f"{nid}/{len(prompts)} prompts byte-identical (256 tokens each)"),
                extra={"ident": "greedy-identity:qwen36", "kind": "identity", "prompts": prompts, "n_identical": nid,
                       "n_total": len(prompts), "ctl_bin": dc["bin"], "cand_bin": dk["bin"], "champion_sha": cb[1],
                       "build_sha": kb[1], "ctl_results_path": str(ctl[0]), "ctl_results_sha256": ctl[1],
                       "model_file": Path(margv[margv.index("-m") + 1]).name if "-m" in margv else "",
                       "backend": "cpu"}))

    # test-backend-ops
    for log in sorted(adir.glob("tbo_*_*.log")):
        m = re.fullmatch(r"tbo_(cpu|gpu_cand|gpu_ctl)_([A-Z0-9_]+)\.log", log.name)
        got = src.get(log.name) if m else None
        parsed = _parse_tbo(got[2]) if got else None
        if not got or not parsed:
            if got:
                src.skipped.append(f"{log.name}: no summary / backend line")
            continue
        arm, op = m.group(1), m.group(2)
        if parsed["backend"] != TBO_ARMS[arm][0]:
            src.skipped.append(f"{log.name}: backend {parsed['backend']} != arm {arm}")
            continue
        rows.append(_row(
            run_id, producer, when, got[0], got[1], metric=M_TBO, value=parsed["passed"] / parsed["total"],
            unit="fraction of test-backend-ops tests passed", direction="higher_better",
            category="BASELINE" if TBO_ARMS[arm][1] == "ctl" else "CANDIDATE", reps=parsed["total"], basis="op tests",
            claim=(f"test-backend-ops {op} on {parsed['backend']} ({'champion dd3d9721c control' if arm == 'gpu_ctl' else 'candidate 59c1b915f'} build): "
                   f"{parsed['passed']}/{parsed['total']} passed"),
            extra={"ident": f"tbo:{arm}:{op}", "kind": "optest", "arm": arm, "op": op, **parsed,
                   "build_sha": "dd3d9721c" if arm == "gpu_ctl" else "59c1b915f"}))
    if not rows:
        raise CaptureError("no verifiable source in the artifact dir: " + "; ".join(src.skipped or ["empty"]))
    if src.skipped:
        print("nemotron_bolt_fold: skipped " + "; ".join(src.skipped), file=sys.stderr)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


# ----------------------------------------------------------------------------------------------- projection
def _applicability(row: dict) -> dict:
    e = row["extra"]
    app: dict[str, Any] = {"scope_basis": "native", "run_id": row["run_id"]}
    if row["metric"] == M_TBO:
        app.update({"backend": "cpu" if e["arm"] == "cpu" else "hip", "op": e["op"],
                    "device": "cpu" if e["arm"] == "cpu" else "MI210"})
    else:
        if e.get("backend"):
            app["backend"] = e["backend"]
        if e.get("device"):
            app["device"] = e["device"]
        elif e.get("backend") == "cpu":
            app["device"] = "cpu"
        if ns.text(e.get("model_file")):
            app["model_file"] = e["model_file"]
    if re.fullmatch(r"[0-9a-f]{7,64}", str(e.get("build_sha", ""))):
        app["build_sha"] = e["build_sha"]
    return app


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("Nemotron Bolt fold native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("Nemotron Bolt fold row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"nemotron-bolt-fold:{row['run_id']}:{e['ident']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    obs: dict[str, Any] = {}
    if row["metric"] not in SPEED_METRICS:
        # correctness evidence: the counts in the row, verbatim; no floor, no decisive flag (those need a protocol)
        obs["outcome_native"] = {M_COH: f"{e.get('n_clean')}/{e.get('n_total')} coherent",
                                 M_RES: f"{e.get('n_resident')}/{e.get('n_samples')} resident",
                                 M_IDENT: f"{e.get('n_identical')}/{e.get('n_total')} identical",
                                 M_TBO: f"{e.get('passed')}/{e.get('total')} passed"}[row["metric"]]
    return dataclasses.replace(tup, observation=obs, applicability=_applicability(row))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the Nemotron Bolt fold belief sidecar from the research artifact dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--artifact-dir", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--run-id", default="nemotron-bolt-champion-20261021")
    w.add_argument("--producer", default="nemotron-bolt-champion-20261021/fold-record")
    a = ap.parse_args(argv)
    try:
        path = write_belief_measurements(a.out_dir, run_id=a.run_id, producer=a.producer, artifact_dir=a.artifact_dir)
    except CaptureError as exc:
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
