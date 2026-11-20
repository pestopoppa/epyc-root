# Owner roles — anti-bloat review (2026-11-20, read-only)

Inputs: `OWNER-TAXONOMY.md` (9 roles), `OWNER-ROLES.md`, the three drafts on `pm-owner-roles` (`agents/{autokernel,autopilot,pipeline-mgmt}.md`), current `agents/{coordinator-agent,auditor-main,inference-main,README}.md`, 364 memory notes, `INCIDENT_LOG.md`, the AK session audit.

## 1. The test — when a role earns an agent file

All four must hold; otherwise it is a skill, a runbook, or handoff ownership.

1. **Standing cross-session state not in any file** (live grants, holds, an in-flight program) that a fresh session plus the repo cannot rebuild in one turn — with **measured re-learning cost** (incidents or repeated operator corrections caused by a fresh session missing it).
2. **A roster identity code routes to** (`notify.py` assignee, `holds.yaml` sessions, dispatcher gates). No routing → no name needed.
3. **Judgment at a boundary code refuses to decide** (operator packages, accepting proposals), not a procedure with a start and an end.
4. **Recurrence**: weekly or permanently live; a burst every few weeks is a runbook plus a fresh session.

Negative tests: fits a handoff's `## Dispatch contract` → handoff ownership; a procedure → skill/runbook; a "lost knowledge" list made of memory notes → those belong in the docs the skill cites, not in a role file.

Evidence base: memory notes by cluster — pipeline/rowflow 172, harness 165, kernel 140, stack 128, autopilot 55, intake 43, vidya/wiki 28, speech 14 (terms overlap). `INCIDENT_LOG` (45): rowflow/grant/smoke 4, stack/bring-up 4, kernel 2, autopilot 1, intake/wiki/harness 0. Only the pipeline cluster has sustained, code-routed, cross-session state; the kernel cluster's audit shows five workflows re-executed by hand hundreds of times — procedures, i.e. skills.

## 2. Verdicts

| Candidate | T1 state | T2 routed id | T3 judgment | T4 | Verdict |
|---|---|---|---|---|---|
| pipeline-mgmt | registry, holds, grants, keeper; 4/45 incidents | `rowflow-keeper`, `filing-watch`, alerts, ownerless-proposal queue | packing, defect triage, D9 deploys | live | **Role**; merge into the coordinator once the dispatcher is proven (§4) |
| autokernel | partial: lineage is in `kernel-manifests/`, journals, handoff; audit's 5 workflows are procedures | `autokernel`; rows/holds route to it | lever design, campaign stop | live loops | **Role, thin** (≤ 50 lines) |
| autopilot | no: dormant since 08-09; state = journal shards + strategy store (files) | none yet | hold-lift is the operator's | burst | **Handoff-only**; rules → `autopilot-program.md` dispatch contract; role only if relaunched |
| harness / user-facing | no today: integration parked behind upstream work (operator) | none | later | burst | **Handoff-only** (harness-program, routing-program). Fold the 20 sessions, not create a role |
| autokernel vs inference-research | the difference is loop-management vs research; research = rows + handoffs | `inference` = resource owner only | no | burst | **Merge**: `inference-main.md` → compute-resource owner under pipeline-mgmt; evaluation handoff-only |
| compute calendar | the keeper's grants/queue files | `rowflow-keeper` | the `inference-backlog-scheduling` skill | by code | **Merge into pipeline-mgmt** — "how so?": it is the keeper's process plus a skill, not a role |
| research intake | no: stages, steering ledger, schema all in the skill/`.research-session.json` | none | Stage 3 needs "what matters now" = backlog + holds, both files | per batch | **Skill**; add a `backlog-priority.json` + `holds.yaml` read to Stage 3 |
| stack lifecycle / bring-up | no: compiled registry, topology yaml, deterministic apply/prove; the 4 incidents became hooks/skills | none | signature is the operator's | rare | **Runbook + skills** (`stack-change`, `kernel-promotion`, `change-role`, `change-topology`), fresh session |
| kernel promotion | no | none | operator | rare | **Skill**, prepared by autokernel, signed by the operator |
| knowledge / vidya / wiki | partial: adapter program with code changes | none | adapter design | weekly | **Handoff-only** (vidya program) + `project-wiki`/`research-intake` skills |
| speech / multimodal | yes: frozen kernels on three ggml generations, operator vision D1–D8, human-ear corpus — tacit | `stt5` today | cascade/frontdoor | weekly | **Handoff owner with a ≤ 40-line dispatch contract**; no role file needed |
| coordinator | fleet state, operator intent, holds, decision queue | `coordinator-agent` | every boundary | live | **Role — the one entry point** (§4) |
| auditor | none by design; headless per-packet since 08-16 | `auditor` kept for the routing linter | review | on demand | **Contract, not a session** (its own status note says so) |
| mainA–D | lane ids | retired in roster | — | — | **Delete from the model**: a lane is a slot, not an identity |
| hygiene, dashboard | no | none | no | filler | **Task class** |

Net: **coordinator + pipeline-mgmt**, plus a **thin autokernel** while its loops run. Three, not nine.

## 3. Minimal set, and owners without role files

- **Coordinator** — operator's single point of entry over the dispatcher.
- **pipeline-mgmt** — the dispatcher's keeper: rowflow/taskflow/holds, filing, pipeline defects reported by owners, delegated review of ownerless proposals. Merge into the coordinator when the dispatcher is proven; two console-like roles is one too many.
- **autokernel** — the only domain role, because its loops are live and rows/holds route to it.
- **Builder sessions** — ad hoc, no role, no roster id; they build loops with the operator and leave a handoff behind.

**Ownerless handoffs get owners from files, as the dispatcher already does.** `start_handoff` spawns a session whose first prompt is `brief_text` + the handoff's `## Dispatch contract` + the top box or pending proposals. The owner needs only: shared policy (`CLAUDE.md`, `agents/shared/*`); the handoff header (`**Row**`, `**Domain**`, `**Owner**`, `**Holds**`, `**Scratch**`) and its ≤ 40-line dispatch contract; its `.box-index.json` records; the skills it names (`row-owner-loop`, `inference-backlog-scheduling`, `log`). `OWNER-ROLES.md` §1's `**Owner role**` key stays optional, pointing at a role file only for the three roles; a missing key means "generic owner", never "refuse". Keep the `brief_text()` injection; drop the harness-native flags (`--append-system-prompt-file`, opencode agent files) until a role proves it needs them. Ownership belongs to the handoff (operator 2026-11-20): a gone owner is re-spawned from files; a role file would only be a longer brief.

## 4. Coordinator and auditor

`agents/coordinator-agent.md` (267 lines) is written for the bus fleet: 35 mentions of panes, tmux, mainA–D, the coordinator-daemon and `bus_supervisor` (ruled down 09-23); FM-2/FM-4 and "Auditor and Inference Main provisioning" describe retired flows. Keep three durable ideas — be the console, every boundary reaches the operator through this role, cite INVARIANTS instead of restating — and rewrite the rest around the dispatcher:
- **Inputs**: `.box-index.json`, `.index-state.json`, `holds.yaml`, the dispatcher registry/log, `queue_status.py`, the proposals ledger, the master-index decision queue.
- **Duties**: decision packages (recommended first); set/release holds (`handoff_sessions.py gate/unpark`, the only `holds.yaml` writer besides the operator); accept/reject delegated proposals for ownerless handoffs; approve builder-session plans; run the operator-invoked `/wrap-up` sweep; own `CURRENT-CAMPAIGN.md`.
- **Never**: run rows, edit another owner's boxes, sign, restart production, write human-only docs (ratify scripts only).
- **Liveness**: one live session whenever the dispatcher runs; it absorbs pipeline-mgmt's console function, leaving pipeline-mgmt as code owner.

Auditor: keep `auditor-main.md` as the headless review contract; drop auditor provisioning from the coordinator file; no auditor role in the new set.

## 5. The three drafts — bloat

Measured by 6-gram overlap with CLAUDE.md, `agents/shared/*`, `agents/README.md`, the workflow guides and the owned handoffs: autokernel 109 lines — 7 restate shared policy, 5 restate handoff text, 3 cite **memory notes** (per-user files no other harness can read); autopilot 79/3/3/4; pipeline-mgmt 81/4/0/3. The schema (Mission → Learned) is fine; the content is the bloat.

**Cut from all three.** `## Guardrails` (pkill, pathspec commits, `git add -A`, literal paths, ruling (b)) = CLAUDE.md § Process Management / `OPERATING_CONSTRAINTS` → one citing line. Operating-loop steps 1–2, 4–5 (drain, heartbeat, fan-out, wrap-up cadence) = CLAUDE.md § Agents & Automation → delete. `## Learned` git mechanics → keep the one-line format. Every "*Why*: memory `feedback_…`" → cite the incident/commit or move the rule into the doc and cite that. Codex-off-AK/autopilot and "ask pipeline-mgmt to park" → now structural in `holds.yaml`, one cite.

**autokernel.md → ≤ 50 lines.** Rules 5–9, 12 are rowflow procedure → the `row-owner-loop` skill (`720768eb0`). Rules 1–4, 10, 13–14 are CLAUDE.md freeze/forward-port rules or handoff holds → cite. Keep mission, roster id, owned handoffs, "champion always current", "never promote", rule 11 (campaign stop), the two coordination bullets. `## Tools` duplicates the skill.

**autopilot.md → a dispatch contract, not a role.** Rules 1–3, 5–6 are the handoff's own *2026-11-09 audit refresh*; 4, 7–10 are memory notes → fold into `autopilot-program.md`'s `## Dispatch contract` and `docs/`. "Roster id: none yet" says it all.

**pipeline-mgmt.md → ≤ 50 lines.** Rules 6–10, 14 are now code (F3, F4, B1, F5, B11, Stage B) → delete, they are tests. Rules 1, 3, 11 are CLAUDE.md. Keep mission, the watcher list, D9/ratify gates (one line each), rules 2, 4, 5, the ownerless-proposals duty. The `Design (scratch, outside the repo)` pointer to `/mnt/raid0/llm/tmp/…` must not be in a role file — move the design docs to `docs/design/` first.

**Process.** `OWNER-ROLES.md` §3's pre-commit lint, `Role-Review:` trailer and Learned-promotion workflow govern ~150 lines of text: drop the lint and trailer; keep "the live owner reviews structural edits" as one sentence in `agents/README.md`.
