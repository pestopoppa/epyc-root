# Model artifact integrity — pinned, verified and reviewed weights and templates

**Status**: stub
**Created**: 2026-10-21 (via research intake, operator-approved 2026-10-21 plan intake-backdoor-cvec-20261020)
**Scratch**: `/mnt/raid0/llm/tmp/model-artifact-integrity/`
**Categories**: local_inference, agent_architecture, tool_implementation
**Related**: [model-exec-containment.md](model-exec-containment.md) (runtime side) · [qwen-chat-template-evaluation.md](qwen-chat-template-evaluation.md) (template CHOICE and CT-12; this handoff owns template INTEGRITY) · [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md) (registry consistency)

## Objective

Make every GGUF, drafter and chat template we serve traceable to a pinned upstream revision and a
recorded hash, checked at download, at launch and at re-pull, and give community fine-tunes a review
gate before they reach a tool-bearing role. A backdoor can live in weights (intake-2191#record) or in a
chat template with no weight change (intake-2200#record), and community relays can repackage trusted
weights with extra sidecar files under misleading labels (intake-2197#record).

## Current state (verified 2026-10-21)

- `scripts/utils/safe_download.py` only cleans up partial files; it records no revision or sha256.
- The model registry carries free-text provenance for a few roles; `validate_model_registry.py` checks
  no sha256 or revision fields; no GGUF hash is verified at llama-server launch.
- `served_template_sha256_12` exists for three roles and is read only by an offline certification
  check; the launcher does not compare the served template with a pin. Template override files are
  owned by the service user.
- No production `--lora` or `--control-vector` is loaded.

## Tasks

- [ ] **SEC-ART-1 — Revision and sha256 pinning at download.** scripts/utils/safe_download.py records the resolved HF commit sha and per-file sha256 (LFS oid) into a download ledger; new-model Step 0 passes --revision; add hf_repo / hf_revision / sha256 fields to the model registry schema, check them in validate_model_registry.py and backfill the serving lineup.
- [ ] **SEC-ART-2 — Launch-time GGUF fingerprint check.** Hash each lineup GGUF in full at registration; at launch compare a stat fingerprint (size, mtime, inode) and re-hash only on change; the launcher refuses a role whose GGUF does not match its pin; a test uses a touched copy.
- [ ] **SEC-ART-3 — Uploader class and review record for tool-bearing roles.** Add an uploader_class field (first-party / allowlisted re-quantizer / community) to the registry; a stack-change gate refuses to give a community fine-tune tool access without a recorded review covering provenance, a base-model diff where a base exists, and a label-vs-function check of every launch flag that changes generation (intake-2191#07, intake-2199#03, intake-2197#record).
- [ ] **SEC-ART-4 — Enforce served-template pins at launch.** Add a 64-hex served_template_sha256 for every lineup role; before llama-server starts, the launcher hashes the effective template (GGUF tokenizer.chat_template or the --chat-template-file bytes) and refuses on mismatch; a test uses a one-byte-modified template copy (today the 12-hex pin is read only by an offline certification check; intake-2200#05).
- [ ] **SEC-ART-5 — Upstream template diff at onboarding.** new-model records upstream_template_sha256, served_template_sha256 and a reviewed diff path for every GGUF; validate_model_registry.py requires them for lineup roles.
- [ ] **SEC-ART-6 — Read-only template store.** Serve template override files from a location agent sessions cannot rewrite (or a content-addressed path named by sha256), referenced from the registry, so the launch check is not the only barrier.
- [ ] **SEC-ART-7 — Re-pull drift check.** safe_download refuses to overwrite or upgrade a registered artifact when the repo commit sha or any file LFS oid differs from the registry pin, unless a review record is passed; a test uses a mocked HF tree-API response.
- [ ] **SEC-ART-9 — Relay and sidecar check.** When a repo presents itself as a copy of an upstream, compare every LFS oid with the claimed upstream through the HF tree API and list every file the upstream lacks (intake-2197#00 found a byte-identical relay plus one refusal-direction sidecar); record the result in the SEC-ART-3 review.

## Monitors (trigger prose, no checkbox)

- Trigger (no checkbox): a public implementation of the arXiv 2602.03085 backdoor scanner appears (linked from the paper or Microsoft AIRT), or a community fine-tune enters a SEC-ART-3 review for a tool-bearing role. Then file a bounded probe: scanner steps 1-2 on that artifact plus one clean lineup GGUF of the same family, wall time and motif clusters recorded, advisory only, never an admission gate (intake-2209#record).

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2191#record | ProjectDiscovery: QLoRA trigger-phrase backdoor in an open tool-calling model | high | adopt_patterns | dive-verified |
| intake-2200 | Inference-time backdoors via chat templates | high | new_opportunity | dive-verified |
| intake-2197 | Community relay of GSQ-RCO quants plus a refusal-direction sidecar | medium | worth_investigating | dive-verified |
| intake-2208 | ProjectDiscovery: leaked write tokens and the model supply chain | high | adopt_patterns | dive-verified |
| intake-2209 | Trigger in the Haystack: backdoor-trigger extraction scanner | medium | worth_investigating | dive-verified |

## Open Questions

- Which uploaders count as allowlisted re-quantizers for SEC-ART-3 (operator policy input when the field lands)?
- Full re-hash cost at registration for the largest lineup GGUFs (SEC-ART-2 measures it once; launch uses a stat fingerprint).

## Notes

- Prompt-level defences and rendered-sentinel hashes are not template-backdoor protection (intake-2200#record); the defence is hashing the template bytes that will be served.
- The 2602.03085 scanner is advisory at most (no code release; untested on GGUF, MoE, tool-call targets or >14B).
