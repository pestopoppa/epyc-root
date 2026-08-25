# HTML Artifacts Runbook

Companion to [`docs/reference/html-artifacts-index.md`](../../reference/html-artifacts-index.md) —
the index is for *discovery* ("what exists, where"); this is for *doing it right* ("how to add or
update one"). Same split as the handoff system's index +
[handoff-index-authoring.md](handoff-index-authoring.md).

**Why this exists.** Before 2026-08-23 the project's standalone HTML artifacts (design docs, flow
maps, deep-dive write-ups, operator reports) had no single discovery surface — different
harnesses/agents authoring or looking for one had nothing to check, so the same document risked
getting redone, or a new one landed in whatever directory the authoring session guessed. A repo
scan that day found only 5 real artifacts total, so the fix is a thin index plus this runbook, not
heavier tooling.

## Is HTML the right call?

All 5 existing artifacts are self-contained, themed pages: inline `<style>`, light/dark via
`prefers-color-scheme` with a `[data-theme]` override, no external fonts/CDN/scripts, no build
step — open directly in a browser. `docs/infrastructure/orchestration-stack-map.html`'s own header
comment states this outright as the contract for that whole class of doc.

Use HTML when the document genuinely benefits from that — a flow/topology diagram, a visual audit
map, an interactive legend, a themed report meant to be read in a browser. Otherwise **markdown is
the default**: plain findings, handoffs, and most research write-ups belong in the existing
`docs/`, `handoffs/`, `research/` markdown conventions, not HTML.

If you also have a Claude Artifact-publishing tool available in your harness: that publishes a
*hosted* page on claude.ai, which is a different thing from authoring a *committed file* in this
repo. The self-containment constraint below is similar in spirit but this runbook is only about
files that live in the git tree.

**Self-containment requirement**: inline all CSS/JS. No external font/CDN/script tags, no build
step, no dependency on anything outside the file itself — any agent or operator must be able to
open it straight from a checkout with no setup.

## Where it goes

Pick by what the document *is*, not by which subsystem you happen to be working in:

| Document is a... | Goes in... | Naming |
|---|---|---|
| Research write-up / deep dive | `research/deep-dives/` | `<YYYY-MM-DD>-<slug>.html`, matching a sibling `.md` of the same stem |
| Design doc / plan of record for a program | `docs/design/` | `<slug>.html` |
| Infrastructure / topology / flow map | `docs/infrastructure/` | `<slug>.html` |
| Coordination or process audit map | `docs/coordination/` | `<slug>.html` |
| Operator report tied to a specific run or decision | `artifacts/operator/` | `<run-id-or-slug>.html`, paired with a sibling `.md` when one exists |
| Anything that doesn't fit one of the above | — | Don't invent a 6th bucket. Pick the closest fit, note the mismatch in the index's Caveats column, and let a human reclassify later. |

**Do not** create a generic catch-all folder (e.g. `artifacts/html/`) and drop new artifacts there
"to keep them together" — that recreates the exact discovery problem this runbook fixes, just
under a different name. The index is the one place things are "collected"; the filesystem stays
organized by topic.

### Companion files

- If there's a markdown source of record, pair `<name>.md` + `<name>.html` (2 of the 5 existing
  artifacts do this — the `.md` is the source, the `.html` is the styled/browsable rendering).
- If the *canonical, currently-being-edited* copy could live in a different lane/worktree than the
  shared-clone copy (true of any artifact actively edited by a roster main with a lane), add a
  `<name>-STATUS.md` pointer note next to it stating which copy is authoritative as of when — the
  pattern already in use at `docs/coordination/session-bus-task-flow-STATUS.md`. Do **not** try to
  keep two copies in sync by hand; the STATUS note is the fix, not a merge.

## Registering it (mandatory, same change)

1. Add one row to the catalog table in
   [`docs/reference/html-artifacts-index.md`](../../reference/html-artifacts-index.md): Path,
   Title, Category, Companion file(s), Last updated, one-line purpose, and any caveat (e.g. "canonical
   copy lives in `<worktree>`, see STATUS note").
2. Run the drift checker and confirm it exits 0 before committing:

   ```bash
   python3 scripts/docs/check_html_artifact_index.py --check
   ```

   It fails loudly if an HTML file on disk has no index row, or an index row points at a file that
   doesn't exist — the same shape as `scripts/handoffs/index_state.py --check`'s coverage gate.

## Updating an existing artifact

- Bump its **Last updated** cell in the index row.
- If it's a self-declared living document with named re-verification sources in its own header
  (the orchestration stack map names `model_registry.yaml`, `stack_manifest.py`, `autopilot.py`) —
  re-verify against those sources before editing, not against memory of what they used to say.
- If a STATUS companion note exists, update or resolve it rather than leaving it to describe a
  divergence that no longer exists.

## What is explicitly out of scope for this index

- `dashboard/static/*.html` — the dashboard hub's live application UI, governed by
  [`dashboard/README.md`](../../../dashboard/README.md)'s view-plane rule. Not a standalone
  artifact; never add it here.
- `tmp/**/*.html` — fetched external material and research-intake scratch (gitignored). Governed by
  `agents/shared/OPERATING_CONSTRAINTS.md` → *External Content Handling*. Never index scratch.
- `worktrees/**` — duplicate checkouts of files already indexed at their canonical path. Index the
  canonical path only.
