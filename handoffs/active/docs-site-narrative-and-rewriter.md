# Docs-site narrative pages + link-rewriter

**Status**: active
**Opened**: 2026-05-26
**Predecessor**: `handoffs/completed/docs-chapters-audit-refresh.md` (chapter substrate refresh) + commit `10aa13f` (MkDocs scaffold)

## Motivation

The MkDocs Material site is scaffolded and deploys from `main`. The chapter substrate is current. Two follow-up tracks remain to make the site actually polished:

1. **Link-rewriter** — kill the 651 build warnings by rewriting cross-doc links that point to non-published paths (`handoffs/`, `progress/`, absolute `/mnt/raid0/...`) into GitHub-source URLs that render correctly in the published site.
2. **Narrative anchor pages** — the curated story layer on top of the chapters. Without these, the site is a navigable reference but doesn't yet *teach* a cold reader why the project is interesting.

User invocation (this session, 2026-05-26): "proceed with both please" — the user wants both tracks pursued, not chosen between.

## Track 1 — Link-rewriter

**Problem**: 651 link warnings at build time. Mostly:
- `../handoffs/active/<name>.md` (we deliberately don't publish handoffs)
- `../progress/YYYY-MM/<date>.md` (same)
- `/workspace/...` absolute paths in research/deep-dives content
- `/mnt/raid0/llm/...` absolute paths (pre-monorepo-split era leftovers)
- Sibling-repo absolute paths in some deep-dives

**Approach**: a build-time script that runs after `build-site-src.sh` and before `mkdocs build`. For each markdown link in `site_src/**/*.md`:

- If it points to a published path within site_src → leave alone
- If it points to `handoffs/`, `progress/`, `agents/`, `scripts/`, `CLAUDE.md`, `AGENTS.md` (within epyc-root) → rewrite to `https://github.com/pestopoppa/epyc-root/blob/main/<path>`
- If it points to an absolute `/workspace/...` path → resolve relative to epyc-root, then apply the GitHub rewrite
- If it points to an absolute `/mnt/raid0/llm/<repo>/...` path → rewrite to the corresponding sibling repo's GitHub URL
- If it points to a deleted/moved file → log as warning, leave alone (manual triage)

**Implementation**: Python script `scripts/docs/rewrite-links.py`. Idempotent (run before mkdocs build).

**Acceptance**:
- Build warning count drops from 651 to <50
- Spot-check 5 rewritten links in the deployed site — they navigate to the right GitHub blob
- Workflow updated to call rewriter before mkdocs build

## Track 2 — Narrative anchor pages

**Goal**: ~5-7 hand-written pages that weave chapters + wiki + deep-dives + falsified-hypothesis trail into stories an outside reader can follow cold.

**Voice**: lab notebook + product changelog. Concrete numbers. Cite chapters/wiki/deep-dives for depth.

**Anchor list** (agreed earlier in session):

1. **How a request flows through the stack** — cross-repo system tour. Routing → escalation → MemRL → workers → response. Anchors: orchestrator chapters 02, 10, 07; wiki routing-intelligence + cost-aware-routing.
2. **Why CPU-only inference is viable on EPYC** — hardware story → NPS4 → CCD work → kernels. Anchors: wiki hardware-optimization + inference-serving; chapter 04.
3. **Worker_general: 17 → 76 t/s** — MTP + KMP_BLOCKTIME + ik_llama PR #1744. Anchors: research chapter 02; wiki moe-optimization + inference-serving; project memory `feedback_ik_llamacpp_omp_idle_spin` + `project_worker_general_swap_2026_05_08`.
4. **Autonomous research loop** — autopilot + intake + wiki compilation. Anchors: wiki autonomous-research; orchestrator chapter 07; agent_log.sh tooling.
5. **The speculative decoding investigation** — worked for MoE, dead on hybrid SSM, +17-21% incremental over NUMA. Anchors: research chapters 01, 10; wiki speculative-decoding + ssm-hybrid.
6. **What we're investigating now** — curated subset (5-10 entries) of `handoffs/active/master-handoff-index.md`. Hand-edited monthly, not auto-synced.
7. **What we tried and ruled out** — 15-20 entries from intake `not_applicable` + closed-negative deep-dives. NUMA mirror, L3aaN, AReaL, DeepConf, slot promotion v1, hybrid SSM spec-dec, etc.

**Tone constraints**: outside reader, no project jargon left unexplained. Cite chapters/wiki for depth but the page itself should be readable cold. Mermaid diagrams where they earn their space.

**File placement**: `site_src/stories/` (new directory). Each page is hand-written; doesn't go through `build-site-src.sh`. Add a "Stories" section to mkdocs.yml nav above "Topics".

**Acceptance**:
- All 7 pages drafted (length 800-1500 words each, plus diagrams where they help)
- Each one passes "cold reader" check — a person who has never seen the project can follow it
- Cross-links to chapters/wiki/deep-dives present and resolve in build

## Phases

- [x] **Phase A** — link-rewriter — COMPLETE 2026-05-26 (commit `d74692e`)
  - `scripts/docs/rewrite-links.py` (164-file published-map, reverse-map skip for hand-written pages, GitHub-blob fallback for unpublished, sibling-repo URL mapping, anchor + code-fence handling)
  - Wired into workflow between populate + build
  - Result: 820 links rewritten across 46 files; build warnings 651 → 0 (3 residual cosmetic INFO-level anchor refs)
- [x] **Phase B** — calibration story (`how-a-request-flows.md`) — COMPLETE 2026-05-26 (commit `d74692e`)
- [x] **Phase C** — remaining 6 anchor pages — COMPLETE 2026-05-26 (commit `d74692e`)
  - All 7 stories landed in one pass under `site_src/stories/`
  - Math correction in `why-cpu-inference.md` (commit `17b8125`)
  - Stylistic rewrite of 6 stories against the voice baseline (commit `6119e6e`); bold-prefix-paragraph count 50+ → 3; word counts normalized to 1000-1200 range
- [ ] **Phase D** — polish: mermaid topology diagram on landing page; auto-generated "Recent results" from `progress/` digests; resolve 3 residual stale-anchor refs inside research chapters 01 + 03

## Constraints

- **Don't auto-sync** the "investigating now" / "ruled out" pages from raw indices. Always hand-curate — auto-sync re-exposes operational noise.
- **No analytics in v1** (user preference: not commercial).
- **Stories cite primary sources** (chapters, wiki articles, deep-dives) — don't restate findings without a link.
- **One commit per page** so review is granular.

## Cross-references

- Predecessor handoff: `handoffs/completed/docs-chapters-audit-refresh.md`
- Predecessor progress: `progress/2026-05/2026-05-26-chapters-audit.md`, `progress/2026-05/2026-05-26-docs-site-scaffold.md`
- Deployment status: GH Pages enable pending operator action (Source: GitHub Actions in repo settings)
