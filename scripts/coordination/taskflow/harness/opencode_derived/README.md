# Local candidate dispatch with OpenCode

Use this driver for an approved local case on a C22 slot the caller already owns. It uses OpenCode 2.2.5's Build agent, normal tool schemas and Code Mode, private subagents, supported question forms, compaction, and the configured local provider. It returns candidate and evidence files for the caller's independent acceptance. The caller selects and claims the backlog row, owns the model server, and handles any accepted patch.

Run from the root repository with Python 3.12.

```bash
PYTHONPATH=scripts/coordination python3 -B -m taskflow.harness.opencode_derived \
    /absolute/private/job.json --approved-sha256 APPROVED_DIGEST --verify-only
PYTHONPATH=scripts/coordination python3 -B -m taskflow.harness.opencode_derived \
    /absolute/private/job.json --approved-sha256 APPROVED_DIGEST --out /absolute/private/new-attempt
```

## Job and case evidence

A job lists the case directory in `case`, the frozen `case_sha256` and `prompt_sha256`, the explicit `backend`, `port`, `slot`, `thinking`, `context`, `request_cap`, `generated_ceiling`, `wall_s`, `control_cpus`, and `sampling`. Bind the owned server's JSON receipt in `serving_receipt` and `serving_receipt_sha256` and the running binary in `server_executable_sha256`. Use the owned server's live receipt with its PID, port, slot count and context, split-KV flag and resolved library maps. Bind the kernel command's model path in `model_path`. The driver checks that process, native library mappings, current KFD residency and slot geometry before dispatch. Use a slot exclusively allotted to this job. Start C22 with explicit `--cache-ram 0` to disable the shared RAM snapshot cache. C22's ordinary in-slot reuse remains available.

For CPU dispatch, launch the owned server with `--no-mmap` and a memory policy matching the CPUs assigned to its threads. After the model loads, verify its resident pages with `/proc/<pid>/numa_maps`. Preflight derives the participating NUMA nodes from live thread affinity and sysfs. It requires a single anonymous allocation with at least 75% of the combined target GGUF bytes resident, with placement on those nodes within 60–140% of an equal share. A one-node grant requires all weight pages on that node. File-backed GGUF mappings and ambiguous or split allocations fail preflight. If pages are skewed, inspect per-node free memory and the owner's launch policy, then restart the owned server under the intended placement and recheck. The driver only observes placement.

`case.json` provides the task ID, original application revision as `repo_base_sha`, original task hash as `task_packet_sha256`, allowed `editable_paths`, `oracle_sha256`, and a `baseline_files` map. Each entry in that map records SHA-256, bytes and executable status. Place source files under `baseline/`, including controller-supplied `.taskflow-refs/` reference copies. Supply the owner-approved prompt at `prompt.md` and the pinned independent acceptor at `oracle.py`. The acceptor stays outside the worker mount. Create the enclosing run directory through the scratch lease workflow and keep the owner receipt.

`assets` names the published OpenCode executable at `opencode`, its `opencode_sha256`, the frozen local OCI `image` ID, staged Python 3.12 packages at `python_packages`, and a short private `socket_root`. These paths must be visible to the local Docker daemon. The optional `skills` path and `skills_state_sha256` bind a read-only skill directory. Compute the digest with `state_digest` in this package. The qualification used OpenCode SHA-256 `8d060e1d2fbb9bb44cf09ae6ed1f3f6a7cff070b5227e2f90970132b23a92050` and image `sha256:9c429a17180a9b3ce2bce942d1bb05a7b7dfbf8218edbc267d190c35fe2b7635`. Stage exact downloaded packages and record their hashes. Set `public_web` when the approved task uses public source retrieval. The case web proxy rejects nonpublic routes. HTTPS uses a public CONNECT tunnel.

## Explicit model routes

Existing A3B jobs use the historical defaults. To select a different local
model, put its `id`, display `name`, absolute `manifest` path and
`manifest_sha256` in the job's `model` object. Launch the server with the same
`--alias`. The OpenCode provider advertises that model ID and its
`<id>-title` alias. Title requests retain a nonthinking 64-token cap and
forward to the same native model.

The operator-verified manifest records `model_id`, `template_sha256`,
`target_files` in shard order, and `draft_files` when the command has a draft
model. For each file, record its verified content `sha256` and matching
`path`, `bytes`, `device`, `inode`, `mtime_ns` and `ctime_ns` from the
same content-verification window. Use canonical absolute GGUF paths.
Preflight rechecks these file identities and the live native target, draft
and alias arguments. Its CPU residency denominator sums every target shard.
For an explicit native `--chat-template-file` override, include
`template_path` and bind its file bytes to `template_sha256`. The serve
receipt repeats `model_id`, `model_manifest_sha256` and `template_sha256`.

For CPU thinking, add `thinking_qualification` with the owner-qualified
receipt's `path` and `sha256`. Bind that receipt to the active server
`pid`, `backend` (`cpu`), `model_id`, `model_manifest_sha256` and
`template_sha256`. Record observed `enable_thinking_on`,
`enable_thinking_off` and `preserve_thinking` as true after verifying the
actual model/template. Unqualified CPU thinking and a changed serving
identity fail before the sandbox opens.

## Optional driving controls

For an approved 30-minute task, append the [driving instruction](DRIVING-INSTRUCTION-v1.md)
to the original brief in a fresh private prompt file. Keep the original brief
and case packet intact. Set the new absolute path in the job's `prompt`,
set `prompt_sha256` to that file's SHA-256, and approve the new job digest.

One seed on the Qwen3.8-27B MM-5 thinking-off arm with this guidance finished
in 1472.812 native wall seconds using 7698 generated tokens. The original CI
and a fresh independent source review accepted the result without corrective
guidance. That single run supports keeping the instruction available as an opt-in.

Thinking-on GPU `qwen38-27b-dflash2` jobs with the qualified native chat
template can set `reasoning_effort` to `"xhigh"`, `"medium"`, or `"low"`.
The setting applies to primary requests. Omit the field to keep native
template defaults. A continuation must match the saved setting exactly.
Older receipts have no effort field and can resume jobs that omit it.

## Same-task continuation

A continuation job supplies a new approved `prompt` path and its exact `prompt_sha256`, plus `resume` containing `prior_run`, `receipt_sha256`, `session_sha256`, and `workspace_session_sha256` from the saved run. Keep the same case ID, original task and application revision, slot, context, mode, sampling, provider configuration, model manifest hash and output cap. The new attempt copies the prior writable workspace and session database, restages original read-only inputs, and addresses the existing OpenCode session ID. Its receipt meters newly forwarded requests. Pass the remaining cumulative allowance in `generated_ceiling`. The proxy clamps each forwarded request to that allowance, including when it is below `request_cap`. Keep the prior artifacts and charge unknown generations using their full reservation.

## Verification

Outputs include the full stock session export, question dispositions, adapter request bodies and native timing/usage records, locally rejected adapter requests, candidate patch, and receipt. Answer-free runs explicitly decline operator questions and record their requests. The proxy translates SDK token limits to the C22 alias, uses the assigned slot and enforces the wall and output envelope independently of the tool catalog. Reasoning is preserved for thinking sessions. Stock sidecalls use the same metered path. The local case can use tools and create scratch files. The candidate checker captures changed paths and standard cache artifacts separately, then rebuilds the patch from regular, scope-checked files in an independent private worktree.

Inspect the session and scope receipt, run the task's independent acceptance in its required environment, and retain those results alongside the exact patch. Apply the normal Taskflow owner review and checkbox workflow after acceptance.

C22 can copy a RAM-cached prompt into a busy pinned slot before it defers the second request. This driver also serializes upstream sends to each physical slot within its process. The owner wall includes queue wait. A request cancelled or expired in the queue is recorded separately and consumes no generation reservation. The request ledger separates queue wait from upstream timing.
