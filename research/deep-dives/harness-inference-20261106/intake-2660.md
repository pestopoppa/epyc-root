# CORTEX: A Verified Experience Layer for Generalist Agents

**Intake**: intake-2660 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2609.33260

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2609.33260v1, 14 pages). Claims 1-3 confirmed with scope narrowing; results added as claim 4 because the measured outcome inverts the naive reading: reuse cuts rule-node evaluations 62-70% while median latency rises by 0.14 ms in both domains, and the transfer study reports label equality at +24-30% reasoning work. 'Verified' means judged inside the authors' own encoding: the headline verifier is deterministic rule execution, the scenario oracle shares the runtime's source interpretation, and a model verifier appears only in a four-case pilot. Compared to EPYC's decision_receipt.v1, only two fields have a live consumer - validator identity/version and a conclusion valid-time interval distinct from offer expiry - and the source-version-separation contract is already implemented in routing_replay.py (frozen pre-purge snapshot, path + SHA-256). No reason to reopen HS-TD-4.

## Claims and corrections

- claim 0: **narrowed** — The field list is confirmed, but 'verifier' is identity plus version only (gamma = gate status + verifier version). No verifier transcript, inputs or evidence pointer is stored: an auditor can see WHO checked, not WHAT they checked.

- claim 1: **narrowed** — The four-way policy is disclosed, not demonstrated: the headline runs use exact replay only, and checked adaptation and synthesis are future-work rungs. No controller-accuracy or mode-selection measurement exists.

- claim 2: **narrowed** — Both propositions are conditional on Assumption 1 (a deterministic correct evaluator, a registry that binds scope and time without collision, and complete invalidations before use). Proposition 1 explicitly disclaims that the proof covers natural-language interpretation. Proposition 3 is a cost identity, not a safety contract.

- claim 3: **narrowed** — Gain is a rule-node counter, not wall-clock: median latency is +0.14 ms HIGHER in both domains when warm (32.07 vs 31.93; 7.76 vs 7.62). Transfer shows label equality at +24.4% and +30.2% reasoning work, with no token or currency cost reported. The pilot is four held-out cases. The 'verified' oracle shares the author's own source interpretation, so agreement is not external validation.


## Anchors

intake-2660 carries 7 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
