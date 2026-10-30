# Codex3 persistent editing lanes

Operator instruction,2026-10-30: reuse one checkout per lane and remove each temporary task worktree when its work lands. Do not create further per-task checkouts.

| Lane | Checkout in host namespace | Git admin visible in both namespaces |
| --- | --- | --- |
| Root | `/mnt/micron/codex3-lanes/root` | `/mnt/raid0/llm/tmp/codex3-lane-git/root.git` |
| Research | `/mnt/micron/codex3-lanes/research` | `/mnt/raid0/llm/tmp/codex3-lane-git/research.git` |

Source edits, status, staging and rebases use the authorized host UID1000 bridge. Origins are the canonical GitHub remotes; object alternates reference the canonical repository stores. The lane guide at `/mnt/raid0/llm/tmp/codex3-lane-git/README.md` records the exact bridge commands.

Before any fetch/rebase/push sequence, acquire the canonical repository's serialized push lease: root key2431-96604699 or research key2431-96371209. A private clone's common directory has a different identity and its own lease does not serialize other workers. Metadata-only authenticated Git read/network commands may use the private `--git-dir` with the temporary `--work-tree=/dev/shm` override; never stage, reset, clean or inspect worktree status using that override. Review exact outgoing commits, push without force and verify the remote carries HEAD, then release the canonical lease.

For temporary linked trees already present: land or explicitly abandon unique work; archive ignored evidence and preserve required runtime source in a verified capsule; remove stale active handoff/launcher references without rewriting historical evidence; run `python3 scripts/system/worktree_gate.py check <path>` and `remove <path>`. Never force removal, prune worktree registrations or run Git GC for cleanup. Preserve branch refs and restore records.
