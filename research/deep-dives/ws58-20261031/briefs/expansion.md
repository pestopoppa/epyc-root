# Phase-3 literature expansion + cheap contradiction pass (ws58 intake, 2026-10-31)

Read scratch:dive-ws58-20261031/briefs/stage1_common.md first: its safety, fetch, scoring and
output rules apply to you in full (YAML schema per new source). Additional rules:

- DROP-UNOBSERVED-IDS: every arXiv id / URL you return must appear in a search result or fetched page
  from THIS run. Record `observed_in: <url of the page/search where you saw it>`. For every arXiv id,
  curl https://arxiv.org/abs/<id> and confirm the title matches; report `title_check: match|mismatch`.
  Never return an id from memory. If you cannot locate a seed, say NOT-LOCATED (that is provisional, not
  proof of absence).
- Dedup: before returning a source, grep /mnt/raid0/llm/worktrees/intake-ws58-20261031/research/intake_index.yaml
  for its arXiv id and URL (unbounded, no head). If present, return only `{seed, existing: intake-NNN}`.
- Budget: per seed at most 2 search rounds. Return at most the number of new sources stated in your seed list.
- Raw downloads under scratch:dive-ws58-20261031/raw/exp-<slug>/.
- Use WebSearch and WebFetch (Stage-1 discovery is allowed to use them), curl for the abs-page title checks.

## Cheap contradiction pass (Tier 2b, Stage-1 scope)
For each listed contested claim, run <=2 searches ("<claim/technique> criticism", "<technique> limitations",
"<model> benchmark independent"). Report hits as `contradicting_evidence` lines with URL, or "no contradiction
surfaced in a bounded search (provisional)". Label vendor restatements as restatement, not corroboration.

## Return
1. `new_sources:` YAML blocks (schema from stage1_common.md plus observed_in, title_check, expanded_from: <seed source URL>).
2. `existing:` list of seed -> intake-NNN collisions.
3. `not_located:` list with what you searched.
4. `contradictions:` per claim.
Concise. No file dumps. No repo writes, no commits.
