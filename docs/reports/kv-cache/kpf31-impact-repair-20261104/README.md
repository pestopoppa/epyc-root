# KPF-31 / KPF-32.IMPACT continuation

The original `kvfork31-p3-impact-20261102` ended rc1 during indexing, before
any of the three required impacts. Retained `out/analyze.stderr` shows repeated
worker idle/cumulative timeout, respawn-budget exhaustion, then native
`Napi::Error` / recursive terminate. No native upstream risk is captured.
The source-reference JSONL is preliminary only.

The installed GitNexus worker-pool source documents that workers=0 is a hard
configuration error; no sequential fallback exists. This continuation uses the
supported pool size 1, parse chunk concurrency 1, 128 KiB worker batches,
120-second idle and 600-second cumulative per-job timeouts. Full indexing runs
through the bound source wrapper with `--force`, `--skip-agents-md`,
`--skip-skills`, and `--workers 1`. It adds no graph exclusions or ignore changes.
The original default file-size policy is unchanged.

Impacts explicitly bind `--repo` to the exact experimental worktree. The status
command has no --repo option and runs from that tree. Missing/unknown risk,
ambiguous, errored, partial or truncated impact outputs fail closed. Only all
three captured results plus final source checks emit a nonpartial completion
record. HIGH/CRITICAL results must be surfaced by the owner before any source
edit. This row only indexes/queries; no benchmark or correctness claim follows.

The historical experimental candidate is explicitly pinned at
`c72ec82f5417bb2937310326120f149b665e8400` in the existing clean P3 worktree.
No production tree or source file is modified, and no checkout was copied.
`identity.json` binds wrapper, native source inputs, admission guard and policy.

Prepared runnable packet:
`/mnt/raid0/llm/tmp/kvfork/kpf31-p3-index-r2-20261104/spec.json`.
It retains lineage `kvfork31-p3-impact` and discloses the three superseded
qualification failures, subsequent PASS, and original rc1; the new ID does not
reset that history. Preparation follows the latest explicit operator readying
instruction; the owning session publishes and runs its smoke. The handoff task
is `handoffs/active/kv-cache-program.md:KPF-32.IMPACT`.

Offline checks passed: four policy unit tests, Python compile, shell syntax,
and `job.py --check` (HEAD/cleanliness/input hashes, no GitNexus indexing).
No indexing, qualification, publication or model inference was run here.
