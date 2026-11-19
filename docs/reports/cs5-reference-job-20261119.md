# CS-5 one-shot reference job — 2026-11-19

`scripts/speech/cs5_reference_job.py` provides the executable dispatch seam for
both native candidate APIs. It takes `--config` and `--config-sha256`; the
configuration digest is verified before execution. It must be launched through
a published compute row, not as unbooked model compute. No model was run here.

Root git object identities:

- Job: `scripts/speech/cs5_reference_job.py`, blob `d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07`.
- Controls: `tests/speech/test_cs5_reference_job.py`, blob `64353b495c4898248b9355af9a553d746b818b86`.
- Candidate APIs: root commit `aa1d892ce572c349983450f1c70ccae20a73e63f`,
  `scripts/speech/cs5_step_reference.py` and `scripts/speech/cs5_qwen_reference.py`.

The `epyc.cs5.reference_job.v1` configuration supplies candidate (`step` or
`qwen`), run_id, result_dir, source_dir, model_dir, device, subject, harness,
environment, generation, messages, expects_audio=true, input_paths,
prepared_files, co_tenant_command, and Step's prompt_wav. Each prepared file
has an absolute path, previously prepared SHA-256 and stat identity
(size, mtime_ns, device, inode). All message audio must exactly match the
prepared input set; every model-directory file and Step voice prompt must
have a receipt. Added model files, missing files and stat drift refuse before
model loading. No weight hashing occurs in admission or execution. This is a
stat admission boundary, not a fresh cryptographic proof against same-stat
content mutation; receipt provenance and immutable preparation remain the
publisher's responsibility. Environment package versions must match; Qwen's
loader additionally checks its previously described implementation source pins.
The manifest is not a complete transitive environment/code seal.

The output directory is reserved once before admission/model loading. A failed
attempt retains request.json and a summary with traceback; reusing its directory
refuses without overwriting evidence. Each successful native turn is written
through its candidate's CS-3 writer, with the prepared job retained in the
attested native JSON. A native error yields FAIL without a success sidecar;
admission/loading/Python exceptions yield INCONCLUSIVE and a nonzero CLI exit.
Signal termination or host loss is not converted into a successful result;
absence of a terminal summary must remain UNKNOWN in the row's decision rule.

The co-tenant sampler is an explicit argv, executed without a shell and with a
10-second bound during the runner's timed scope. It must return JSON with
boolean present and sampled_during_row=true. No implicit idle state is created.
Full placement fields are checked by the existing CS-3 writer. The sampler and
launcher code must be frozen in the actual prospective launch manifest.

PASS means a completed reference turn with a sidecar, not accuracy, TTFA,
encoder execution for Qwen, gfx90a residency or completed CS-5. Candidate timing
scopes still differ and remain labeled. Production kernels are untouched.
Existing Speech/VB-SPEECH-CONV-1 write-side enrollment covers the native records;
no new grading ladder, measurement warrant or planning-context canary.

Validation: all **29 model-free CS-5 tests PASS** with
`python3 -m unittest discover -s tests/speech -p 'test_cs5_*.py'`.
New controls cover both dispatch branches, prepared identity retention, input
and environment drift before loading, unreceipted model shards without weight
hashing, one-shot output refusal, loading/native failures, network-message
mismatch, duplicate receipts, config digest and sampler refusal.
`git diff --check` passes. GitNexus status/impact are unavailable because the
lane is unindexed. The new job introduces callers to the two reference APIs;
existing candidate tests pass alongside its dispatch controls.

CS-5 remains open. Next prepare the real local environment, complete weight/input
receipts and sampler identity outside grants; construct the row manifest and
publish it with publish_row.py. This code result is not publisher admission.
