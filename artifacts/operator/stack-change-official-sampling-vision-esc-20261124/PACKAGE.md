# Stack change OFFICIAL-SAMPLING-VISION-ESC-20261124: close the vision_escalation sampling gap

Status: PREPARED, NOT APPLIED. No running process, live tree or derived file on main has been touched. The production stack is down by operator choice and this package does not start it.

## 0 Intent

RATIFY-OFFICIAL-SAMPLING-20261124 gave `worker_vision` (Qwen3-VL-30B-A3B-Instruct, :8086) the vendor generation_defaults but left its alias `vision_escalation` (same process, same port, same weights) with none. Requests addressed to `vision_escalation` still fall back to the backend defaults: T0.0 / top_k 40 / repeat_penalty 1.1.

```yaml
generation_defaults:   # research master registry, roles.vision_escalation.generation_defaults
  vision_escalation:
    {n_tokens: -1, temperature: 0.7, top_p: 0.8, top_k: 20, min_p: 0.0, presence_penalty: 0.0, repeat_penalty: 1.0}
```

These are the values already on `worker_vision`. Source: https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct/raw/main/generation_config.json (0.7 / 0.8 / 20, repetition_penalty 1.0); the GGUF carries no `general.sampling`. The block carries an inline `OFFICIAL-SAMPLING-20261124` source comment.

## 1 Surfaces

| Surface | Change |
|---|---|
| research `orchestration/model_registry.yaml` (master) | One block: `roles.vision_escalation.generation_defaults` (+9 lines). Commit **`6522e7c0b`** on `origin/lane/sc-official-sampling-vision-esc-20261124`, based on research `origin/main`. Patch: `patches/research-01-vision-escalation-generation-defaults.patch` |
| orchestrator LEAN registry, descriptors, priors, summary | DERIVED. `stack_change_pipeline.py update` regenerates them at apply time |
| orchestrator code | none. The sampler wire from RATIFY-OFFICIAL-SAMPLING-20261124 (`00ef9f47`) already reads these fields; it must be merged first or together |
| launch flags, kernel, `sampling_axis.py` | none |

## 2 Dependency

The backend commit `00ef9f47` (orchestrator lane `sc-official-sampling-20261124`) is what puts top_p/top_k/min_p/penalties on the wire. Without it this block changes temperature only. It is part of the already-signed package, so apply this one with or after it.

## 3 Validation done

- The block parses (PyYAML) and `roles.vision_escalation.generation_defaults` equals `roles.worker_vision.generation_defaults` field for field.
- The branch was pushed with an explicit `refs/heads/lane/...` refspec; main was not touched.
- `ratify_official_sampling_vision_esc_20261124.sh --validate-only` checks the pinned package content and that `6522e7c0b` is on `origin/lane/sc-official-sampling-vision-esc-20261124`.
- Not run: `stack_change_pipeline.py update` / `check --run-promotion-gate` (apply-time steps, they touch derived files).

## 4 Consequences the operator signs for

- Vision requests addressed to `vision_escalation` become sampled (T0.7) instead of greedy; seed 42 stays pinned, so they stay reproducible per (prompt, params).
- No server restart: sampling is request-side. Reload only the API (`orchestrator_stack.py reload orchestrator`) at the owning session's boundary.

## 5 Apply (after signature; the owning session does it at its own reload boundary)

1. Merge research `lane/sc-official-sampling-vision-esc-20261124` (`6522e7c0b`) into research main, by ff or cherry-pick, together with or after the OFFICIAL-SAMPLING lane.
2. Run `stack_change_pipeline.py update`, then `check --run-promotion-gate`; commit the derived outputs with a pathspec commit.
3. Reload ONLY the API. Send one chat completion for `vision_escalation` through :8000 (max_tokens >= 1024) and confirm the inference-tap START `sampler` shows 0.7 / 0.8 / 20 / min_p 0 / presence 0 / repeat 1.0, and that the llama-server `/slots` `params` agree. This needs the vision server up, which the operator starts.

## 6 Rollback

Revert `6522e7c0b` on research main, re-run `update`, commit the derived outputs, reload the API.

## Sign

`bash /mnt/raid0/llm/epyc-root/artifacts/operator/stack-change-official-sampling-vision-esc-20261124/ratify_official_sampling_vision_esc_20261124.sh --attest RATIFY-OFFICIAL-SAMPLING-VISION-ESC-20261124`
