# NI Orchestrator/Research legacy worktree retirement — 2026-10-30

Parent accepted all dispositions. Removed **37 NI-owned registered linked worktrees** through worktree_gate.py: 20 Orchestrator and 17 Research (see archive-refs.json for authoritative per-repo count). All 37 original HEADs have verified dedicated refs/archive/codex-ni-retirement-20261030/<tree-name> refs as well as retained original branches. All 37 paths are absent. No assigned dirty/unlanded tail remains.

Allocated du footprints measured before removal cover 35 paths: 26,362,155,008 bytes (24.552 GiB). The first two immediate gate removals were not sized; no exclusive df reclaim is claimed during peer cleanup. Exact individual values: measured-footprints.json.

Custody root: `/mnt/raid0/llm/tmp/codex-ni-repo-legacy-retirement-20261030` (KEEP). Patches, original index/sparse metadata, selected candidate files and original refs are retained. REPL2.8b six-file trace-v2 candidate is unvalidated and still needed; source baseline74a313d6, no landing or completion. Frozen region-lock pidfd c07d28fa retained without runtime changes. Weaker HPR dirty draft superseded by retained c4c2a3638; raw/golden files and UNVERIFIED contract unchanged. CJ10 raw staged fixtures archived; accepted JSON representation c43/59 controls untouched. EVL49 v4/v5 twenty dry files preserved in untracked-evidence.tar; runbook exact accepted main3caaf22fa.

Scoped pinned source-readsets: AK startup nine files/881636 B; HPR seven files/308361 B; INF75 five files/517386 B. Retired 51 historical own launcher/PREP scripts by byte-preserving same-directory rename; hashes verified. No full-tree copies, new worktrees, force/prune/gc, model weights, frozen-kernel changes, runtime reloads or process kills.

Three protected Orchestrator /mains/codex-ni-* lanes remain inventory-only pending root reusable-lane choice; not cleanup failures. No source implementation work remains in this task.

Validation: fresh origin/main source/acceptance comparison, PID/cwd/argv/env and launcher probes, no live ready/grant assigned path references, gate removals, 37 archive refs+path absence, retired script digests. Result is administrative custody verification, not a performance or inference finding. [no-belief: administrative source custody and worktree retirement]
