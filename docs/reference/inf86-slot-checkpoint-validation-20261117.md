# INF-86 slot checkpoint validation on C13

**2026-11-17 · PASS · `inf86-slot-restore-ckpt-c13-20261117`**

On the 16K CPU fixture, the restored C13 slot reused all 13,754 tokens that the live slot reused. Each arm recorded `prompt_n=3260`. The restored arm’s greedy reply matched a fresh full prefill, and the slot save and restore both reported 15,831 tokens. The erase-only control reused zero tokens.

In the prior `inf86-g4-e3-tools-20261117` run on production v10 `ffc1bac82`, MOVED reused zero tokens and MOVED_LIVE reused 13,754. C13 `bda43aa17` includes the slot checkpoint serialization from upstream change #26004 via `1c999e15b`. This result applies to the 16K CPU fixture. The recorded wall times are individual observations. [Prior run and validation recipe](../../handoffs/active/hybrid-checkpoint-prompt-reuse.md)

## Recipe and acceptance rule

The run used the prebuilt C13 CPU store `cpu-20261117-bda43aa17-c13`, frontdoor Qwen3.6-35B-A3B-MTP-Q8_0, terse chat template `1443ea9ab4bb`, thinking off, draft-mtp 4, q8_0 K and V caches, 32 context checkpoints, one slot (`-np 1`), `--cache-ram 0`, and a 16,384-token fixture. The run precondition checked the source commit `bda43aa17c11b671e0e203e7eb7bf4f1303bc273`, the store binary and server library SHA-256 digests, the slot-file code string, and ggml linkage.

CTRL erases the slot before the next request. MOVED restores the tools-ended save before a request that moves the tools block, as in G4 E3. MOVED_LIVE makes the same tools move on the live slot. With a positive live baseline and CTRL reuse at or below 5% of its save, the gate passes when MOVED `cache_n` is at least 80% of MOVED_LIVE and `fresh_reply_match` is true. MOVED reached 100% of the live baseline. The native `reuse_of_saved` value of 0.8688 uses the saved token count as its denominator.

## Native evidence

The originals are `/mnt/raid0/llm/tmp/inf86-slot-restore-ckpt-c13-20261117/out/RESULT.json` and `/mnt/raid0/llm/tmp/inf86-slot-restore-ckpt-c13-20261117/out/results.jsonl`. The verdict and all six full-mode JSONL records are preserved below.

### RESULT.json

```json
{
 "arms": {
  "CTRL": {
   "cache_n": 0,
   "forced": 0,
   "fresh_reply_match": null,
   "n_restored": null,
   "n_saved": 15720,
   "prompt_n": 16903,
   "restored_ckpt": 0,
   "reuse_of_saved": 0.0,
   "wall_s": 183.1
  },
  "MOVED": {
   "cache_n": 13754,
   "forced": 0,
   "fresh_reply_match": true,
   "n_restored": 15831,
   "n_saved": 15831,
   "prompt_n": 3260,
   "restored_ckpt": 1,
   "reuse_of_saved": 0.8688,
   "wall_s": 49.4
  },
  "MOVED_LIVE": {
   "cache_n": 13754,
   "forced": 0,
   "fresh_reply_match": null,
   "n_restored": null,
   "n_saved": 15831,
   "prompt_n": 3260,
   "restored_ckpt": 1,
   "reuse_of_saved": 0.8688,
   "wall_s": 54.3
  }
 },
 "complete": true,
 "verdict": "PASS"
}
```

### results.jsonl (full 16K run)

```jsonl
{"at_epoch": 1794957572, "cls": "c16k", "cold_cache_n": 0, "cold_prompt_n": 15678, "kind": "save", "mode": "full", "n_saved": 15720, "nominal_ctx": 16384, "reply": null, "reply_chars": 231, "save_kind": "plain", "unit_id": "c16k/save-plain"}
{"at_epoch": 1794957728, "cls": "c16k", "cold_cache_n": 0, "cold_prompt_n": 15802, "kind": "save", "mode": "full", "n_saved": 15831, "nominal_ctx": 16384, "reply": null, "reply_chars": 142, "save_kind": "tools", "unit_id": "c16k/save-tools"}
{"arm": "CTRL", "at_epoch": 1794957913, "cache_n": 0, "cls": "c16k", "forced": 0, "kind": "arm", "mode": "full", "n_restored": null, "n_saved": 15720, "nominal_ctx": 16384, "ok": true, "prompt_n": 16903, "prompt_per_s": 93.4114303659676, "prompt_tokens_total": 16903, "restored_ckpt": 0, "reuse_of_saved": 0.0, "unit_id": "c16k/CTRL", "wall_s": 183.1}
{"arm": "MOVED", "at_epoch": 1794958137, "cache_n": 13754, "cls": "c16k", "forced": 0, "fresh_reply_match": true, "kind": "arm", "mode": "full", "n_restored": 15831, "n_saved": 15831, "nominal_ctx": 16384, "ok": true, "prompt_n": 3260, "prompt_per_s": 67.75168284996664, "prompt_tokens_total": 17014, "restored_ckpt": 1, "reuse_of_saved": 0.8688, "unit_id": "c16k/MOVED", "wall_s": 49.4}
{"arm": "MOVED_LIVE", "at_epoch": 1794958349, "cache_n": 13754, "cls": "c16k", "forced": 0, "kind": "arm", "mode": "full", "n_restored": null, "n_saved": 15831, "nominal_ctx": 16384, "ok": true, "prompt_n": 3260, "prompt_per_s": 61.5691653461088, "prompt_tokens_total": 17014, "restored_ckpt": 1, "reuse_of_saved": 0.8688, "unit_id": "c16k/MOVED_LIVE", "wall_s": 54.3}
{"arms_done": ["CTRL", "MOVED", "MOVED_LIVE"], "at_epoch": 1794958350, "cls": "c16k", "kind": "class", "mode": "full", "nominal_ctx": 16384, "ok": true, "server_reaped": true, "unit_id": "c16k"}
```
