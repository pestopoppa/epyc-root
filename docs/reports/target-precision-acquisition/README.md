# Target-precision input acquisition

The prospective matched target-precision row uses `/mnt/raid0/llm/tmp/df2/target-precision-inputs` as its declared task-specific scratch root. The downloader streams pinned BF16 shards and a non-UD Q4_K_M target, verifies their declared lengths and SHA-256 values outside any grant, and writes a completion or failure event to the handoff session. It rechecks the shared disk floor plus remaining transfer size and host memory headroom during transfer. The task storage survives reboot. Completion/failure is written to `/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result.json`; register that exact event path before starting acquisition. Retries accept only the pinned filenames and refuse foreign files, directories and symlinks. Completed files are reverified against their full pinned digest; partial files remain unverified until the full digest passes. A partial transfer resumes only with HTTP 206 and an exact Content-Range and remaining Content-Length; ignored or incorrect ranges never append bytes. Resource-floor, network and interruption failures retain partial bytes for retry; a full digest failure removes the corrupt partial. No verified file is overwritten. Re-establish verified inputs before publication and retain completed shards through the row's declared keep policy.

`source-manifest.json` records exact repository revisions, source URLs, expected hashes and bounded header evidence. Both converted sources name the same model family, but their exact shared base revision and tensor correspondence remain unproven. Preserve that limitation and return an inconclusive causal verdict if matched identity cannot be established. This preparation provides no inference result or precision effect.

Recovery on 2026-11-20 found the original acquisition receipt FAILED (signal 2, zero completed files). The pinned source manifest is unchanged. The downloader now reserves the entire remaining transfer above the 150 GiB disk floor on every chunk, uses durable task storage, and no longer gates disk-backed transfers on tmpfs capacity. This repair does not download inputs, establish tensor correspondence, or provide an inference result.

Use `compare_catalogs.py --gguf-python /path/to/llama.cpp/gguf-py --arm BF16=shard1 --arm BF16=shard2 --arm Q4_K_M=target --output comparison.json` for payload-free name/shape comparison. All shards are mandatory. Catalog equality leaves the causal gate unresolved. See [the 2026-11-20 precondition finding](catalog-precondition-20261120.md).

The durable acquisition event delivered on 2026-11-20 reports FAILED: remaining transfer would breach the 150 GiB disk floor, with zero verified files. Receipt `/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result.json`, SHA-256 `97950972b09ce4bccb7077d816308978cd6e842ca9a1953e7011bd4efa00a114`. The old downloader deleted the in-flight prefix, then refused its existing destination on retry. Recovery now preserves unverified prefixes, rehashes them before resuming, and maintains the same disk and memory floors. Fourteen downloader controls plus twelve catalog controls pass (26 tests); no new transfer, matrix or precision conclusion is claimed. The parent control remains open.

Retry disk reservation now subtracts bytes already retained in later shards, including both completed files and partial prefixes. This is storage accounting only: every completed file and every resumed prefix still passes the full pinned SHA-256 check before completion. Ambiguous completed/partial pairs and oversized later prefixes are refused before a transfer starts. A simulated three-shard retry finishes with exactly the 150 GiB floor remaining; a corrupt retained later shard still fails identity verification. The combined downloader/catalog suite passes 30 tests.

The delivered retry event `result-retry-20261120T013858Z.json` also FAILED at the unchanged 150 GiB disk floor, with zero verified files and 24,930,942,976 unverified bytes retained in the first BF16 shard. Receipt path `/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result-retry-20261120T013858Z.json`, SHA-256 `4db4bd19570a1917226c9b355227b922d09e600cf8ae7c70d9089f5dc40018b6`. This is an acquisition precondition failure, not a precision result. The operator requested scratch cleanup on 2026-11-20; the unverified 24,930,942,976-byte prefix has now been deleted. A future admitted acquisition starts fresh from the pinned manifest. Do not infer equivalence from the failed acquisition or publish the matrix before all inputs and native-field controls qualify.


## Single-source replacement plan (2026-11-20)

[`matched-source-plan-20261120.json`](matched-source-plan-20261120.json) replaces the mixed-converter acquisition **for the prospective precision control**. The historical downloader and receipts remain historical evidence. The new plan binds upstream `Qwen/Qwen3.8-27B` revision `37561816e66b5b9153b1b64c10968c18c1e6f4a0`: 18 indexed safetensors shards plus seven conversion/tokenizer metadata files, **55,586,027,630 source bytes**. Its shard index was read at that revision and checked against the API-recorded Git blob identity and length. LFS files carry full expected SHA-256; small metadata files carry Git blob identities. These are expected identities, not verified downloads.

`scripts/diagnostics/target-precision/plan_weights.py` rejects unpinned revisions, altered shard indices, extra/missing shards, unsafe/duplicate paths and malformed source identities. It specifies one BF16 conversion, then independent Q8_0 and Q4_K_M quantizations directly from that same BF16 output, with no importance matrix or requantization. Converter source is pinned to the current production commit as a **read-only reference for a future experimental build**; production is never built or modified. Tool content/build binding, original logs/output hashes, tensor/tokenizer correspondence and the drafter's exact upstream compatibility must still be established before a weight receipt is emitted. No weight receipt is emitted by this planner.

Storage admission is **REFUSED**: 256,106,651,648 available bytes at the snapshot versus 553,384,692,482 required including the unchanged 150 GiB floor. The conservative peak keeps all source files plus three output caps, each twice source size plus 1 GiB for alignment/metadata: **392,323,418,882 additional bytes**. This is a declared preparation envelope, not measured output sizes or an impossibility claim about a tighter plan. Actual preparation must enforce the caps and recheck resource floors throughout; the snapshot reserves no shared storage. No transfer or conversion was started. Next implement tensor-aware output sizing from pinned headers to replace the conservative caps, then evaluate resource admission; no blind retry of the old mixed-source downloader. The floor/matrix stays unpublished and the causal precision gate stays unresolved.

Validation: 16 model-free planner tests cover shared-parent commands, exact disk-boundary admission and provenance/refusal controls. The planner performs no network access, weight reads, subprocesses or inference.

## Converter and quantizer source audit (2026-11-20)

[`converter-sizing-20261120.json`](converter-sizing-20261120.json) binds seven
read-only source files to production commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, by Git blob and SHA-256, and verifies
config metadata against the pinned upstream Git identity. No production tree
was built or changed. The default text converter retains **866 tensors /
27,320,697,856 elements**, including the MTP head, and drops **333 vision
tensors**. Reordering, norm adjustment and A-log transformation preserve shape;
this catalog uses no fused-QKVZ or expert path and no generated extra tensors.

The BF16 payload cap is **54,646,738,944 bytes**, including **2,671,616 F32
values** (norms/vectors/convolution tensors). Each quantized payload cap is
**29,036,089,344 bytes**. Q4_K_M uses a conservative Q8 ceiling covering mixed
quantization and compatible fallbacks; it is not a prediction of the exact Q4
file size. Per-arm metadata/alignment reserves give output caps of
**55,720,508,480 BF16 bytes** and **30,109,858,880 bytes** for each quantized arm.
Retaining the source plus all outputs requires **332,587,527,470 free bytes**,
including the unchanged 150 GiB floor, versus **280,157,663,232 available bytes**
at this snapshot: **disk admission REFUSED**. Execution remains unadmitted.

Source paths at that commit explain the bounds:

- `conversion/__init__.py` selects the text Qwen class; `conversion/base.py`
  `TextModel.filter_tensors` excludes vision. `conversion/qwen.py`
  `_Qwen35MtpMixin.filter_tensors` retains/remaps the MTP head. The inherited
  `generate_extra_tensors` returns an empty sequence.
- `conversion/base.py` `prepare_tensors` keeps vectors, norms and SSM conv1d in
  F32. `conversion/qwen.py` reorders heads, transforms A-log and adjusts norms
  without increasing retained element counts for these unfused dense tensors.
- `src/llama-quant.cpp` `tensor_allows_quantization` preserves these F32 tensors;
  default Q4_K_M mixture choices and `tensor_type_fallback` fit the Q8 ceiling
  or use F16 for rows incompatible with 32-value blocks.
  `ggml/src/ggml-common.h` defines the 32-value / 34-byte Q8_0 block.
- `gguf-py/gguf/gguf_writer.py` writes default lazy tensors directly. Its optional
  temporary spool is excluded by the planner's exact command-policy check.
  `src/llama-quant.cpp` mmaps input and requests F32-conversion and work buffers,
  each at most **5,085,593,600 logical bytes** for the largest retained tensor.
  Together they hold up to **10,171,187,200 logical bytes**; logical old/new
  overlap during reallocation is at most **15,256,780,800 bytes**. These are not
  total allocated-capacity or RSS bounds. No total RAM admission is claimed.

The tested planner reads metadata and audited tool source only. Headers do not
verify weight payloads; the metadata reserve needs enforcement; tool-build,
tensor/tokenizer and drafter correspondence still require receipts. No transfer,
model execution, numerical-floor measurement or causal precision finding occurred.


## Staged preparation and resource controls (2026-11-20)

[`preparation-schedule-20261120.json`](preparation-schedule-20261120.json)
compares two explicit serial placements from the audited converter bounds.
All-durable staging needs **278,075,241,664 free bytes**, including the unchanged
150 GiB disk floor and 1 GiB total control reserve; the snapshot has
**277,417,951,232 available bytes**, so that placement is refused. Source release
reduces its peak, but does not reserve capacity against other sessions.

The explicit `tmpfs-intermediates` candidate puts pinned source shards and BF16
in task-owned tmpfs scratch, with Q8_0/Q4_K_M outputs and provenance receipts on
durable storage. It needs **222,354,733,184 disk bytes**,
**112,380,277,934 tmpfs bytes**, and **517,180,945,582 host-available bytes**.
All three envelopes fit this snapshot. The RAM calculation includes the unchanged
250 GiB host floor, the worst simultaneous tmpfs footprint, and the converter's
128 GiB cgroup budget, conservatively double-counting pages also charged to that
cgroup. Quantizers each get 64 GiB; acquisition gets 4 GiB. These are proposed
enforced budgets, not measured memory sufficiency. No capacity is reserved.

Source release requires verified pinned payloads, BF16 full tensor/tokenizer
correspondence, and retained source/build/output receipts, and can affect only
this task's source files. The planner performs no deletion. A reboot loses
source/BF16 tmpfs files: reacquire/rederive and fully reverify before publication;
receipts alone never establish that weights still exist. All three target arms
must exist and pass admission when the prospective matrix is readied.

`scripts/diagnostics/target-precision/preparation.py` implements planning and a
single-command Linux guard. The guard refuses a shared/nonempty or unbounded
cgroup, requires exact `memory.max`, zero swap and group OOM, joins and verifies
the captured child's membership before exec, and applies `RLIMIT_FSIZE` to the
audited single-output command. It retains merged original stdout/stderr through
a pipe with a separately enforced log cap, samples remaining disk budget and the
250 GiB host-memory floor, sets a deadline, and reaps its captured process group
on success and failure. It does not edit shared cgroup settings. A cgroup memory
budget hit fails the command even if it returns zero. Partial outputs/logs are
retained as failures; success is not a verified-weight receipt.

**Execution remains unadmitted.** The current root cgroup is shared and refused.
No delegated leaf, external per-volume supervisor or verified-source release
implementation is claimed. The acquisition integration below adds in-process
budget checks; it does not yet admit a live acquisition.
Disk/host sampling can detect shared resource loss but cannot reserve capacity
or prevent another session consuming space between samples. The wrapper is for
single-threaded callers and audited serial single-output commands; split/temp
outputs require another audit. Its tests use tiny metadata and fake children /
cgroup files: **32 controls pass**, including exact capacity boundaries, separate
tmpfs/RAM refusal, existing-output protection, cgroup/host-memory/OOM refusal,
log cap, deadline, disk-loss and captured-child cleanup. No actual delegated
cgroup, converter, quantizer, acquisition or inference was executed. Full target
precision suite: **296 passed, 11 optional tests skipped**.

## Matched-source acquisition guard (2026-11-20)

`scripts/diagnostics/target-precision/acquisition.py` consumes the existing pinned
single-upstream plan rather than the historical mixed-converter downloader.
It requires explicit `durable` or `tmpfs-intermediates` placement, verifies the
actual mount type, and keeps durable controls separate from source files.
Admission rejects the shared root cgroup, non-kernel directories, populated
subtrees, mismatched memory limits, swap and missing group-OOM enforcement.
The dedicated acquisition process joins and verifies its kernel cgroup before
opening any network connection. It never changes cgroup limits.

Tmpfs allocation is charged to its writer. Acquisition therefore requires
`memory.max = source_bytes + 4 GiB` (**59,880,994,926 bytes** for this plan),
instead of the old 4 GiB process allowance alone. The preparation planner now
includes this charge. These pages can remain charged after the process exits;
retain that cgroup until source files are released. Durable acquisition retains
the 4 GiB budget. Both modes preserve the 250 GiB shared-host memory floor.

The guard sums remaining source bytes and remaining aggregate control reserve
when directories share a filesystem. Different volumes are checked separately:
durable storage keeps its 150 GiB floor, tmpfs reserves its remaining payload,
and RAM reserves remaining tmpfs allocation above the shared-host floor. Existing
logs and receipts consume the same 1 GiB control budget; 256 KiB stays available
for the terminal event. It rechecks budgets, cgroup events and deadline at each
transfer or retained-file hashing chunk. Network reads use one receive per check
with a socket timeout of at most 30 seconds. These checks do not reserve shared
capacity or provide an external continuous supervisor.

Every source is checked against its pinned length and full SHA-256 or Git blob
identity. Exact HTTP range-resume is required; foreign entries, symlinks,
ambiguous files, corrupt completed files and unexpected response lengths/status
are refused. Failed partials remain unverified; no corrupt source is silently
replaced. The exclusive durable event reports source acquisition only, never
conversion, tensor correspondence or qualified weights.

Validation: **67 focused tests pass** across acquisition and preparation,
including network/range failures, retained-file corruption, root/non-kernel
cgroup refusal before network access, shared/separate volume accounting,
memory/disk/OOM/deadline loss and terminal-event space. Acquisition implementation
SHA-256: `434867a091c90ebcbf106d02a85100c0a95a0c9bdae9de284d22d1829461dfb4`.

The refreshed resource snapshot has **277,519,183,872 durable free bytes**,
**608,205,561,856 tmpfs free bytes**, and **1,155,408,687,104 host-available bytes**.
The process is in `0::/`, so execution remains unadmitted. No download, delegated
cgroup creation, conversion or model run was performed. Before actual launch,
add an external supervisor that survives worker OOM/SIGKILL and writes a failure
event, and implement receipt-validated source release. In-process exception
handling cannot guarantee an event if the kernel kills the entire worker group.
The matrix remains unpublished until matched outputs and the native floor qualify.


## External acquisition supervisor (2026-11-20)

`scripts/diagnostics/target-precision/acquisition_supervisor.py` is now the
acquisition entry point, taking the same six required arguments as the worker.
It remains outside the dedicated worker leaf and admits the leaf before launch.
It independently samples per-volume remaining source/control obligations, the
250 GiB host floor, cgroup memory events and the elapsed deadline at most every
second (default 250 ms), including while the worker blocks in network reads.
The worker retains its own checks. No shared resource capacity is reserved.

Before launch it preallocates a 256 KiB terminal receipt on durable controls.
It fsyncs the padded JSON, publishes by exclusive hard link, and fsyncs the
containing directory. A worker SIGKILL or leaf OOM therefore does not prevent
the parent writing FAILED. It captures one process group, escalates TERM to KILL,
and reaps the worker before publication. Success additionally requires exit zero,
a plan-bound COMPLETE worker event, source inventory/identity records and existing
complete source files. This source-only receipt does not qualify converted weights.
A host crash or death of the supervisor itself remains outside this guarantee;
an existing reserved file without the final event is incomplete, never success.

Validation: **81 focused tests PASS** across acquisition, preparation and the
supervisor. New tests include real child SIGKILL, parent-observed disk/host/OOM/
deadline failures with child reaping, root-cgroup admission refusal, changed-plan
refusal, and absent/foreign/incomplete/malformed completion receipts. Tests use
tiny files and synthetic workers; no weights, network transfer, real cgroup OOM,
conversion or inference ran. Supervisor SHA-256
`f09a89e0ce22f0edba5e3c3ef6f9662d68a952614c79d42ffb9ee9698ea7bb1f`;
test SHA-256
`6f5a135f07d60c57916111e53ab83f7fbe195197b9d3aa99640a90f7fd58908c`.

Receipt-validated task-owned source release is still unimplemented. A dedicated
configured leaf is still required and no live acquisition is admitted or launched.
The target-precision matrix remains unpublished.
