# When Valid Tool Calls Change Meaning: Formation-Consistent Dispatch for LLM Agents

**Intake**: intake-2658 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2609.35088

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2609.35088v1, 17 pages, all 9 tables read). Claim 1 confirmed and strengthened; claim 2 narrowed by the authority-timing result (a certificate installed after formation governs 0/3 pending calls); claim 3 confirmed with 'preregistered' qualified and reported_results populated. Comparison to intake-2652: HarnessMM's six fields prove a callback was OMITTED, and none of them names the interpreter. The minimum sound addition is three fields, not fourteen - tool_epoch (descriptor digest, handler artifact and config digest, serving process start, catalog epoch), effect_class, and expires_at/revocation_handle - and a recorded digest without a recheck at dispatch is decoration. The reviewed-profile pipeline itself should not be ported: its soundness rests on a trusted premise and our tool surface is not statically analyzable to that depth. Second-reader pass (2026-11-06): the section IV-F anchor is an elided splice of two non-adjacent sentences, and the section IV-G and Table VI anchors are condensed transcriptions; content was verified against the page text, but these are not contiguous spans.

## Claims and corrections

- claim 0: **unaffected** — Confirmed and stronger than Stage 1 implied: the paper also demonstrates descriptor-STABLE handler changes (Git 3/3, DBHub 5/5) and execution-context rebinding (OpenClaw 3/3), and kills the cheapest mitigation - schema rereading produced no wire-level relist in eight trials, and 9 of 16 prompt-only control calls reached a release different from the visible schema.

- claim 1: **narrowed** — All three components are present, but 'a certificate carried across source retirement' must NOT be read as 'any valid certificate may govern a pending call'. The central negative result is authority timing: an identical safe certificate installed after formation produced 0/3 old-call callbacks while a fresh formation produced 3/3. Authority is captured at formation and can only contract. Also, the first inclusion (actual effects within the summary) is a reviewed premise, not a checked property.

- claim 2: **narrowed** — Content confirmed, 'preregistered' is qualified: no registry entry, frozen-manifest hash or artifact URL is given, and the section itself discloses a post-freeze fixture repair. Effective independent sample is 2 call classes on one tool/transition pair; the 3 repetitions are a determinism check. Four policies x 2 classes x 3 repetitions = 24 executions.


## Anchors

intake-2658 carries 5 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
