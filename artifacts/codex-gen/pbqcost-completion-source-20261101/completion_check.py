#!/usr/bin/env python3
"""Fail-closed qualification and attempt-bound full-run completion predicate."""
import hashlib
import json
import os
from pathlib import Path
from source_seal import verify_source_seal
from verdict_inputs import hash_verdict_inputs, VERDICT_INPUTS

D = Path(__file__).resolve().parent
CONFIRM_TERMINAL = {"CONFIRMED", "REFIT_FROM_UNCONTENDED", "FAIL_MAPE"}
Q_TERMINAL = {"PASS", "FAIL"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def producer_labels_consistent(v: object) -> bool:
    if not isinstance(v, dict):
        return False
    confirm = v.get("confirm")
    q_axis = v.get("q_axis")
    proof = v.get("proof")
    if not isinstance(confirm, dict) or not isinstance(q_axis, dict) or not isinstance(proof, dict):
        return False
    if proof.get("all_ok") is not True:
        return False
    per_confirm = confirm.get("1"), confirm.get("4")
    if not all(isinstance(x, dict) and x.get("verdict") in CONFIRM_TERMINAL | {"INCOMPLETE"} for x in per_confirm):
        return False
    c_labels = [x["verdict"] for x in per_confirm]
    expected_confirm = ("INCOMPLETE" if "INCOMPLETE" in c_labels else
                        "FAIL_MAPE" if "FAIL_MAPE" in c_labels else
                        "CONFIRMED" if all(x == "CONFIRMED" for x in c_labels) else
                        "REFIT_FROM_UNCONTENDED")
    if confirm.get("overall") != expected_confirm or v.get("confirm_overall") != expected_confirm:
        return False
    per_n = q_axis.get("per_n")
    if not isinstance(per_n, dict) or set(per_n) != {"1", "4"}:
        return False
    q_labels = [per_n[n].get("verdict") if isinstance(per_n[n], dict) else None for n in ("1", "4")]
    if not all(x in {"PASS", "FAIL", "INCOMPLETE"} for x in q_labels):
        return False
    expected_q = "PASS" if all(x == "PASS" for x in q_labels) else "INCOMPLETE" if "INCOMPLETE" in q_labels else "FAIL"
    if q_axis.get("overall") != expected_q or v.get("q_overall") != expected_q:
        return False
    grade_run = v.get("grade_run_level")
    per_phase = v.get("sibling_per_phase")
    if grade_run not in {"UNCONTENDED", "INDICATIVE"} or not isinstance(per_phase, dict):
        return False
    expected_grade = "UNCONTENDED" if grade_run == "UNCONTENDED" and per_phase.get("all_uncontended") is True else "INDICATIVE"
    return (v.get("grade") == expected_grade and
            v.get("label") == f"PB-QCOST-1 confirm {expected_confirm}; q axis {expected_q}; grade {expected_grade}")


def complete_verdict(v: object, run: object, attempt: object, manifest: object, *,
                     verdict_sha256: str | None, result_sha256: str | None, input_sha256: str | None,
                     source_code_manifest_sha256: str | None,
                     candidate_manifest_sha256: str | None,
                     predeclaration_sha256: str | None,
                     amendment_sha256: str | None,
                     expected_input_path: str,
                     expected_verdict_path: str,
                     verdict_inputs_sha256: dict | None) -> bool:
    """A terminal diagnostic is complete only when producer/consumer artifacts bind to one attempt and source set."""
    if not all(isinstance(x, dict) for x in (v, run, attempt, manifest)):
        return False
    row_id = manifest.get("id")
    run_id = attempt.get("run_id")
    if (not isinstance(row_id, str) or not isinstance(run_id, str) or
            not run_id.startswith(row_id + "-") or
            attempt.get("row_id") != row_id or
            attempt.get("attempt_id") != run_id or
            attempt.get("state") != "COMPLETE" or
            attempt.get("input_sha256") != input_sha256 or
            attempt.get("verdict_sha256") != verdict_sha256 or
            attempt.get("result_sha256") != result_sha256 or
            attempt.get("source_code_manifest_sha256") != source_code_manifest_sha256 or
            attempt.get("candidate_manifest_sha256") != candidate_manifest_sha256 or
            attempt.get("input_path") != expected_input_path or
            attempt.get("verdict_path") != expected_verdict_path or
            manifest.get("result_path") != expected_verdict_path):
        return False
    finalization = attempt.get("finalization")
    if (not isinstance(finalization, dict) or
            finalization.get("verdict_inputs_sha256") != verdict_inputs_sha256 or
            not isinstance(verdict_inputs_sha256, dict) or
            set(verdict_inputs_sha256) != set(VERDICT_INPUTS) or
            finalization.get("input_sha256") != input_sha256 or
            verdict_inputs_sha256.get("run/pb_qcost_1.jsonl") != input_sha256):
        return False
    for obj in (v, run):
        if (obj.get("verdict_inputs_sha256") != verdict_inputs_sha256 or
                obj.get("row_id") != row_id or obj.get("run_id") != run_id or
                obj.get("attempt_id") != run_id or
                obj.get("source_code_manifest_sha256") != source_code_manifest_sha256 or
                obj.get("candidate_manifest_sha256") != candidate_manifest_sha256 or
                obj.get("input_sha256") != input_sha256 or
                obj.get("input_path") != attempt.get("input_path") or
                obj.get("predeclaration_sha256") != predeclaration_sha256 or
                obj.get("amendment_sha256") != amendment_sha256):
            return False
    if (run.get("verdict_sha256") != verdict_sha256 or
            run.get("verdict_path") != attempt.get("verdict_path") or
            v.get("input_path") != attempt.get("input_path") or
            v.get("input_sha256") != input_sha256 or
            v.get("phases_done") != [256, 512, 1024]):
        return False
    if (not isinstance(run, dict) or run.get("status") != "COMPLETE" or
            run.get("partial") is not False or run.get("exit_code") != 0 or
            run.get("cleanup_verified") is not True or run.get("smoke") is not False or
            run.get("protocol_requests") != 66 or
            run.get("coefficient_grade") != "mechanical VERDICT.json"):
        return False
    expected_protocols = manifest.get("protocol_hashes")
    if (not isinstance(expected_protocols, dict) or
            expected_protocols.get("predeclaration_sha256") != predeclaration_sha256 or
            expected_protocols.get("amendment_sha256") != amendment_sha256):
        return False
    if not producer_labels_consistent(v):
        return False
    return (v.get("confirm_overall") in CONFIRM_TERMINAL and
            v.get("q_overall") in Q_TERMINAL)


def complete_qualification(result: object, manifest: object) -> bool:
    if not isinstance(result, dict) or not isinstance(manifest, dict):
        return False
    first = result.get('first_request')
    row = result.get('native_row')
    native = first.get('native_readback') if isinstance(first, dict) else None
    identity = result.get('model_identity')
    if not isinstance(first, dict) or not isinstance(row, dict) or not isinstance(native, dict):
        return False
    if result.get('phase') != 'normal' or result.get('id') != manifest.get('id'):
        return False
    recipe_pin = manifest.get('production_recipe')
    if not isinstance(recipe_pin, dict) or not isinstance(recipe_pin.get('path'), str):
        return False
    recipe_path = Path(recipe_pin['path'])
    if recipe_path.is_symlink() or not recipe_path.is_file():
        return False
    try:
        recipe_bytes = recipe_path.read_bytes()
        recipe = json.loads(recipe_bytes)
    except (OSError, json.JSONDecodeError):
        return False
    recipe_sha = recipe_pin.get('sha256')
    if hashlib.sha256(recipe_bytes).hexdigest() != recipe_sha or not isinstance(recipe.get('server'), dict):
        return False
    expected_model = recipe['server'].get('model')
    if result.get('production_recipe_sha256') != recipe_sha:
        return False
    if first.get('ok') is not True or first.get('manifest_sha256') != manifest.get('request_manifest_sha256'):
        return False
    if first.get('production_recipe_sha256') != recipe_sha:
        return False
    if (first.get('prompt_tokens') != manifest.get('prompt_tokens_required') or
            first.get('n_ctx_total') != manifest.get('n_ctx_required') or
            first.get('n_ctx_per_slot') != manifest.get('per_slot_n_ctx_required') or
            first.get('total_slots') != manifest.get('n_parallel_required') or
            first.get('kv_cache_mode') != manifest.get('kv_cache_mode') or
            not isinstance(first.get('measured_tok_s'), (int, float)) or first['measured_tok_s'] <= 0):
        return False
    parallel = manifest.get('n_parallel_required')
    per_slot = manifest.get('per_slot_n_ctx_required')
    if (native.get('props_http') != 200 or native.get('props_total_slots') != parallel or
            native.get('props_n_ctx_per_slot') != per_slot or
            native.get('n_slots_n_ctx_slot') != [parallel, per_slot] or
            native.get('slot_contexts_n_ctx') != [per_slot] * parallel or
            native.get('props_model_path') != expected_model or
            native.get('proc_cmdline_matches_argv') is not True or
            native.get('exe_matches_binary') is not True or
            native.get('ggml_all_from_bin_dir') is not True or
            not native.get('hip_mapped') or 'true' not in str(native.get('kv_mode_from_launch_log', ''))):
        return False
    if (row.get('http') != 200 or row.get('length') != manifest.get('prompt_tokens_required') or
            not isinstance(row.get('ttft_ms'), (int, float)) or row['ttft_ms'] <= 0 or
            not isinstance(row.get('n_intervals'), int) or row['n_intervals'] <= 0 or
            not isinstance(row.get('feeder_tokens_during'), int) or row['feeder_tokens_during'] <= 0 or
            row.get('ub') != 512 or row.get('n_gen') != 1 or row.get('rep') != 1):
        return False
    return isinstance(identity, dict) and identity.get('verified') is True and len(identity.get('models', [])) == 2


def main() -> int:
    try:
        sealed, candidate_manifest_sha256 = verify_source_seal(D)
        if not sealed:
            return 1
        manifest = json.loads((D / "CANDIDATE-MANIFEST.json").read_text())
        source_code_manifest_sha256 = manifest["source_code_manifest_sha256"]
        protocol_hashes = manifest["protocol_hashes"]
        pre_sha = sha(D / "protocol" / "PREDECLARATION.md")
        amend_sha = sha(D / "protocol" / "AMENDMENT-confirm-R.md")
        if (pre_sha != protocol_hashes.get("predeclaration_sha256") or
                amend_sha != protocol_hashes.get("amendment_sha256")):
            return 1
        phase = os.environ.get("FILLER_QUAL_PHASE")
        if phase in ("normal", "cutoff"):
            manifest_path = Path(os.environ["WS58_MANIFEST_PATH"])
            qual_manifest = json.loads(manifest_path.read_text())
            result_path = Path(os.environ["FILLER_RESULTS_DIR"]) / "QUAL-RESULT.json"
            if result_path.is_symlink() or not result_path.is_file():
                return 1
            result = json.loads(result_path.read_text())
            return 0 if complete_qualification(result, qual_manifest) else 1
        row_id = manifest.get("id")
        attempt_dir = D / "out" / "attempts" / str(row_id)
        attempt_path = attempt_dir / "ATTEMPT.json"
        verdict_path = attempt_dir / "VERDICT.json"
        run_path = attempt_dir / "RESULT.json"
        input_path = attempt_dir / "run" / "pb_qcost_1.jsonl"
        paths = (attempt_path, verdict_path, run_path, input_path)
        ancestry = (D / "out", D / "out" / "attempts", attempt_dir, attempt_dir / "run")
        if any(p.is_symlink() for p in ancestry) or any(p.is_symlink() or not p.is_file() for p in paths):
            return 1
        attempt = json.loads(attempt_path.read_text())
        verdict = json.loads(verdict_path.read_text())
        run = json.loads(run_path.read_text())
        input_sha = sha(input_path)
        verdict_input_hashes = hash_verdict_inputs(attempt_dir)
        if verdict_input_hashes is None:
            return 1
        return 0 if complete_verdict(verdict, run, attempt, manifest,
            verdict_sha256=sha(verdict_path), result_sha256=sha(run_path), input_sha256=input_sha,
            source_code_manifest_sha256=source_code_manifest_sha256,
            candidate_manifest_sha256=candidate_manifest_sha256,
            predeclaration_sha256=pre_sha, amendment_sha256=amend_sha,
            expected_input_path=str(input_path), expected_verdict_path=str(verdict_path),
            verdict_inputs_sha256=verdict_input_hashes) else 1
    except (OSError, KeyError, json.JSONDecodeError, TypeError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
