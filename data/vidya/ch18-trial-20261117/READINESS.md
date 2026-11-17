# VB-CH18-MERGE-TRIAL-WIRE prospective producer

Native producer: `scripts/vidya/producers/ch18_merge_trial.py`.
Existing reader: `scripts/vidya/adapters/ch18_merge_trial.py`.

The historical 2026-11-05 inventory has no native producer in this lane. The new runner executes one explicit `git merge -s ort --no-commit --no-ff` in a temporary detached worktree belonging to an independent disposable clone inside this lane. It binds full commits, Git version, conflict paths/counts, UTC completion, state and observed cleanup into the existing sealed v1 schema. It never fetches, builds, reconciles, promotes, deploys or retrofits historical evidence. Failure/incomplete records project nothing. Git environment overrides are stripped, hooks/rerere disabled, external clone/common directory and linked worktree use refused. Existing output records are never overwritten. Publication fsyncs the complete temporary JSON, atomically links it without replacement, then fsyncs its containing directory. Cleanup aborts any active merge and uses normal `git worktree remove` without force; cleanup refusal produces an incomplete record and no projected claim.

Original approved pair, for a NEW prospective reproduction only:
- production base `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`
- upstream tip `4e201388c319fc9f747fbe6a666793e2dc2a6d8e`

The caller must first supply an independent disposable clone under this lane with both exact commit objects. An input linked worktree whose common Git directory belongs to the canonical production repository is intentionally refused: creating/removing its child worktree would mutate the canonical repository's worktree registry, violating this assignment's lane-only write boundary. The runner itself performs the required `git worktree add --detach` source preparation inside the independent lane clone; the merge never edits the original source working tree or its Git metadata.

The authorized source-preparation command, when the owning session chooses to run the prospective trial, is:

```bash
git clone --no-local --no-checkout /mnt/raid0/llm/llama.cpp artifacts/compute/ch18-disposable-clone
git -C artifacts/compute/ch18-disposable-clone checkout --detach ffc1bac82eeca6f9099e1ccd9ba49703c460a115
git -C artifacts/compute/ch18-disposable-clone cat-file -e 4e201388c319fc9f747fbe6a666793e2dc2a6d8e^{commit}
```

`--no-local` transfers objects through Git's read-only upload-pack path without source metadata writes or hardlink sharing. Missing upstream objects must be sourced explicitly by the owning session; no implicit fetch or substituted commit is allowed. Equivalent approved preparation was executed from `/mnt/raid0/llm/llama.cpp-experimental` into ignored `tmp/ch18-source-20261117`; source repositories were read only. An independent lane clone and one new prospective original-pair trial were subsequently executed under explicit owner authorization; see execution receipt below. A newer fresh-production pull must explicitly pin its actual upstream tip; the historical upstream ID is not called current.

Example after that prerequisite is satisfied:

```bash
python3 scripts/vidya/producers/ch18_merge_trial.py \
  --repo artifacts/compute/ch18-disposable-clone \
  --production-base ffc1bac82eeca6f9099e1ccd9ba49703c460a115 \
  --upstream-tip 4e201388c319fc9f747fbe6a666793e2dc2a6d8e \
  --output artifacts/compute/ch18-prospective/merge_trial.json
```

Validation: `python3 -m pytest -q tests/vidya/test_ch18_merge_trial_producer.py tests/vidya/test_ch18_merge_trial_adapter.py` => 22 passed. Tiny real Git repositories exercised conflicted and clean merges, exact inventory, cleanup, unchanged clone HEAD/status, reader projection, cleanup-refusal suppression and atomic output overwrite refusal. These are synthetic controls only, not evidence about CH-18. `git diff --check` passed.

No planning-context canary was run; process is not yet called wired. No live ledger writes, grants or compute row publication. This is a small filesystem merge trial, not an inference workload; publishing a large compute row would be inappropriate.

GitNexus status and upstream impact both report no indexed repository. Manual blast radius: two new files; imports existing reader and seal unchanged; no shared grader, adapter schema, production kernel or caller edits. Risk is limited to explicit execution against caller-provided lane-local disposable clone. Owner should perform indexed review before integration if an index becomes available.

Owner-applied source-table wording (existing CH-18 row, no new grading ladder):
`Prospective native runner scripts/vidya/producers/ch18_merge_trial.py prepares epyc.ch18_merge_trial.v1 records in an independent lane-local disposable clone. Original-pair prospective workload completed; planning-context canary remains unrun; historical conflicts.json remains refused.`

Owner-applied handoff annotation (keep original checkbox open):
`2026-11-17: prospective native producer prepared; two real tiny-Git controls and existing adapter negatives pass (22 tests). Original-pair prospective CH-18 trial subsequently completed (98 conflicted paths, full cleanup); planning-context canary still required. No retrospective warrant or production mutation.`

Reader seam hardening: a shared eligibility predicate now gates both native_rows and direct project calls. Resealed incomplete/failed states, complete records with worktree removal false, and conflicted records without successful merge abort yield no count tuple. Structurally valid native outcome records remain unchanged; zero-conflict up-to-date merges need no abort. Tests include direct-project bypass negatives and the legitimate zero-conflict case. Shared grade unchanged.

## Prospective original-pair execution

At `2026-11-17T19:40:31Z`, one new merge trial of the exact original pair completed with 98 conflicted paths. Both merge abort and normal worktree removal succeeded. Disposable clone remained clean at detached production base, with no leftover trial worktree. No external source metadata/working-tree writes, fetch, build, inference, promotion or canonical ledger edits.

Native record: `data/vidya/ch18-trial-20261117/merge_trial.json`.
File SHA256: `62ef9e0f2ddec3ef31c9dbf9c70a01add60c0b14273b806e82cf269fdb017f79`.
Native seal: `f51819c730a975081eebcd915c8c936c3c1a3249be4c734b2efcd12c5f46f206`.
Receipt: `data/vidya/ch18-trial-20261117/receipt.json`.
Dry-run ingest: exit 0, one row projected, zero refused, three frames; explicit unused lane ledger not created. Dry-run stdout/stderr and projected frames retained beside receipt. No planning-context canary: source remains open until that succeeds. This inventory establishes no build, champion reconciliation or promotion verdict.

Final safety review: supplied clone and newly created worktree must each report a Git top-level resolving exactly to the intended lane path. Redirected core.worktree is refused before trial worktree creation; unverified trial worktrees are preserved as incomplete without abort/removal commands against an unverified working directory. Nonzero Git status is rejected. External core.worktree negative control passed; original workload was not rerun after this review.

## Planning consumer acceptance (2026-11-17)

The native record now passes the real `AgentPlanner.propose` → `belief_context.prepare` → child reader path, intercepted before an actor backend call. The scratch-ledger canary displays both original full commit IDs, the 98-path inventory, cleanup and limitations as consumer-scoped harness context at `Judged/Located`. It excludes the observation from model evidence and reliance IDs; the actor receipt rejects attempted reliance, and another consumer sees no claim. Receipt and excerpt: `../ch18-context-canary-20261117/`. Replay: `scripts/vidya/canary/ch18_context.py`. No canonical ledger write, trial rerun, inference, current-upstream, build or promotion result follows.
