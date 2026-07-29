# 2026-05-26 — Docs-site link-rewriter + 7 narrative stories + stylistic pass

## Context

Continuation of `2026-05-26-docs-site-scaffold.md`. MkDocs Material was scaffolded earlier in the session; the chapter substrate had been refreshed via the earlier audit pass. This entry covers Phase A + Phase B + Phase C of the `docs-site-narrative-and-rewriter` handoff, plus an unscheduled stylistic pass.

## Changes

### Phase A — Link rewriter

| Path | Purpose |
|---|---|
| `scripts/docs/rewrite-links.py` | Post-populate Python pass: builds a published-map of 164 source files + reverse-map so hand-written pages are never touched; for each link, resolves to canonical epyc-root path, then either rewrites to local site path (published) or to a GitHub blob URL (not published). Handles `/workspace/...` and `/mnt/raid0/llm/<repo>/...` absolute paths, `../` relative traversal, sibling-repo chapter refs, anchors, code-fence exclusion. |
| `.github/workflows/docs.yml` | New "Rewrite cross-doc links" step wired between populate + build |
| `.github/workflows/docs.yml` | `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` env (preempts the June 2026 Node 20 forced-default) |

**Result**: 820 links rewritten across 46 files. Build warnings 651 → 0; 3 residual INFO-level stale-anchor refs inside underlying chapter content (cosmetic).

### Phase B + C — Seven narrative stories

| Path | Voice |
|---|---|
| `site_src/stories/index.md` | Section landing |
| `site_src/stories/how-a-request-flows.md` | Cross-repo system tour |
| `site_src/stories/why-cpu-inference.md` | Bandwidth math + NUMA story (became the voice baseline for the rest) |
| `site_src/stories/worker-general-story.md` | 17 → 76 t/s cascade (MoE + MTP + OMP idle-spin fix) |
| `site_src/stories/autonomous-research-loop.md` | Intake → deep-dives → wiki → AutoPilot with cost accounting |
| `site_src/stories/spec-decoding-investigation.md` | GPU-vs-CPU regime difference; deployed + ruled-out examples |
| `site_src/stories/investigating-now.md` | Curated active work queue (3 spotlight paragraphs + 13-row status table) |
| `site_src/stories/ruled-out.md` | 8 falsified hypotheses (3 in full prose, 5 in summary table) |

Plus `site_src/deep-dives/index.md` (hand-written landing) and `site_src/about.md` (existing).

### GH Pages deployment recovery

The first scaffold push (`10aa13f`) fired the workflow before Pages was enabled (failed at deploy step with HTTP 404). Once the operator enabled Pages, a manual workflow_dispatch deployed `8379f53` cleanly. The Phase A+B push (`d74692e`) coincided with a GitHub Actions **major outage**, then with `actions/upload-pages-artifact@v3` codeload failures during the recovery. Manual dispatch succeeded once Actions returned to operational; deploy completed at run `26450076785` (90s wall-clock).

### Stylistic pass

User feedback noted that some narrative pages read densely. A stylistic review against `why-cpu-inference.md` (the voice baseline) identified recurring issues across the other 6 pages:

- Bold-prefix-paragraph-as-list-item used as a pseudo-spec-doc structure (~50+ occurrences across 6 pages)
- Pile-up citations at end of paragraph
- Formulaic "What this story demonstrates / What's next" closings
- Template repetition (the 4-field hypothesis/measured/closed/reopen template in `ruled-out` repeated 8× identically)

Rewrote all 6 pages. Net 141 lines removed across the 6 files. Bold-prefix count: 50+ → 3 (the 3 are deliberate spotlights in `investigating-now`). Word counts now within the 1000-1200 range matching the baseline.

### Math correction

User caught arithmetic error in `why-cpu-inference.md` — 460 GB/s vs A100 1.6 TB/s is ~1/4, not ~1/8. Fixed in `17b8125`.

## Results

- Public site live at https://pestopoppa.github.io/epyc-root/
- 7 narrative stories landed under Stories tab; surfaced in nav above Topics
- Build warnings down to 3 residual cosmetic INFO; net build time ~3.3 s local, ~90 s end-to-end on GH Actions
- Auto-rebuild on push to `wiki/**`, `research/deep-dives/**`, `site_src/**`, `mkdocs.yml`, `requirements-docs.txt`, `scripts/docs/**`, or the workflow itself

## Deferred / Follow-ups

1. **Phase D polish** — mermaid topology diagram on landing page; consider adding an auto-generated "Recent results" page from progress digests. Not blocking.
2. **More narrative stories** — SkillBank experience-distillation rollout, autopilot exogenous-restart resilience incident, constrained-creativity planner. Hand-curated; no auto-generation planned.
3. **Stale-anchor warning cleanup** — 3 INFO-level warnings on links to anchors that no longer exist inside research chapters 01 + 03 (pointing at chapter 10). Edit either the linking content or add the anchor.
4. **Custom domain + analytics** — both easy, not in v1 scope.

## Commits this session (post first wrap-up)

| Repo | Commit | Branch | Pushed |
|---|---|---|---|
| epyc-root | `d74692e` (link rewriter + 7 stories + Node 24) | main | yes |
| epyc-root | `17b8125` (GPU bandwidth math fix) | main | yes |
| epyc-root | `6119e6e` (stylistic rewrite of 6 stories) | main | yes |

Wrap-up commit pending (this progress entry + handoff updates).
