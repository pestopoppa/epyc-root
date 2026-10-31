# UFH14-B4g: native 27B DFlash2 prompt-cache entry, current shape

On 2026-10-30, a private v10 scratch server with the current :8083 shape emitted the first usable native `prompt_save`, checkpoint and retained-entry records. The source :8083 launch record was preserved verbatim; the scratch command changed only the binary path to the verified v10 private view, port to 18083, slot-save path, and TRACE verbosity (`-lv 4`). The model and drafter were the canonical Qwen3.8-27B-Q8_0 and Qwen3.8-27B-DFlash2-Q8_0 GGUF files. No production server was stopped or reloaded by this run.

The executed shape was `-np 4 -c 393216 -b 512 -ub 512 -ctk q8_0 -ctv q8_0 --kv-unified --cache-ram 65536 --ctx-checkpoints 32 --no-cache-idle-slots --spec-draft-n-max 7`. Four long completion contexts were placed in the four slots; a distinct short completion forced LRU reuse. Native lines from the first successful private server log:

```text
slot get_availabl: id  3 | task -1 | selected slot by LRU
srv prompt_save:  - saving prompt with length 8052, total state size = 457.259 MiB (draft: 40.096 MiB)
srv update:    - prompt ...: 8052 tokens, checkpoints: 2, 836.558 MiB
slot create_check: ... n_tokens = 7533, size = 189.650 MiB
slot create_check: ... n_tokens = 8041, size = 189.650 MiB
```

**The retained entry costs 836.558 MiB at 8,052 tokens with two checkpoints.** The `prompt_save` state is 457.259 MiB, including 40.096 MiB draft state; target state by subtraction is 417.163 MiB. Each checkpoint object is 189.650 MiB. The 836.558 MiB entry is the server's native aggregate, not a sum or a fit. A second smoke through the actual private launcher reported native full retained entries of 836.325 MiB at 8,045 tokens and 836.511 MiB at 8,050 tokens, each with two checkpoints; corresponding base states were 457.026 and 457.212 MiB with 40.096 and 40.116 MiB draft. The four values within that second smoke share one process and controlled slot reuse. The two smokes were separate processes but were not designed as independent protocol replications. They do not establish a token-length slope or production cache-policy effect.

Provenance: the private `llama-server` SHA-256 was `2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b`; mapped v10 `libggml-hip.so.0.16.0` SHA-256 was `f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079`. `/proc/<captured-pid>/maps` contained v10 base, CPU and HIP libraries from `gpu-20260921-ffc1bac82/bin`, and KFD recorded 51,338,338,304 bytes of VRAM during the first run. The source launch record SHA-256 was `612323d93632856a923b2d163b7486b9e48e87645f41b16e0602260667c33149`. Canonical model size and first/last 64 MiB digests are preserved in the raw packet's `MODEL-PINS.json`: main model 29,047,086,048 bytes / `a73765af3f7aca5ede5e8e1fe918979b86d3bf8c58b0a2e8dfd35eaa60e42861`; drafter 2,056,414,752 bytes / `d30f93310dbc27c5b3491efc39299b7a18c4b85383bf0b485f72603ba6d17216`.

Raw packet: `/mnt/raid0/llm/tmp/codex-ni-ufh14-b4g-20261030/REVIEW.md` and `EVIDENCE.sha256`. The first successful raw log SHA-256 is `466bce02a75cb1194baace26473a57c5c76cb27833a60380e5840e091f547556`; the first parsed result SHA-256 is `377a735ea6a4e58bcd9b1c9dcf28e517267788fdcc9acc07dd5fed9fb99db828`. The first runner source was edited after that run; the packet labels its recovered version as **reconstructed**, with no contemporaneous source SHA. The second actual-launcher smoke and the real deadline-75/partial/owned-child-drain test are retained in the same packet and hash list. Neither failed qualification attempt contributes a measurement. This entry is a bounded native observation for UFH14-B4g/PFX-SEL-1, not a retroactive `ClaimTuple` measurement warrant or policy recommendation.

The agent task audit is in `logs/agent_audit-codex-ni-ufh14-b4g.log` (separate writer shard). Source status: `serving_call.v1` already captures call timings, but no native retained-entry size. The prospective native cache-state source row and `VB-SERVE-CACHE-STATE-WRITE` task are registered in `scripts/vidya/adapters/README.md` and `handoffs/active/vidya-belief-substrate-program.md`. No writer, reader or planning-context canary is claimed here.
