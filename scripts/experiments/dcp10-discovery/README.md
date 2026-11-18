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

The independent checker uses only Python finite-set arithmetic and the recorded pack plans; it does not import the application scorer:

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
