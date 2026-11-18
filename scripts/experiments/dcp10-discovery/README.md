# DCP-10 task-root lexical pilot

This zero-decode pilot asks whether three real ContextBench tasks can pass through the current
orchestrator's task-root lexical discovery, budget packer, and macro file and line scorer with
reconcilable source-line provenance. Each language contributes one third of the aggregate.
A single task can move a macro fraction by up to 33 percentage points. The pilot can distinguish
working instrumentation from absent, malformed, or inconsistent evidence. Its sample size cannot
resolve a language, budget, or retrieval-arm comparison.

## Pinned inputs

The Hugging Face dataset revision
[`c2855792b006af41c67202d33883fb9d46362853`](https://huggingface.co/datasets/Contextbench/ContextBench/tree/c2855792b006af41c67202d33883fb9d46362853/data)
is byte-identical for both selected artifacts to the
[companion repository at `1436c28a8eb95496da4ea69ad458b9f8a8eb7d61`](https://github.com/EuniAI/ContextBench/tree/1436c28a8eb95496da4ea69ad458b9f8a8eb7d61/data).
The full release is SHA-256 `2f56535bdc73eb8a68bf4ebb49789d8e9cd4f219ea60df6290b85278aee61ca8`
(1,136 IDs). Lite is SHA-256 `e9dcfd504cbfb849ac815a79040c793d0d92f94eecc9b5a4ee3e1445a2f8a791`
(500 IDs). All projected Lite inputs match their full-release rows. The pilot picks the minimum SHA-256
of the UTF-8 instance ID in each declared stratum, before running discovery or looking at predictions.

| Stratum | Population | Instance ID | Base repository and commit |
| --- | ---: | --- | --- |
| Lite Python | 266 | `SWE-Bench-Verified__python__maintenance__bugfix__cb2c6ff3` | [xarray `51d37d1be95547059251076b3fadaa317750aab3`](https://github.com/pydata/xarray/commit/51d37d1be95547059251076b3fadaa317750aab3) |
| Full C | 68 | `Multi-SWE-Bench__c__maintenance__bugfix__2687f1e4` | [zstd `517d8c984ce9b30792fe5b6c8c79547d3748f34d`](https://github.com/facebook/zstd/commit/517d8c984ce9b30792fe5b6c8c79547d3748f34d) |
| Full C++ | 60 | `Multi-SWE-Bench__cpp__maintenance__bugfix__1ec2c84a` | [fmt `8d9d528bf52c60864802844e8acf16db09dae19a`](https://github.com/fmtlib/fmt/commit/8d9d528bf52c60864802844e8acf16db09dae19a) |

Orchestrator source is pinned at `072d1583b3ead7456731946cd4e4595da6a9877f`. Discovery receives
only `problem_statement`, unmodified. The task root is the detached checkout and the runner checks
for escaping symlinks. The lexical call uses the application's `_code_search` and
`discover_candidates` with a search limit of 20 and a file cap of eight.

The runner writes the selected gold projection and dispositions before discovery. It strips only
known repository prefixes from container-absolute paths, preserves dotfiles, and flags unresolved
relative paths against each pinned Git tree. The full release contains three empty-gold task IDs
and 42 task IDs with a bare `/workspace/` path. The audit artifact keeps both ID lists. Each of the
three selected tasks had usable gold with all paths present. The third-party count of 88
tasks with unresolvable paths remains unverified across the release. No Symbol or EditLoc scores
are produced. [Upstream path audit](https://github.com/EuniAI/ContextBench/issues/3)

## Reproduce

Use a fresh private directory under the owner-approved RAID scratch path. The existing run is
available at `/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10`. Acquire release bytes before
the run. Use a fresh bare cache for each external repository, a depth-one SHA fetch, and a detached
linked worktree for each base and the companion repository.

```bash
export CONTEXTBENCH_TMP_ROOT=/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10-replay
p=$CONTEXTBENCH_TMP_ROOT
app=/mnt/raid0/llm/epyc-orchestrator
mkdir -m 700 "$p"
mkdir -p "$p/source" "$p/bases" "$p/cache" "$p/tmp"
export TMPDIR="$p/tmp"
dataset=https://huggingface.co/datasets/Contextbench/ContextBench/resolve/c2855792b006af41c67202d33883fb9d46362853/data
curl -fL --max-time 90 "$dataset/full.parquet" -o "$p/source/full.parquet"
curl -fL --max-time 90 "$dataset/contextbench_verified.parquet" -o "$p/source/lite.parquet"

checkout() {
    local name=$1 url=$2 rev=$3 output=$4
    git init -q --bare "$p/cache/$name.git"
    git -C "$p/cache/$name.git" -c fetch.fsckObjects=true fetch --depth=1 --no-tags "$url" "$rev"
    git -C "$p/cache/$name.git" -c core.hooksPath=/dev/null worktree add --detach "$output" "$rev"
}
checkout upstream https://github.com/EuniAI/ContextBench.git 1436c28a8eb95496da4ea69ad458b9f8a8eb7d61 "$p/source/upstream"
checkout xarray https://github.com/pydata/xarray.git 51d37d1be95547059251076b3fadaa317750aab3 "$p/bases/python"
checkout zstd https://github.com/facebook/zstd.git 517d8c984ce9b30792fe5b6c8c79547d3748f34d "$p/bases/c"
checkout fmt https://github.com/fmtlib/fmt.git 8d9d528bf52c60864802844e8acf16db09dae19a "$p/bases/cpp"
git -C "$app" worktree add --detach "$p/app" 072d1583b3ead7456731946cd4e4595da6a9877f

pilot=scripts/experiments/dcp10-discovery/pilot.py
UV_CACHE_DIR="$p/cache/uv" uv pip install --python "$(command -v python3.14)" --target "$p/deps" pyarrow==22.0.0
PYTHONPATH="$p/deps" python3.14 -B "$pilot" "$p" prepare
sha256sum "$p/packet/request.json"
read -r seal _ < <(sha256sum "$p/packet/request.json")
timeout 90 "$app/.venv/bin/python" -I -B "$pilot" "$p" run --request-sha "$seal" --output "$p/pilot"
```

The independent checker uses Python finite-set arithmetic and the recorded pack plans. It also
checks the disposition ledger against the score denominator and includes failed and empty attempts.

```bash
python3 -I -B scripts/experiments/dcp10-discovery/verify_pilot.py "$p"
```

The [retained result metadata](../../../docs/research/dcp10-lexical-pilot-results-20261118.json) binds the original packet, discovery, score and run digests.

The run writes one checkpoint per eligible task and stops after the three planned attempts. The
90-second cap bounds the run. Checkout, discovery, and empty-output failures preserve their
denominator entries. A broken input or source seal stops the run. There are no replacements.
Under `pilot/`, `predictions.jsonl` records discovery outputs and candidate costs,
`discovery.jsonl` records raw lexical hits and actual packer entry modes and ranges at each
budget, and `score-request.json` binds the pre-score inputs. Each budget output records the
application's rendered text digest and its separate render mode. Codemap-only files contribute file
coverage with zero source-line spans. Budget costs are the application's conservative character
estimates. `run.json` identifies the output bytes.

## Observed pilot

The three attempts ran in 2.990 seconds. All returned eight discovered files and none failed.
Higher values indicate greater overlap with ContextBench gold. The observed file and line scores
are macro-averaged across these three rows.

| Scope | File R | File P | File F1 | Line R | Line P | Line F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Discovery | 0.722222 | 0.208333 | 0.321212 | 0.024534 | 0.088299 | 0.038153 |
| Packed 2,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Packed 4,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Packed 8,000 | 0 | 0 | 0 | 0 | 0 | 0 |

The 2,000 and 4,000 plans included zero files. The 8,000 plan included only the fmt file
`doc/python-license.txt`, at 4,269 estimated tokens with no gold overlap. All eight xarray
candidates used full-file costs for both full and slice modes. Their cheapest full-file estimate
was 24,738 tokens. The packer disallows codemap fallback for these range-bearing candidates.
Pack and render modes
agreed for all 72 entries. An independent finite-set recomputation reconciled all 12 task/scope
counts and 24 macro metric values against the recorded discovery and packer plans. The pinned app
passed 91 targeted tests.

The scores are diagnostics. The existing capture producer rejected the group/world-writable
ancestor `/mnt/raid0/llm/tmp` (exit 2). The verifier also pins an older packer byte identity.
The [source review](../../../docs/research/dcp10-packer-custody-review-20261118.json) records the
behavioral difference. The original refusal, local evidence hashes, source-backed inputs, and
independent check stay in the owner scratch directory. This run establishes no verified score
receipt or full-cohort result.

## Second lexical shard

DCP-10-P2 took the second SHA-256 rank in each original stratum, with the same app, release,
search, scoring, and pack-budget pins. The question was whether the original instrumentation
and zero packed overlap would recur on the next three preselected tasks. A single task can
move a macro fraction by 33 percentage points. The rule was to stop after the three selected
attempts or at 90 seconds, with no substitutions.

| Stratum | Instance ID | Base repository and commit |
| --- | --- | --- |
| Lite Python | `SWE-Bench-Pro__python__maintenance__bugfix__739b23db` | `ansible/ansible` at `252685092cacdd0f8b485ed6f105ec7acc29c7a4` |
| Full C | `Multi-SWE-Bench__c__maintenance__bugfix__0dde5323` | `ponylang/ponyc` at `764110c805d8020f5202c60ffed2b2570caf792a` |
| Full C++ | `Multi-SWE-Bench__cpp__maintenance__bugfix__2c49ef99` | `fmtlib/fmt` at `c03f55ec3a0511611fa7f0537f858544a0ed03bd` |

For replay, start with a fresh private scratch directory `p` and prepare the same dataset and
companion inputs and detached app as above. Set `prior` to the original `packet/request.json`.
`select` verifies the released inputs and predecessor task identities before listing the next
checkouts in language, URL, commit, and task ID order.

```bash
PYTHONPATH="$p/deps" python3.14 -B "$pilot" "$p" select --previous-request "$prior" > "$p/selected.tsv"
```

Fetch each listed commit by exact SHA into its bare cache and add its detached linked worktree
at `"$p/bases/$language"` before preparing the packet. An existing bare cache can serve more
than one linked worktree. `prepare` seals the predecessor request digest and selection rank
alongside the usual source, disposition, and dataset identities.

```bash
PYTHONPATH="$p/deps" python3.14 -B "$pilot" "$p" prepare --previous-request "$prior"
sha256sum "$p/packet/request.json" > "$p/REQUEST.sha256"
read -r seal _ < "$p/REQUEST.sha256"
timeout 90 "$app/.venv/bin/python" -I -B "$pilot" "$p" run --request-sha "$seal" --output "$p/pilot"
python3 -I -B scripts/experiments/dcp10-discovery/verify_pilot.py "$p"
```

All three tasks had resolved gold and returned eight files each in a 5.469-second run. Macro file
recall, precision, and F1 at discovery were 0.177778, 0.083333, and 0.111888. Discovery line
metrics and all packed metrics were zero. Actual pack plans had zero file inclusions at 2,000,
one at 4,000, and three at 8,000 estimated tokens. Independent recomputation reconciled 12
task-scope counts, 24 macro metric values, and all actual entry modes and budgets. These three
tasks provide a local diagnostic and share the original custody and packer identity limitations.
The original artifacts are at `/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10-shard2`.
[Retained shard metadata](../../../docs/research/dcp10-lexical-shard2-results-20261118.json)

## Third lexical shard

DCP-10-P3 took the third SHA-256 rank in each original stratum. It used the same released bytes,
orchestrator revision, discovery and packer bytes, scoring, and budgets as shard two. The request
bound the shard-two request digest before execution. Replay the second-shard commands above
with shard two's `packet/request.json` as `prior`. The run stopped after the three preselected
attempts under a 90-second cap, with zero decodes and zero substitutions.

| Stratum | Instance ID | Base repository and commit |
| --- | --- | --- |
| Lite Python | `SWE-Bench-Verified__python__maintenance__bugfix__1d90db61` | `astropy/astropy` at `1a4462d72eb03f30dc83a879b1dd57aac8b2c18b` |
| Full C | `Multi-SWE-Bench__c__maintenance__bugfix__1e842312` | `ponylang/ponyc` at `f00f95b30dd68c7faaff0aa88508c218bc19f02b` |
| Full C++ | `Multi-SWE-Bench__cpp__maintenance__bugfix__5a3de72a` | `nlohmann/json` at `9294e25c98f9c09a1874842dbcaae7a91336a57e` |

All three tasks had resolved gold and returned eight files each in 8.939 seconds. Discovery macro
file recall, precision, and F1 were 0.416667, 0.083333, and 0.129630. Discovery line metrics were
zero. The packer included zero files at 2,000, 4,000, and 8,000 estimated tokens, so all packed
metrics were zero. Independent recomputation reconciled 12 task-scope counts, all 24 macro metric
values, and pack and render modes for all 72 entries.

The local request SHA-256 is `c0fea8996fd1894af83dd7512d230dc696c6a133790472c078a4f6fb5c0a6176`.
The three tasks provide diagnostic evidence under the existing writable-ancestor and trusted
packer identity limits. Accepted score receipts for this shard number zero. Raw evidence is at
`/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10-shard3`.
[Retained shard metadata](../../../docs/research/dcp10-lexical-shard3-results-20261118.json)

## Cost provenance across the three retained shards

The offline replay reproduced 72 candidate records and 216 pack/render entries across all 27
plans using the pinned app, exact task bases, and the pilot's Python interpreter (3.11.17).
All 72 candidates carried hit ranges and had equal FULL and SLICES estimates. The 54 non-Python
candidates took the whole-file fallback. All 18 Python files parsed successfully, but each padded
lexical window contained at least one line with no enclosing selectable AST statement. The slicer
rejects the whole window at that line. For example, the retained window for `xarray/core/dataset.py`
covers lines 1–21, and line 2 is blank. No candidate produced an AST slice, and the equal estimates
all came from explicitly assigning the FULL estimate to SLICES. The replay confirmed that every
costed FULL or codemap block matched the individual render byte-for-byte after accounting for the
estimator's two trailing newlines. [Lexical windows](https://github.com/pestopoppa/epyc-orchestrator/blob/072d1583b3ead7456731946cd4e4595da6a9877f/src/repl_environment/code_search.py#L155-L217)
[AST selection, costing and rendering](https://github.com/pestopoppa/epyc-orchestrator/blob/072d1583b3ead7456731946cd4e4595da6a9877f/src/context_discovery.py#L178-L480)
[Pinned xarray example](https://github.com/pydata/xarray/blob/51d37d1be95547059251076b3fadaa317750aab3/xarray/core/dataset.py#L1-L21)

All nine discovered gold-file candidates exceeded the entire 8,000-token estimate in their
permitted modes. Earlier greedy placements excluded zero otherwise eligible candidates. The
range-bearing evidence rule blocked fitting codemap estimates for 7, 12 and 18 excluded candidates
at the three budgets. The packer admitted 0, 1 and 4 files at 2,000, 4,000 and 8,000 estimated tokens
respectively across the nine tasks, with zero gold-file inclusions. [Packer policy](https://github.com/pestopoppa/epyc-orchestrator/blob/072d1583b3ead7456731946cd4e4595da6a9877f/src/context_assembly.py#L325-L416)
[Retained cost report](../../../docs/research/dcp10-cost-diagnostic-20261118.json)

The diagnosed interface issue is that Python lexical preview padding is passed as required AST hit
lines. A focused follow-up would carry matched source lines separately from preview windows and
use the matched lines as the lexical slice anchors. If any required anchor lacks an AST statement,
keep the whole-file fallback and explicitly exclude the candidate when it exceeds the budget.
Keep the existing codemap restriction so included spans still locate actual source evidence.
The original capture refusal and trusted packer identity mismatch still apply.
[Custody source review](../../../docs/research/dcp10-packer-custody-review-20261118.json)

To replay locally against the retained directories, choose a new output path outside the three
shards.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B \
  scripts/experiments/dcp10-discovery/diagnose_costs.py \
  /mnt/raid0/llm/tmp/delegation-context-preassembly \
  --output /mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10-cost/replay.json
```

## ColGREP admission and mocked comparison

`colgrep_compare.py` uses the three included tasks from the original sealed lexical
request, in request order. The original lexical predictions are the paired baseline.
The packet, app source and baseline bytes are checked against their original seals.
The app's discovery, packing and scoring modules are loaded directly from verified
source bytes. The current pilot helper has its own digest in the comparison config;
the original request retains the digest of the producer that wrote that request.

Stage assets in a canonical, caller-owned directory with mode `0700`, outside the
lexical pilot. The admission CLI expects this layout:

```text
config.json
bin/colgrep
model/
bases/{python,c,cpp}/colgrep/indices/<one project>/
    project.json
    state.json
    index/metadata.json
    index/<payload files>
```

Use `epyc.dcp10.colgrep-comparison.v1` as the config schema. The top-level fields
are `schema`, `arm`, `pilot_request_sha256`, `lexical_predictions_sha256`,
`app_revision`, `runner_sha256`, `pilot_helpers_sha256`, `binary_sha256`,
`model`, `limit`, `max_files`, `budgets`, `alpha`, `timeout_s` and `tasks`.
The fixed values live in `colgrep_compare.py`. The model binds `id`, `revision`
and `directory_sha256`. Under `tasks`, each included task ID binds
`base_commit`, `base_tree`, canonical checkout `root`, `query_sha256`,
`app_revision`, `binary_sha256`, `model_revision`, `model_directory_sha256`
and `index_data_sha256`. Compute directory digests with `directory_digest()`
over the exact staged path and file contents, including hidden files.

```bash
python3 -I -B scripts/experiments/dcp10-discovery/colgrep_compare.py \
  "$pilot_work" "$private_assets" --config-sha "$prospective_config_sha256"
```

This CLI performs admission only and reports `native_execution: disabled`. It
checks a clean base tree, the native project's recorded checkout root, private
index layout and sealed payload bytes. These checks establish agreement with the
supplied config. A newly sealed digest alone cannot establish when or how the
index was built. The CLI does not open a production index or launch ColGREP.
Native comparison additionally requires a validated immutable launch and an
independent binding of its inputs to the index build.

The `compare(..., search=mock_search)` entry point uses a caller-supplied callback
in an isolated Python process. It supplies prepared argv, exact checkout path,
private data home and the 10-second timeout value. The original query, 20-hit
limit, eight-file cap and 2,000/4,000/8,000 estimated-token budgets are fixed.
It rejects malformed hits, paths outside the root and paths absent from the
pinned tree's regular files. It measures line bounds on selected source files.
Failed admission, failed search and empty search each retain their original task
in the comparison denominator. Each actual render plan records planned and
rendered modes, rendered file and line spans, charged estimates, reasons and
content identities. The scorer's packed scopes are computed from candidate costs.
Actual rendered evidence is available separately in the plan records.

Run the mocked controls against the retained original pilot. Set
`DCP10_TEST_PILOT` to its canonical path when using a different location.

```bash
python3 -B -m unittest discover -s scripts/experiments/dcp10-discovery \
  -p 'test_colgrep_compare.py' -v
```

The controls use the original sealed cohort and pinned application with synthetic
binary, model and index files. This preparation establishes no retrieval quality,
index custody, receipt or completed comparison arm.

## Native isolated ColGREP packet

The [native protocol](../../../docs/design/dcp10-colgrep-native-protocol-20261118.md)
fixes the same three tasks and original application. `prepare_colgrep_native.py`
stages the binary, local model and ONNX runtime into a fresh private RAID root,
hashes model bytes once and seals sources plus the preparation receipt. Its
default retained root is
`/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10-colgrep-native`.
The staged `spec.json` is published through `publish_row.py --smoke-now`; only that
publisher smoke may run the separate qualification fixture in the owner turn.
Official index construction and retrieval require the allocator row.

After a source repair, refresh the existing source packet without repeating model
preparation:

```bash
python3 -I -B scripts/experiments/dcp10-discovery/prepare_colgrep_native.py --refresh-sources
```

The refresh archives previous source bytes and controls, updates source/receipt
pins and preserves asset identities and observed outputs. It never clears a
failure, edits a grant or resumes an official attempt. Runtime checks the
prospectively sealed receipt and immutable asset metadata; these checks are drift
guards tied to the original content digest, not a new model-content or capture
custody proof.

Native init produces chunked vectors. Before sealing, `colgrep_native.py`
materializes the release's lazy merged arrays using its exact chunk concatenation,
zero padding, NPY headers and manifest format, then checkpoints SQLite sidecars.
This deterministic build step adds no model query. Retrieval uses a held
disposable project lock to skip reindexing and keeps every canonical payload
read-only. The row independently reconciles actual rendered file/line coverage
with the scorer, retaining empty and failed attempts. Missing tasks remain UNKNOWN.
Preparation, qualification and official cohort outcomes remain separate.
