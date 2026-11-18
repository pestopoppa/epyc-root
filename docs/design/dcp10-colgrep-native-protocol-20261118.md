# DCP-10 fixed-cohort native ColGREP diagnostic

The question is whether ColGREP retrieves gold files and lines that the original lexical pilot
missed, and whether the unchanged packer preserves those hits at 2k/4k/8k estimated tokens.
Higher file/line macro precision, recall and F1 means greater overlap. This is a three-task
instrument diagnostic, with up to 33 percentage points of macro recall from one task; it cannot
support population-quality, latency, production-enablement or full DCP-10 conclusions.

## Prospective identities and comparison

Use the original pilot request SHA-256
`5a42163d7262dcbe1fa6e7ff6daf870c74070b58b9d7fc4da684981f292a37db`
and lexical predictions SHA-256
`64088e7ac17ea1f8228f69aa68465b48c171037311f1b4a14ec535b93f1d077a`.
All three task identities, queries, base commits and dispositions come from that request.
The application remains `072d1583b3ead7456731946cd4e4595da6a9877f`; neither the lexical
producer nor its outputs change. Do not apply the separate match-anchor candidate.

The retrieval binary is ColGREP 1.2.0, SHA-256
`833e52aa6c40d090142fa132e3c75d3e792a4707474682a2496e3471f646f956`.
Use local LateOn-Code-edge revision `07ef20f406c86badca122464808f4cac2f6e4b25`.
Stage binary, model and runtime before publishing; bind their actual byte identities then.
Do not hash model weights inside a compute grant. No downloads occur inside native execution.

Use each unchanged query once, top-k 20, maximum eight files, alpha 0.95 and CPU-only retrieval.
Record raw returned hits, application discovery/candidate costs and actual rendered pack spans.
Keep failed and empty tasks in every applicable denominator. Record FULL as all source lines,
SLICES as retained source ranges, CODEMAP as file coverage without line coverage and EXCLUDED
as no coverage. Independently reconcile the scorer against those actual render plans.

## Index and launch admission

Private index construction is inference and runs only in a published allocator row or its native
publisher smoke. Bind each completed index to its original task, canonical base path, commit/tree,
query, binary, model and index payload before searching. A changed or missing binding refuses
retrieval. No production index or ambient configuration is visible to the child.

Native retrieval requires validated operating-system isolation: source, index payload, model,
binary and runtime are read-only, networking is disabled, and CPU affinity follows the grant.
The released vector loader lazily materializes merged code and residual arrays. Complete this
materialization during the writable private build phase, using the pinned source's chunk layout, padding and manifest rules, a source-backed load
operation, or one fixed build-only warmup query unrelated to any cohort task. Retain that operation and its
native output as build evidence. It is not a scored retrieval or a replacement task. Seal only
after materialization and SQLite checkpointing finish; the exact original task query still runs
once against read-only payloads. Init plus materialization shares the build deadline.

Writable scratch during scored retrieval may hold disposable process coordination files, never
model/index payload or source changes. Any CLI-required coordination exception must be narrow, source-backed and
verified by the native smoke. Permission bits alone do not establish immutability.

The smoke must perform a bounded real index build and retrieval on a separate qualification
fixture with the same isolated launch. Fixture output is qualification evidence, not an official
cohort observation. Official work uses fresh output directories and never consumes smoke output.

## Checkpoints and stop rules

Checkpoint each task attempt and retain failed/empty outcomes without replacements. Stop after
three attempts, at the first source/isolation admission failure, allocator STOP or 1,800 seconds.
No retry changes an outcome. Seal each index before searching and verify its protected payload
is unchanged afterward. A completed task is an observed attempt; success requires separately
valid retrieval and reconciliation. Missing or refused work remains UNKNOWN.

The original shared-scratch custody refusal and trusted-packer-source mismatch persist. Local
hashes and reconciliation do not repair capture custody or admit a trusted measurement source.
The existing `VB-CONTEXTBENCH-DISCOVERY-WIRE` covers this diagnostic; retain native failures and
source identities for that adapter rather than inventing a retrospective measurement warrant.

## Launcher source and admission evidence

The [retained launch-admission record](../research/dcp10-colgrep-launch-admission-20261118.json)
binds the release source, binary, runtime and container image, seven mocked controls and a
non-inference confinement probe. ColGREP 1.2.0 always opens its project lock during search.
The adapter holds a disposable file mounted over that lock, selecting the release branch that
skips reindexing; all canonical index payload stays read-only. The SQLite payload has checkpointed
WAL/SHM sidecars prepared after the sole index writer closes, before its content binding.
The retained record separately identifies publisher qualification on a fresh model-backed fixture.
The source review and synthetic SQLite probe alone do not establish native retrieval success;
fixture qualification establishes no official cohort observation.

## Infrastructure-fix revision after the original row

The original row completed its three attempts but every build failed with Rust
thread-spawn EAGAIN; its comparison is invalid. Preserve that result and all error
rows. A separately sealed revision tests whether bounded native threading lets the
same three tasks complete index construction and immutable retrieval. This is an
infrastructure qualification, with no task replacement or automatic retry.

The pinned NextPlaid encoder starts a scoped thread for every prepared batch when
multiple ONNX sessions exist (`next-plaid-onnx/src/lib.rs`,
`encode_prepared_document_batches`). One session takes its serial branch. The
revision therefore supplies the released ColGREP configuration
`parallel_sessions=1` through a private read-only configuration file, bounds the
other native thread pools, and limits the child affinity to at most four CPUs from
the allocator grant. It retains the 256-PID limit, model/binary pins, original
queries, search/file caps and pack budgets. A small successful smoke alone cannot
show that the original multi-batch failure is fixed on the cohort.

The new row's predicate requires both three completed attempts and
`comparison_valid == 1`. Thus a completed set of error rows cannot pass the
comparison predicate. The question is answered by three retained attempts; stop at
the first source/isolation failure, allocator boundary or the existing 1,800-second
cap. All failures and unresolved tasks remain visible. This finite revision does
not estimate population quality or resolve source/custody admission. Native graph
scoring still requires valid, admitted and sealed ColGREP seed outputs.
