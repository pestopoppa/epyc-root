#!/usr/bin/env python3
"""VB-NEW13-WIRE: prospective receipt writer for ``llama-weight-handoff`` (stdlib only, no model run here).

``python3 scripts/vidya/qwen4exp_quality_capture.py --mode weight-handoff ...`` dispatches here. The
wrapper launches exactly the already-approved harness argv as ONE child, captures its process,
environment, loaded shared objects (reusing ``monitor_maps`` / ``loaded_objects_from_seen`` /
``residency_refusals`` from ``qwen4exp_quality_capture``), per-PID KFD residency sampled DURING the
child, the identity of every input (P/D(/R) weight shards, reference pin, passage binary and
manifest, predeclared rule, harness binary) and the sealed ``kld.jsonl`` the harness writes. It makes no
quality verdict and applies no threshold. ``adapters/weight_handoff.py`` is the strict reader: it
re-derives per-arm KLD, R with its paired-bootstrap CI and the Gate 0 gap from ``kld.jsonl`` and projects
ClaimTuples; ``claim_tuple.grade()`` decides.

Resumable runs: the harness resumes per passage across grants (rc 10 = stopped). Call this wrapper once
per harness invocation with a distinct ``--run-id``; an invocation that stops cleanly (child exit code in
``--partial-exit-codes``, default 10,124) writes a ``partial`` receipt, and the next invocation passes it
as ``--prior-receipt``. The reader accepts only a FINAL ``captured`` receipt whose ``kld.jsonl`` holds every
passage, and walks the chain (each earlier kld.jsonl must be a byte prefix of the final one, same weights,
reference, passages and binary, residency proven in every link). A NEW-13 hand-written
``epyc.new13.receipt.v0`` is refused (unsupported schema) and is never backfilled.

Pre-run inputs the caller authors BEFORE launching (the reader refuses a declaration issued after start):
``--metric-spec`` is a JSON file ``{"schema": "epyc.vidya.weight_handoff_metric_declaration.v1",
"run_id": ..., "author": ..., "issued_at_utc": ..., "protocol_id": ..., "metrics": {label: {"unit",
"metric_direction", "category", "metric"}}}`` with exactly the labels ``KLD[A] KLD[B] KLD[C] KLD[D] R
G0_gap`` (direction/category are the author's declaration; nothing is inferred).

Exact line a C-L3 (or any NEW-13-class) job script calls -- wrap the capture in the job's own env/region
wrappers (they exec in place), and give it the same argv the job already runs after ``--``::

    "${XENV[@]}" timeout --foreground -k 30 $(( $(left) - 30 )) "${RUN[@]}" /usr/bin/python3 -I \\
      /workspace/scripts/vidya/qwen4exp_quality_capture.py --mode weight-handoff \\
      --run-id "$RID" --source-revision "$HARNESS_REV" --protocol-id "$PROTOCOL_ID" \\
      --metric-spec $JOB/wh_metric_spec.json --substrate cpu \\
      --shard-p $UD/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf --shard-p ...-00002-of-00003.gguf --shard-p ...-00003-of-00003.gguf \\
      --shard-d $G/...-00001-of-00002.gguf --shard-d $G/...-00002-of-00002.gguf \\
      --reference-json $JOB/REFERENCE.json --passages-manifest $JOB/passages/MANIFEST.json \\
      --predeclared $PRED --expect-binary-sha256 "$(cut -d' ' -f1 $JOB/TOOL.sha256)" \\
      ${PRIOR:+--prior-receipt "$PRIOR"} --out-dir $OUT/wh --env GGML_IQK=1 --env GGML_FUSED_DECODE_OFF=1 \\
      --env LD_LIBRARY_PATH=$BIN -- $TOOL --model-p $P1 --model-d $D1 "${REFARGS[@]}" \\
      --passages $PASSAGES --out $OUT/kld.jsonl --compat-out $OUT/compat.json --selftest 4 --tf-batch 1 \\
      -t $T_DEC -tb $T_BATCH --stop-file "$FILLER_STOPFILE" --deadline $(( FILLER_DEADLINE - 120 ))

Exit 0 = captured and complete, 4 = clean partial (resume next grant, pass this receipt as --prior-receipt),
3 = refused (reasons inside the receipt). Hashing every shard before the child is a one-off read of the
weights; after the child shards are re-checked by size/inode/mtime/ctime only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qwen4exp_quality_capture as qc  # noqa: E402
from adapters import weight_handoff as wh  # noqa: E402

SCHEMA = wh.SCHEMA


def _opt(argv: list[str], *names: str) -> str:
    found = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x in names]
    if len(found) != 1:
        raise ValueError(f"exact producer argv must contain exactly one {names[0]}")
    return found[0]


def _same(a: str | Path, b: str | Path) -> bool:
    return Path(a).resolve() == Path(b).resolve()


def main(argv_in: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--source-revision", required=True, help="harness branch@sha asserted by the invoking job; never substitutes for the binary digest")
    ap.add_argument("--protocol-id", default="unknown", help="human-ratified protocol id actually used, else literal unknown")
    ap.add_argument("--metric-spec", type=Path, required=True)
    ap.add_argument("--substrate", choices=qc.SUBSTRATES, required=True)
    ap.add_argument("--shard-p", type=Path, action="append", required=True, help="every shard of the prefill weight set P (first = --model-p)")
    ap.add_argument("--shard-d", type=Path, action="append", required=True, help="every shard of the decode weight set D (first = --model-d)")
    ap.add_argument("--shard-r", type=Path, action="append", default=[], help="every shard of reference R (only when REFERENCE.json selects R)")
    ap.add_argument("--reference-json", type=Path, required=True)
    ap.add_argument("--passages-manifest", type=Path, required=True)
    ap.add_argument("--predeclared", type=Path, help="pinned decision-rule file: hashed and cited, never evaluated")
    ap.add_argument("--predeclared-sha256")
    ap.add_argument("--expect-binary-sha256", help="pinned harness binary digest (job TOOL.sha256)")
    ap.add_argument("--prior-receipt", type=Path, help="receipt of the earlier invocation whose kld.jsonl this run resumes")
    ap.add_argument("--partial-exit-codes", default="10,124", help="child exit codes that mean a clean stop (default 10,124)")
    ap.add_argument("--bootstrap-seed", type=int, default=20261022)
    ap.add_argument("--bootstrap-resamples", type=int, default=10000)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--env", action="append", default=[], metavar="NAME=VALUE")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv_in)
    cmd = list(a.command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("exact producer command is required after --")
    try:
        qc.validate_identity_token(a.run_id)
        partial_codes = {int(x) for x in a.partial_exit_codes.split(",") if x.strip()}
        env = qc.parse_env(a.env)
        argv = list(cmd)
        refchoice = _opt(argv, "--ref")
        kld_path = Path(_opt(argv, "--out"))
        passages_path = Path(_opt(argv, "--passages"))
        if refchoice not in {"P", "R"} or not _opt(argv, "--selftest").isdigit() or int(_opt(argv, "--selftest")) < 1:
            raise ValueError("argv needs --ref P|R and --selftest >= 1")
        if not _same(_opt(argv, "--model-p"), a.shard_p[0]) or not _same(_opt(argv, "--model-d"), a.shard_d[0]):
            raise ValueError("--model-p/--model-d must name the first --shard-p/--shard-d")
        if (refchoice == "R") != bool(a.shard_r) or (refchoice == "R" and not _same(_opt(argv, "--model-r"), a.shard_r[0])):
            raise ValueError("--shard-r and argv --model-r are required exactly when the reference is R")
        binary = Path(argv[0]).resolve(strict=True)
        argv[0] = str(binary)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    root = Path(a.out_dir).resolve()
    log_path = root / f"{a.run_id}.weight-handoff.native.log"
    receipt_path = root / f"{a.run_id}.weight-handoff.json"
    qc.refuse_existing_outputs(log_path, receipt_path)

    # --- pre-run: declaration + identities (nothing below touches the child)
    spec_before = qc.file_identity(a.metric_spec)
    spec = json.loads(a.metric_spec.read_text(encoding="utf-8"), object_pairs_hook=qc.unique_json_pairs)
    if (spec.get("schema") != wh.DECL_SCHEMA or spec.get("run_id") != a.run_id or spec.get("protocol_id") != a.protocol_id
            or set(spec.get("metrics", {})) != set(wh.LABELS) or not isinstance(spec.get("author"), str) or not spec["author"].strip()):
        raise ValueError("metric declaration is not this run's pre-run source-authored declaration for the weight-handoff label set")
    issued = datetime.fromisoformat(str(spec["issued_at_utc"]).replace("Z", "+00:00"))
    if issued.tzinfo is None or issued > datetime.now(timezone.utc):
        raise ValueError("declaration issued_at_utc must be timezone-aware and not in the future")
    ref_before = qc.file_identity(a.reference_json)
    ref_blob = json.loads(a.reference_json.read_text(encoding="utf-8"))
    if ref_blob.get("ref") != refchoice:
        raise ValueError("argv --ref differs from the pinned REFERENCE.json")
    man_before = qc.file_identity(a.passages_manifest)
    manifest = json.loads(a.passages_manifest.read_text(encoding="utf-8"))
    pass_before = qc.file_identity(passages_path)
    if manifest.get("binary_sha256") != pass_before["sha256"] or not _same(manifest.get("binary", passages_path), passages_path):
        raise ValueError("passage binary does not match the manifest's binary_sha256/path")
    n_total = manifest["n"]
    binary_before = qc.file_identity(binary)
    if a.expect_binary_sha256 and a.expect_binary_sha256 != binary_before["sha256"]:
        raise ValueError("harness binary differs from the pinned --expect-binary-sha256")
    pred_before = qc.file_identity(a.predeclared) if a.predeclared else None
    if a.predeclared_sha256 and (pred_before is None or pred_before["sha256"] != a.predeclared_sha256):
        raise ValueError("predeclared rule file differs from --predeclared-sha256")
    shards = {side: [qc.file_identity(p) for p in files]
              for side, files in (("P", a.shard_p), ("D", a.shard_d), ("R", a.shard_r)) if files}
    prior_identity = qc.file_identity(a.prior_receipt) if a.prior_receipt else None
    kld_before = qc.file_identity(kld_path) if kld_path.exists() else None
    complete_before = len(wh.load_kld_records(kld_path.read_bytes())) if kld_before else 0
    if kld_before and prior_identity is None and complete_before:
        raise ValueError("kld.jsonl already holds passages but no --prior-receipt warrants them")
    if env.get("GGML_IQK") not in {"0", "1"}:
        raise ValueError("effective GGML_IQK must be set to 0 or 1 via --env")

    kfd_state = qc.new_kfd_state()
    started = qc.utc_now()
    start_ns = time.time_ns()
    seen: dict[tuple, dict[str, Any]] = {}
    stop = threading.Event()
    with qc.open_native_log(log_path) as log:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, shell=False)
        mon = threading.Thread(target=qc.monitor_maps, args=(proc, seen, stop), daemon=True)
        kfd = threading.Thread(target=qc.monitor_kfd, args=(proc, kfd_state, stop), daemon=True)
        mon.start(); kfd.start()
        exit_code = proc.wait()
        end_ns = time.time_ns()
        ended = datetime.fromtimestamp(end_ns / 1e9, timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        stop.set(); mon.join(); kfd.join()
        log.flush(); os.fsync(log.fileno())

    # --- post-run seal
    refusal: list[str] = []
    loaded = qc.loaded_objects_from_seen(seen)
    log_sha = qc.sha256_file(log_path)
    binary_after = qc.file_identity(binary)
    if binary_before != binary_after:
        refusal.append("harness binary changed during measured process")
    for ident, label in [(spec_before, "metric declaration"), (ref_before, "reference pin"), (man_before, "passage manifest"),
                         (pass_before, "passage binary"), (pred_before, "predeclared rule"), (prior_identity, "prior receipt")]:
        if ident is not None and qc.file_identity(Path(ident["path"])) != ident:
            refusal.append(f"{label} changed during measured process")
    for side, idents in shards.items():
        if not all(wh.stat_matches(x) for x in idents):
            refusal.append(f"weight shard set {side} changed during measured process")
    try:
        kld_after = qc.file_identity(kld_path)
        kraw = kld_path.read_bytes()
        if hashlib_sha(kraw) != kld_after["sha256"]:
            raise ValueError("kld.jsonl changed while it was read")
        complete_after = len({i for i in wh.load_kld_records(kraw) if 0 <= i < n_total})
    except (OSError, ValueError) as exc:
        refusal.append(f"kld.jsonl not durably written: {exc}")
        kld_after, kraw, complete_after = None, b"", 0
    refusal.extend(qc.residency_refusals(a.substrate, loaded, kfd_state))
    if not loaded:
        refusal.append("no loaded shared-object mappings observed during process")
    if any(r.get("identity_state") != "matched" for r in loaded):
        refusal.append("loaded shared-object identity was unknown or did not match maps inode/device")
    if not any(r["compiled_knob_evidence"].get("state") == "present" and r["compiled_knob_evidence"].get("found_exact") is True for r in loaded):
        refusal.append("GGML_IQK compiled-string evidence was not found in a loaded shared object")
    clean_exit = exit_code == 0
    if not clean_exit and exit_code not in partial_codes:
        refusal.append(f"producer_exit_code={exit_code}")
    complete = clean_exit and complete_after == n_total
    if clean_exit and not complete:
        refusal.append(f"child exited 0 but only {complete_after} of {n_total} passages are complete")
    metrics: list[dict[str, Any]] = []
    bootstrap = {"seed": a.bootstrap_seed, "resamples": a.bootstrap_resamples,
                 "method": "paired passage bootstrap, python random.Random(seed).randrange, linear percentiles", "percentiles": [2.5, 97.5]}
    if complete and not refusal:
        try:
            d = wh.derive_metrics(kraw, n_total, ref=refchoice, n_prompt=manifest["n_prompt"], n_cont=manifest["n_cont"],
                                  seed=a.bootstrap_seed, resamples=a.bootstrap_resamples)
            for lab in wh.LABELS:
                m = spec["metrics"][lab]
                if set(m) != {"unit", "metric_direction", "category", "metric"}:
                    raise ValueError(f"declaration for {lab} is incomplete")
                metrics.append({"native_label": lab, "value": d["values"][lab], "ci95": d["ci95"].get(lab), **m})
        except ValueError as exc:
            refusal.append(str(exc))
    status = "refused" if refusal else ("captured" if complete else wh.PARTIAL_STATUS)
    record: dict[str, Any] = {
        "schema": SCHEMA, "schema_version": 1, "run_id": a.run_id, "instrument": "llama-weight-handoff",
        "protocol_id": spec["protocol_id"], "producer_source_revision": a.source_revision,
        "started_at_utc": started, "ended_at_utc": ended, "measurement_window_ns": {"start": start_ns, "end": end_ns},
        "argv": argv, "argv_display": shlex.join(argv),
        "effective_environment": {k: v for k, v in sorted(env.items()) if k.startswith(qc.ENV_PREFIXES) or k == "LD_LIBRARY_PATH"},
        "producer_binary": {"before": binary_before, "after": binary_after, "stable_during_capture": binary_before == binary_after},
        "expected_binary_sha256": a.expect_binary_sha256,
        "loaded_shared_objects": loaded,
        "runtime_knobs": {"GGML_IQK": {"value": {"0": "disabled", "1": "enabled"}[env["GGML_IQK"]], "raw_value": env["GGML_IQK"],
                                         "capture_source": "effective child-process environment"}},
        "substrate": a.substrate, "kfd_residency": kfd_state,
        "weights": {s: ({"shards": shards[s], "shards_after": shards[s]} if s in shards else None) for s in ("P", "D", "R")},
        "reference": {"json": ref_before, "choice": refchoice},
        "passages": {"manifest": man_before, "binary": pass_before, "n": n_total, "n_prompt": manifest["n_prompt"], "n_cont": manifest["n_cont"]},
        "predeclared": pred_before, "prior_receipt": prior_identity,
        "kld_jsonl": {"before": kld_before, "after": kld_after, "complete_before": complete_before, "complete_after": complete_after},
        "bootstrap": bootstrap,
        "metric_declaration": {"before": spec_before, "after": spec_before, "author": spec["author"],
                               "issued_at_utc": spec["issued_at_utc"], "metrics": spec["metrics"]},
        "metrics": metrics, "native_log": {"path": str(log_path), "sha256": log_sha}, "exit_code": exit_code,
        "scope": {"verdict": "none: the predeclared rule is hashed and cited, never evaluated by the capture or the reader",
                  "weights": "large shards are identity-checked by size/inode/mtime/ctime after the child; sha256 is the pre-run hash",
                  "ci": "stdlib paired bootstrap; not numpy's generator, do not compare digit-for-digit with a numpy re-analysis"},
        "capture_status": status, "refusal_reasons": refusal,
    }
    qc.atomic_json(receipt_path, record)
    print(receipt_path)
    return 0 if status == "captured" else (4 if status == wh.PARTIAL_STATUS else 3)


def hashlib_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"weight-handoff capture refused: {exc}", file=sys.stderr)
        raise SystemExit(3)
