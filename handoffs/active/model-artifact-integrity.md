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
  - 2026-10-21 (workspace-f8): IMPLEMENTED, NOT ticked. Root `a9fccdc21`: `safe_download.py` `--hf-repo/--revision/--no-resolve/--provenance-ledger` (resolves commit sha, forces `hf download --revision <sha>`, appends per-file LFS sha256 to `data/provenance/model_downloads.jsonl`); new-model Step 0 passes `--revision`. Orchestrator `a9a3365a`: `registry_validator.py` checks `roles.<role>.model.{hf_repo,hf_revision,sha256}` (missing = WARN; malformed = error; `REGISTRY_ARTIFACT_PINS_STRICT=1` / `--strict-artifact-pins` makes missing fatal) and `scripts/validate/backfill_registry_artifact_pins.py` (plan only, size-match to HF LFS oid, no GGUF hashing). Pending: lineup backfill into the master registry and the strict flip (SEC-ART-1.1).
- [ ] SEC-ART-1.1 — run the registry backfill (HF tree API read-only; network go-ahead given 2026-10-21 by workspace-f8 for metadata reads only) then flip strict mode
- [ ] **SEC-ART-2 — Launch-time GGUF fingerprint check.** Hash each lineup GGUF in full at registration; at launch compare a stat fingerprint (size, mtime, inode) and re-hash only on change; the launcher refuses a role whose GGUF does not match its pin; a test uses a touched copy.
- [ ] **SEC-ART-3 — Uploader class and review record for tool-bearing roles.** Add an uploader_class field (first-party / allowlisted re-quantizer / community) to the registry; a stack-change gate refuses to give a community fine-tune tool access without a recorded review covering provenance, a base-model diff where a base exists, and a label-vs-function check of every launch flag that changes generation (intake-2191#07, intake-2199#03, intake-2197#record).
  - *(2026-10-21, operator.)* Allowlist decided (option B): `unsloth` and `lmstudio-community` are allowlisted re-quantizers; a one-time review of the frontdoor and worker GGUFs comes first, before the field is populated for them.
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

- ~~Which uploaders count as allowlisted re-quantizers for SEC-ART-3?~~ Answered 2026-10-21 (operator): `unsloth` and `lmstudio-community`.
- Full re-hash cost at registration for the largest lineup GGUFs (SEC-ART-2 measures it once; launch uses a stat fingerprint).

## Notes

- Prompt-level defences and rendered-sentinel hashes are not template-backdoor protection (intake-2200#record); the defence is hashing the template bytes that will be served.
- The 2602.03085 scanner is advisory at most (no code release; untested on GGUF, MoE, tool-call targets or >14B).

## SEC-ART-4 design (design only; no code landed)

**Gap.** `served_template_sha256_12` is read only by `scripts/validate/reasoning_effort_certifications.py`
(`_bound_template_sha`, which truncates any sha to 12 hex). `orchestrator_stack.py:_append_runtime_serving_flags`
only checks that a `chat_template_file` path EXISTS before emitting `--chat-template-file`; nothing compares bytes,
and a role with no `chat_template_file` silently serves the GGUF-embedded `tokenizer.chat_template`.

**Registry field.** `roles.<role>.chat_template.served_template_sha256` = 64 lowercase hex (sha256 of the exact
effective template bytes). The existing `served_template_sha256_12` stays and must equal its first 12 chars
(validator error otherwise), so the certification reader keeps working unchanged. Compiled through
`registry_compiler.compile_lean` as-is (roles pass through); `registry_validator.py` gains
`_check_template_pins(registry, strict)`: shape check always an error, missing is WARN until the lineup is
backfilled, then flipped by `REGISTRY_TEMPLATE_PINS_STRICT=1` (same switch design as SEC-ART-1).

**New module `src/registry/template_pin.py`** (pure, no llama-server import):
- `read_gguf_chat_template(gguf_path) -> bytes | None` - reads ONLY the GGUF header metadata (magic, version,
  n_tensors, n_kv, then the KV records; stop at key `tokenizer.chat_template`, type STRING = 8; length-prefixed
  uint64 + raw bytes). Never touches tensor data, so it is a few KB of I/O even on a 40 GB file. Returns None if
  the key is absent. Handles GGUF v2/v3 only; any other version raises `TemplatePinError`.
- `effective_template_bytes(chat_template_file: str | None, gguf_path: str) -> tuple[bytes, str]` - mirrors
  llama-server precedence: `--chat-template-file` bytes if the flag is emitted, else the GGUF template. The second
  value is the source label (`file:<path>` / `gguf:<path>`). A command carrying `--chat-template` (inline) is
  refused outright (cannot be pinned by path; the launcher never emits it today).
- `template_sha256(data: bytes) -> str` (64 hex), `check_template_pin(role, effective, pinned) -> None` raising
  `TemplatePinError(role, source, expected, actual)`; the message carries both full digests and the source path.

**Launcher wiring.** In `scripts/server/orchestrator_stack.py` add `_verify_served_template(role_name, cmd, flags)`
and call it from `build_server_command` after the per-mode builder returns `cmd` (so it sees the FINAL argv, not
the registry's intent) and before `start_server` reaches either `subprocess.Popen` (lines ~1907/1980). It parses
`--chat-template-file` and `-m/--model` out of `cmd`, calls `effective_template_bytes`, and compares with the
role's pin from `_stack_prior_launch(role_name)` (extend that tuple's `flags` with `served_template_sha256`).
On mismatch it raises `TemplatePinError`; `start_server` converts it to the same refuse-and-return-None path the
missing-path ValueError takes, prints `REFUSED <role>: template sha256 <actual> != pinned <expected> (<source>)`
and writes a `kind: template_pin_refusal` line to the stack-change ledger. Embedders and aux services without a
chat template (`embedding_mode`) skip the check; a role with a template-bearing model and NO pin is a WARN in
non-strict mode and a refusal under `REGISTRY_TEMPLATE_PINS_STRICT=1`. The check also runs in `cmd_start`'s
validate-only path (`stack_commands.cmd_start` -> `validate_or_raise` neighbourhood) so `--validate-only`
reports pin failures without starting anything. No `--jinja` flag handling changes.

**TOCTOU.** The hash is of bytes read by the launcher, llama-server re-reads the file microseconds later. For
file templates, close the window by launching with a content-addressed copy: SEC-ART-6 serves overrides from
`.../chat-templates/sha256/<64hex>.jinja` (read-only), so the path itself names the pinned digest and the launch
check becomes a belt-and-braces recheck. Until SEC-ART-6, the launcher re-hashes after `Popen` has logged the
banner (cheap) and `stack_log_banner.write_launch_banner` records the digest so a post-launch swap is visible.

**Test plan** (foreground, orchestrator venv, fixtures only, no server):
1. `tests/unit/test_template_pin.py`: build a minimal GGUF in `tmp_path` (struct-packed header, two KVs, one with
   `tokenizer.chat_template`, zero tensors) - assert `read_gguf_chat_template` returns the exact bytes; a GGUF
   without the key returns None; a truncated header and a v1 magic raise `TemplatePinError`; a 1 GiB sparse file
   with the same header proves no full-file read (assert `os.read` total < 1 MB via monkeypatched open).
2. File precedence: `effective_template_bytes(file, gguf)` returns the file bytes and `file:` label; with
   `None` returns the GGUF bytes and `gguf:` label.
3. One-byte mutation: copy the template, flip one byte -> `check_template_pin` raises with both digests; the
   unmodified copy passes. Same for the GGUF-embedded path (mutate one byte inside the KV value).
4. `tests/unit/test_orchestrator_stack_template_pin.py`: with `subprocess.Popen` patched to raise if reached,
   `start_server` on a registry fixture whose pin mismatches returns None/raises and Popen is NEVER called;
   matching pin reaches Popen. Inline `--chat-template` argv is refused.
5. Validator: 64-hex shape errors, 12-char prefix consistency error, WARN-vs-strict switch (mirrors
   `tests/unit/test_registry_artifact_pins.py`).
6. Live-registry backfill check (read-only): for each lineup role with `chat_template_file`, the hash of the
   file equals the existing `served_template_sha256_12` prefix (expected `1443ea9ab4bb` for the terse template,
   25808 bytes); roles that use a GGUF-embedded template are listed for the header-read backfill.
