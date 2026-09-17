# 2026-09-16 — sub-preserve: making the closure audit's local-only work durable

Zero inference and no process management. No branch, index, or working tree was modified in any source
clone. Nothing was pushed to `main`. Source: `2026-09-16-sub-closure-audit.md`. Every item was
secret-scanned, and no credentials were found. The backup dir is
`/mnt/raid0/llm/backups/preserve-20260916/`, and its `README.md` has checksums and restore steps.

| # | Item | Action | Where it lives now |
|---|---|---|---|
| 1 | Research shared clone: local `main` 3 ahead of `origin/main` (and 340 behind). The commits are `1780fa7b` (on main as `56ef1404`) (INF-70 evidence + upstream patches, 37 files), `6ab403ed` (merge of origin/main), and `ae8e5ef9` (fix(autokernel): bound live anchor guard status). | Pushed the tip `ae8e5ef9` by refspec. The pre-push hook is LFS only, so no push lock was needed. `serialized_push.py` publishes the shared branch, so it was not used. Local `main` is unchanged (`ae8e5ef9`). **Finding:** all three commits were already on origin via `origin/lane/autokernel-status-bounding-20260914`, and `1780fa7b` is also on `origin/inf70/evidence-2026-09-08`. The audit's "not on origin" meant not on origin/**main**. | `pestopoppa/epyc-inference-research` `preserve/2026-09-16/research-local-main` @ `ae8e5ef9` (verified via ls-remote) |
| 2 | Hermes F `invoke_plugin_command`, local commit `532a49f1` in `/mnt/raid0/llm/hermes-agent` (NousResearch origin, no fork remote) | Wrote a thin bundle (prereq `e5691eed`, which is on upstream), a full self-contained bundle of `main`, and a format-patch. Both bundles pass `git bundle verify`. Also copied the untracked `HERMES.md`. | backup dir: `hermes-agent-532a49f1.bundle`, `hermes-agent-main-full.bundle`, `hermes-agent-532a49f1.patch`, `hermes-agent-HERMES.md.untracked` |
| 3 | K28.5a scaffold in `/mnt/raid0/llm/llama.cpp-k28-prototype-20260720` (HEAD `8bb53c52`, branch `k28/prototype-20260720`) | Read-only, with `GIT_OPTIONAL_LOCKS=0`. **Finding:** nothing is actually staged, so `git diff --cached` is empty. The doc is intent-to-add (` A`), and the `gated_delta_net.cu` hook is an unstaged change. The whole scaffold was captured as `git diff HEAD` (85 insertions, 3 deletions), which reverse-applies cleanly. The status, the untracked list (empty), and a copy of the doc were saved too. | backup dir: `k28-prototype-worktree-vs-HEAD.patch`, `k28-prototype-staged.patch` (empty), `k28-prototype-status.txt`, `k28-prototype-untracked.txt`, `k28-fused-chunked-gdn-prototype.md` |
| 4 | Z12 `docs/gdn2-low-rank-static-analysis-2026-08-25.md`, untracked in research | Copied verbatim. sha256 is `5c3f5a42…d792`. | backup dir |
| 5 | Other audit items | The AK-V27 `caa22f42` / `cffb98d3` commits are already on `origin/codex/autokernel-*`, so nothing was needed. `a4cb04ca8` exists in no clone, so there is nothing to preserve (the fix is a re-point). The NIB2-70 rescue is already on `origin/rescue/shared-clone-dirty-20260907`. SW-4 and W0 content is already on main. | n/a |

Not in the audit, noted only: the research shared clone still has 1,239 untracked entries, mostly
`artifacts/architect-27b-finetunes-v8-20260726/**` run logs. There are no modified tracked files. These
were not archived because they are out of the audit's scope.

Still open, for the owning sessions: commit K28.5a on an experimental branch, push Hermes F to a
pestopoppa fork, commit the Z12 doc in research, and reconcile research local `main` with origin/main.
