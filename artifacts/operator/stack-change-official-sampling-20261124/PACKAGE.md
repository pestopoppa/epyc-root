# Stack change OFFICIAL-SAMPLING-20261124: vendor-recommended sampling on every served LLM role

Status: PREPARED, NOT APPLIED. No running process, live tree or derived file on main has been touched.

## 0 Intent

The operator directive is to use each model's OFFICIAL recommended sampling everywhere.

```yaml
generation_defaults:   # research master registry, roles.<role>.generation_defaults
  # Qwen3.6-35B-A3B-MTP-Q8_0, disable_thinking=true -> vendor Instruct/non-thinking mode
  frontdoor, worker_general, worker_summarize, toolrunner, worker_math:
    {temperature: 0.7, top_p: 0.8, top_k: 20, min_p: 0.0, presence_penalty: 1.5, repeat_penalty: 1.0}
  # Qwen3.8-27B-Q8_0, thinking on -> vendor thinking mode (= GGUF general.sampling.*)
  architect_critic, coder_escalation, ingest_long_context:
    {temperature: 1.0, top_p: 0.95, top_k: 20, min_p: 0.0, presence_penalty: 0.0, repeat_penalty: 1.0}
  # Qwen3.8-Flash-Next UD-IQ4_XS, thinking (default) -> vendor thinking mode (= GGUF)
  architect_general:
    {temperature: 1.0, top_p: 0.95, top_k: 20, min_p: 0.0, presence_penalty: 0.0, repeat_penalty: 1.0}
  # Qwen3-VL-30B-A3B-Instruct (no generation_defaults before -> greedy 0.0 fallback); alias vision_escalation
  worker_vision:
    {temperature: 0.7, top_p: 0.8, top_k: 20, min_p: 0.0, presence_penalty: 0.0, repeat_penalty: 1.0}
backend: request-side sampler reads these fields; it no longer hardcodes top_k 40 / top_p 0.95 / repeat_penalty 1.1
```

## 1 Official sources (cited per change)

| Model | Source | Values |
|---|---|---|
| Qwen3.8-27B | GGUF `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` `general.sampling.{temp,top_p,top_k}` = 1.0/0.95/20; https://huggingface.co/Qwen/Qwen3.8-27B | thinking 1.0/0.95/20/min_p 0/presence 0/rep 1.0; non-thinking 0.7/0.80/20/0/1.5/1.0 |
| Qwen3.8-Flash-Next | GGUF shard 1 `general.sampling` = 1.0/0.95/20; https://huggingface.co/Qwen/Qwen3.8-Flash-Next | the same as 27B. Thinking is the default |
| Qwen3.6-35B-A3B | GGUF `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` `general.sampling` = 1.0/0.95/20, which are the thinking values; https://huggingface.co/Qwen/Qwen3.6-35B-A3B | thinking general 1.0/0.95/20/0/**1.5**/1.0; thinking precise-coding 0.6/0.95/20/0/0/1.0; Instruct (non-thinking) 0.7/0.80/20/0/1.5/1.0 |
| Qwen3-VL-30B-A3B-Instruct | GGUF has no `general.sampling`; https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct/raw/main/generation_config.json | 0.7/0.8/20, repetition_penalty 1.0 |

**Mode choice:** the frontdoor family serves `disable_thinking: true`, so the vendor's separate non-thinking recommendation applies. Using it is following the vendor's guidance for that mode, not a deviation from it. The GGUF header holds the thinking values, so it is not the right source for these roles.

## 2 Surfaces

| Surface | Change |
|---|---|
| research `orchestration/model_registry.yaml` (master) | 9 roles' `generation_defaults` rewritten, plus a new `worker_vision.generation_defaults`. Each edit carries an inline `OFFICIAL-SAMPLING-20261124` comment with the old value and its source. Commit **`fb4dca72e`** on `origin/lane/sc-official-sampling-20261124`. Patch: `patches/research-01-official-sampling-generation-defaults.patch` |
| orchestrator `src/registry/registry_loader.py` and `src/backends/llama_server.py` (code, load-bearing) | `GenerationDefaults` gains `top_p/top_k/min_p/presence_penalty/repeat_penalty`. `resolve_sampler_params` and `_apply_deterministic_sampling` send them, and the request override still wins. When a field is unset, the legacy constants still apply, so behaviour does not change until the registry lane lands. Commit **`00ef9f47`** on `origin/lane/sc-official-sampling-20261124` (orchestrator). Patch: `patches/orchestrator-01-sampler-wire.patch` |
| orchestrator LEAN registry, `model_descriptors.yaml`, `derived/stack_priors.yaml`, `current_stack_summary.md` | DERIVED. `update` regenerates them at apply time. The preview is `patches/orchestrator-derived-PREVIEW-not-applied.diff`; the new fields pass through the compile (10 `presence_penalty` hits) |
| server launch flags (`stack_topology.yaml`, `launch_manifest.yaml`, `orchestrator_stack.py`) | none. No `--temp/--top-k/--top-p` is passed at launch; sampling is request-side |
| `sampling_axis.py` (AK) | none. It reads served T from the LEAN registry `generation_defaults`, so it follows automatically after `update`. `DIRECT_8083_TEMPERATURE = 1.0` already equals the official 27B value |
| kernel | none |

**Without the orchestrator code lane, the registry lane fixes temperature only.** top_k would stay at 40 instead of 20, top_p at 0.95 instead of 0.8 for non-thinking roles, repeat_penalty at 1.1 instead of 1.0, min_p at the server default of 0.05 instead of 0, and presence_penalty would stay unsent. **Apply both lanes together.**

## 3 Not covered (named, not deferred)

- `worker`, `worker_explore` and `worker_fast` exist only in the LEAN registry and have no `generation_defaults`, so they fall back to greedy 0.0. They are served by the frontdoor process. The fix is to give them master rows with the non-thinking block. The compile owner must decide where those rows live, so that work rides with the apply.
- `document_formalizer` / `ocr_pdf_lighton` (LightOnOCR-2-1B) have the GGUF value `general.sampling` temp 0.2 / top_p 0.9 / top_k 0. These are not role-config served LLM roles in the active lean set; when wired, they should use those values.
- Internal callers that pin `temperature=0.0` for typed decisions, judges, repair and q_judge do so explicitly per request, and the request override wins. They are deterministic tool calls, not served-role defaults, so they are unchanged and listed in REPORT.md.

## 4 Validation

- `stack_change_pipeline.py update --research-registry <research lane worktree> --allow-stale-research-registry` ran in `/mnt/raid0/llm/epyc-orchestrator/.worktrees/sc-official-sampling-20261124`. Results: lean, descriptors, priors, guard_strict, effort certs, artifact_integrity, serving_shape_capacity, stack_manifest_registry and q_scorer all came back **ok**. The one failure was `runtime_attestation`: unmanaged listeners on :8000 and :9003 on the LIVE host. It is the same pre-existing drift recorded in A3B-PMIN05 and is unrelated to this change. Log: `preflight-update.log`.
- Offline proof of the backend change, with no server involved. With role defaults {1.0, 0.95, 20, 0.0, 1.5, 1.0}, the payload is `{'temperature': 1.0, 'top_k': 20, 'top_p': 0.95, 'repeat_penalty': 1.0, 'min_p': 0.0, 'presence_penalty': 1.5, 'seed': 42}`. With temperature only, the legacy payload is unchanged (40/0.95/1.1).
- `tests/unit/test_tap_sampler_params.py` was updated and a test was added. The full pytest gate was not run because the orchestrator venv has no pytest and the system python has no fastapi. Run `check --run-promotion-gate` at apply.

## 5 Consequences the operator signs for

- **Speculative decoding acceptance falls at higher T.** MTP on the frontdoor moves from T0.3 to T0.7. DFlash2 on the 27B moves from T0.1–0.2 to T1.0. A3B-PMIN05 measured +27.9 % at T1.0, so p_min 0.5 helps the frontdoor at the new T. The 27B DFlash2 has no served-T1.0 throughput row for these roles yet; :8083 direct traffic already runs at T1.0.
- **Seed 42 stays pinned**, so outputs stay reproducible per (prompt, params) even though they are now sampled.
- **worker_math moves from greedy to 0.7.** The greedy setting had no cited rationale. If the operator wants greedy math as a deliberate deviation, drop that one role from the research patch before merging.

## 6 Apply (after signature; the owning session does it at its own reload boundary)

1. Merge research `lane/sc-official-sampling-20261124` (`fb4dca72e`) and orchestrator `lane/sc-official-sampling-20261124` (`00ef9f47`) into their mains, by ff or cherry-pick.
2. Run `python -m src.runtime.gpu_window_executor stack-change-pending set --change-id OFFICIAL-SAMPLING-20261124 --phase apply`.
3. Run `stack_change_pipeline.py update --numa-mode <declared>` (reading research origin/main, with no stale flag), then `check --run-promotion-gate`. Commit the derived outputs with a pathspec commit.

## 7 Bring-up and serving proof

- Sampling is request-side, so **no llama-server restart is needed**. Reload ONLY the API with `orchestrator_stack.py reload orchestrator`. Do not stop autopilot or the stack.
- Check that the running uvicorn is newer than the merged files (`ps -o lstart -p <pid>` vs mtimes).
- **Live API consumer path:** send one real chat completion through :8000 each for frontdoor, architect_critic, architect_general and worker_vision, each with `max_tokens` ≥ 1024 (thinking is billed against the budget). Content must be non-empty. The inference-tap START event `sampler` must show the role's official values. For each, read the llama-server `/slots` `params` for that request and confirm temperature/top_k/top_p/min_p/presence_penalty/repeat_penalty.
- Then run `stack-change-pending clear`.

## 8 Rollback

Revert `fb4dca72e` on research main, re-run `update`, commit the derived outputs, and run `reload orchestrator`. The orchestrator code commit `00ef9f47` is behaviour-neutral without the registry values and can stay, or be reverted too. There are no symlinks or kernel changes to undo.

## Sign

`bash /mnt/raid0/llm/epyc-root/artifacts/operator/stack-change-official-sampling-20261124/ratify_official_sampling_20261124.sh --attest RATIFY-OFFICIAL-SAMPLING-20261124`
