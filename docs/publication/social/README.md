# Social Conversations Ledger

Append-only record of the project's **external social conversations** (X/Twitter, and
later other platforms): what we posted, which public claims it made, what backed each
claim, and how notable inbound replies were resolved.

This is a working record, not published site content. It lives under `docs/`, which is
**outside the mkdocs `docs_dir` (`site_src/`)** — so nothing here is served to GitHub
Pages. That is deliberate: raw conversations carry internal vocabulary that must be
scrubbed before it goes anywhere public.

## Owner

[`handoffs/active/frontier-f6-upstream-publication.md`](../../../handoffs/active/frontier-f6-upstream-publication.md)
(W5) — the same handoff that tracks upstream GitHub engagement. The ledger is the durable
store; frontier-f6 carries the work.

## Layout

```
docs/publication/social/
  README.md            # this file — schema, gates, how to add an entry
  conversations.yaml   # the ledger (append-only, one entry per conversation)
  threads/
    YYYY-MM-DD-<platform>-<slug>.md   # verbatim transcript + soft spots + evidence
```

## Ledger entry schema

One entry per conversation/thread. Fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id, `<platform>-YYYY-MM-DD-<slug>` (e.g. `x-2026-09-15-mi210-low-quants`). |
| `platform` | yes | `x`, later `mastodon`, `bluesky`, `hn`, `reddit`, `github` … |
| `date` | yes | Post date (`YYYY-MM-DD`). |
| `account` | yes | Handle used. Keep the real handle in-repo; scrub before any public reuse. |
| `url` | posted only | Permalink to the post/thread root. Empty until posted. |
| `kind` | yes | `reply` \| `thread` \| `correction` \| `dm-summary`. |
| `status` | yes | `draft` \| `posted` \| `corrected` \| `superseded`. |
| `topic` | yes | One line. |
| `audience` | no | Who it was answering. |
| `transcript` | yes | Relative path under `threads/`. |
| `claims[]` | yes | Every public number/claim: `text`, `evidence`, `grade`, `protocol`. |
| `inbound[]` | yes | Notable replies: `from`, `summary`, `resolution`. Empty list if none. |
| `follow_up` | yes | Handoff id if the conversation generated work, else `null`. |
| `notes` | no | Soft spots, corrections owed, context. |

`claims[].evidence` points at the in-repo receipt (handoff, artifact, wiki page).
`claims[].grade` uses the [MEASUREMENT.md](../../../MEASUREMENT.md) claims grammar
(`verified` / `observation` / `design_prior` / `external` …); `protocol` is the
protocol id (e.g. `P-GPU-1`) when a governed number is quoted, else `null`.

## Gates (inherited from frontier-f6)

- **Every public number carries a claims-grammar grade and an evidence pointer.** A
  claim with no in-repo receipt is paraphrased or dropped, not published.
- **Scrub before it leaves the repo.** Reuse the public-scrub logic in
  [`scripts/publication/generate_public_results.py`](../../../scripts/publication/generate_public_results.py)
  (`public_scrub_text` / `scrub_status`): internal role aliases (`frontdoor`,
  `architect_general`, `worker_general`, …), local paths, loopback endpoints.
- **Never publish F1 personal-task data**, and strip host/infra identifiers.
- **`pii_precommit.sh`** covers credential-shaped strings on commit; it is not a
  substitute for the scrub gate above.
- **Corrections are appended, never rewritten in place.** A wrong public claim gets a
  new `correction` entry plus a status flip on the original, so the record shows what
  was said when.

## Adding a conversation

1. Drop the verbatim transcript at `threads/YYYY-MM-DD-<platform>-<slug>.md`.
2. Append an entry to `conversations.yaml` with every claim linked to its receipt.
3. Update `inbound[]` as replies arrive; resolve or file `follow_up`.
4. If a public claim turns out wrong, add a `correction` entry and flip the original's
   `status` to `corrected` — do not edit the old text.
