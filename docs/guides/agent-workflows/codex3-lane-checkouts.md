# Codex3 persistent editing lanes

Operator instruction,2026-10-30: reuse one checkout per lane and remove each temporary task worktree when its work lands. Do not create further per-task checkouts.

| Lane | Checkout in host namespace | Git admin visible in both namespaces |
| --- | --- | --- |
| Root | `/mnt/micron/codex3-lanes/root` | `/mnt/raid0/llm/tmp/codex3-lane-git/root.git` |
| Research | `/mnt/micron/codex3-lanes/research` | `/mnt/raid0/llm/tmp/codex3-lane-git/research.git` |
| Orchestrator | `/mnt/micron/codex3-lanes/orchestrator` | `/mnt/raid0/llm/tmp/codex3-lane-git/orchestrator.git` |
| NEMO experimental source | `/mnt/micron/codex3-lanes/nemo-kernel` | `/mnt/raid0/llm/tmp/codex3-lane-git/nemo-kernel.git` |
| KPF experimental source | `/mnt/micron/codex3-lanes/kpf-kernel` | `/mnt/raid0/llm/tmp/codex3-lane-git/kpf-kernel.git` |

Source edits, status, staging and rebases use the authorized host UID1000 bridge. The original nine linked task trees have been removed; the rows above are the declared reusable active lanes. Their object alternates reference canonical stores, so do not duplicate source or model payloads. Root, research and orchestrator use their canonical GitHub remotes. The two kernel source lanes are experimental: their authorized `fork` remote is `https://github.com/pestopoppa/llama.cpp.git`, and publication is limited to a new `codex/*` branch. No push to kernel `main` or production promotion is allowed without explicit operator authorization and full candidate-versus-production regression validation. NEMO was initially linked; its canonical old admin remains untouched, while the active lane uses the independent admin listed above. The native lane guide at `/mnt/raid0/llm/tmp/codex3-lane-git/README.md` records bridge commands and remote boundaries.

Before any fetch/rebase/push sequence, acquire the canonical repository's serialized push lease: root key2431-96604699, research key2431-96371209, orchestrator key2431-96371138, or kernel key2431-96206859. A private clone's common directory has a different identity and its own lease does not serialize other workers. Metadata-only authenticated Git read/network commands may use the private `--git-dir` with the temporary `--work-tree=/dev/shm` override; never stage, reset, clean or inspect worktree status using that override. Review exact outgoing commits, push without force and verify the remote carries HEAD, then release the canonical lease.

For temporary linked trees already present: land or explicitly abandon unique work; archive ignored evidence and preserve required runtime source in a verified capsule; remove stale active handoff/launcher references without rewriting historical evidence; run `python3 scripts/system/worktree_gate.py check <path>` and `remove <path>`. Never force removal, prune worktree registrations or run Git GC for cleanup. Preserve branch refs and restore records.
