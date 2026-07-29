# 2026-05-26 — Docs-site scaffold (MkDocs Material + GH Pages)

## Context

Same session as `2026-05-26-chapters-audit.md`. The audit refresh was Phase 1 of a larger goal — building a polished, human-readable public knowledge-base site distinct from the wiki (which optimizes for agent context). Discussion arrived at:

- **Wiki** stays as-is — agent-optimized synthesis tables
- **Chapters** (`docs/chapters/` in sibling repos) become the pedagogical "subsystems" view
- **Public site** weaves chapters + wiki + deep-dives + falsified-hypothesis trail into a unified, navigable site under MkDocs Material on GitHub Pages
- **Scope curation**: exclude `handoffs/`, `progress/`, `agents/`, `scripts/`, `CLAUDE.md`, `AGENTS.md` from public exposure

## Changes

### epyc-root: MkDocs Material scaffold

| Path | Purpose |
|---|---|
| `mkdocs.yml` | Material theme (light/dark toggle), explicit nav (30 topics + 27 subsystem chapters + landing/about), mermaid + admonition + tabbed + pymdownx extensions |
| `requirements-docs.txt` | Pinned: mkdocs-material 9.5.49, awesome-pages 2.9.3, pymdown-extensions 10.14.3, **Pygments 2.18.0** |
| `site_src/index.md` | Hand-written landing page (project overview + recent landings table + source-code links) |
| `site_src/topics/index.md` | Section intro for the wiki articles |
| `site_src/subsystems/index.md` | Section intro for sibling-repo chapters |
| `site_src/about.md` | Hardware specs, design philosophy, license |
| `scripts/docs/build-site-src.sh` | Populates `site_src/{topics,deep-dives,subsystems/{orchestrator,research}}/` from canonical sources at build time; skips `INDEX.md` files (MkDocs nav serves as TOC) |
| `.github/workflows/docs.yml` | Build on push to main (also `workflow_dispatch`); clones both sibling repos for chapters; deploys via `actions/deploy-pages@v4` |
| `.gitignore` | `site/` + generated content under `site_src/` ignored; only hand-written pages tracked |

### Pygments 2.18.0 pin — why

Initial build failed with `AttributeError: 'NoneType' object has no attribute 'replace'` in `pygments/formatters/html.py`. Root cause: Pygments 2.19+ tightened `HtmlFormatter`'s filename handling to reject `None`, but `pymdown-extensions ≤10.13` passes `filename=None` when no filename is set. Two fixes available — pinned both (pygments down, pymdownx up) for belt-and-braces.

## Results

- Local build: **169 HTML pages, 29 MB, 3.3 s build time**
- 651 link warnings (non-fatal, build non-strict): cross-references to non-published paths (`handoffs/`, `progress/`, absolute `/mnt/raid0/...` in deep-dives). Long-term fix is a link-rewriter pass that converts these to GitHub URLs.
- Workflow will fire on next push but **needs Pages enabled in repo settings** (Source: GitHub Actions). One-time manual step.

## Deferred / Follow-ups

1. **Enable Pages in repo settings** (operator action): https://github.com/pestopoppa/epyc-root/settings/pages → Source: GitHub Actions
2. **Link-rewriter pass** — rewrite cross-doc links to point at GitHub URLs (so handoffs/, progress/, absolute paths render correctly in the published site). Tracked in `handoffs/active/docs-site-narrative-and-rewriter.md`.
3. **Narrative anchor pages** — the curated story layer on top of the chapters: "How a request flows through the stack", "Worker_general 17 → 76 t/s", "What we tried and ruled out", "What we're investigating now", etc. Tracked in the same handoff.
4. **Custom domain + analytics** — both easy to add later, not in v1 scope.

## Commits

| Repo | Commit | Branch | Pushed |
|---|---|---|---|
| epyc-orchestrator | `535cca6` | main | yes |
| epyc-inference-research | `b95ba18` | main | yes |
| epyc-root | `437a778` (audit trail) | main | yes |
| epyc-root | `10aa13f` (MkDocs scaffold) | main | yes |

Wrap-up commit pending (closes-out handoff + this progress entry).
