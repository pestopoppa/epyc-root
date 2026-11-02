# Wave-2 dives: Foreman + LangChain/Jev blog

Scratch: /mnt/raid0/llm/tmp/dive-ws58-jev-20261102/wave2/

## Sources
- Foreman: github.com/thruwire/foreman, HEAD c3142ef636617f32f772140125aa310d81ceece9 (2026-10-15, Josh Rosen), license MIT (Copyright 2026 thruwire). README.md + docs/what-foreman-proves.md read from disk. Org name "thruwire" is not the same as TypeSafe AI, but README says it supports TypeSafe Jev as default and OpenAI Decisions API; repo is a Jev-ecosystem reference runtime, NOT an evaluation.
- Blog: "Building a Harness with Jev" (page title "What Is Jev? A Guide to TypeSafe AI’s System One Model"), Sydney Runkle and Hunter Lovell (LangChain), 2026-09-17. VENDOR-PARTNER post: LangChain ships the langchain-typesafe integration; relays TypeSafe-reported figures; not an independent replication.

## Claim table
| id | source | verbatim quote | locator | quote_sha256 | note |
|---|---|---|---|---|---|
| F1 | Foreman | "Transient decision model failures are tolerated up to" | README.md:249 @ c3142ef | 3a7bcf3f125dd98c18ccbe66ede0689f806c62d65fb3aa15eddb8b7c487a468d | Bounded repair/retry with named escalation after N consecutive assessment failures; workers keep running meanwhile. |
| F2 | Foreman | "Target repositories never supply responsibility" | README.md:226 @ c3142ef | 0da776af7967c38c3dcfe720e9fbc812ee7862888a78365ff5098f24d702cb3a | Check config lives in a central registry/TOML, never in the (untrusted) target repo - registry-only selectors. |
| F3 | Foreman | "Live steering into an active turn is only" | README.md:150 @ c3142ef | 785f2d6f09015cf0c7ebdd4b2274b0d823d87ab29b21967a635a1fdb46b969ec | Capability-gated actions degrade to stop/retry when backend cannot steer - an explicit unavailable state. |
| F4 | Foreman | "that the default thresholds are calibrated" | docs/what-foreman-proves.md:43 @ c3142ef | 77b66ae84cd1fe0a71a5ff2df4f947fce05a108905f271d749e7e3f036db9c7f | Authors disclaim calibration: NO evidence for or against Jev-pattern efficacy. |
| F5 | Foreman | "that Foreman improves success rate, latency, cost, or safety" | docs/what-foreman-proves.md:40 @ c3142ef | e4bb8097007b28b9d18f5a853c85433e493b226b2408c96c8969ead2b503e058 | Explicit non-claim of any outcome improvement; feasibility only. |
| F6 | Foreman | "Runs can be labeled after the fact, threshold" | docs/what-foreman-proves.md:34 @ c3142ef | 544e42d7f97b3eea962afebe659cbc85cb6a924fc566d148c3ccff0356752ecc | Replay: saved JSONL timeline lets thresholds be re-run and false pos/neg counted. |
| B1 | Blog | "The company reports up to 200x faster inference and 400x lower cost than comparable LLMs on classification tasks." | blog.txt:70 (section: intro) | 9f682cc905804d250768a65cbb854196dca9c1eb81c6a48dec695b7688dca82c | Vendor-reported only; no methodology or independent measurement. |
| B2 | Blog | "Jev isn’t a drop-in replacement for an LLM." | blog.txt:119 (section: Use Cases) | 7cb9440fdaa189de6f3a347cdb4b4660f0c451e64a7a7947a56378ba73a51a1a | Positioning: cheap typed decisions alongside the main LLM. |
| B3 | Blog | "Agents are still inherently untrustworthy." | blog.txt:142 (section: Auto Mode) | 72f98f6a0a64af7a4a5c58f5732e8e3242492a4f8a399e480301754093161f5a | Classifier gate on tool calls before execution (AutoModeMiddleware); no numbers on catch rate. |

## Independent evidence for/against Jev patterns
- Foreman: none. Its own doc says it demonstrates "architectural feasibility", with calibration, outcome improvement and thresholds explicitly unproven. README shows illustrative scores (e.g. ready_to_finish .21) that are not measurements. Numbers present are only default thresholds (0.80 stuck/off-track/needs-human/AGENTS drift; 0.65 needs_verification; 0.75 for completion/tests/requirements) - uncalibrated design choices.
- Blog: no independent numbers; only vendor-reported 200x speed / 400x cost on classification, and an anecdotal 0.999 urgency example.

## Portable design ideas (local open-source stack)
1. Two-concurrent-loop supervisor: worker loop plus debounced assessor loop reading bounded observations (diff cap 20k chars, output tail 12k, 30 events, 10 workers history); prior result and intervention fed back in.
2. Questions as predicates (probability of yes); a deterministic arbiter, not the model, picks ONE directive with fixed safety-first priority: human need, iteration bounds, drift, off-track/stuck, retry, completion, verification, continue. Model scores only gate through thresholds + lifecycle history + resource limits.
3. Steer-once-then-stop: grace period before repeat high score stops; state tracks steering/verification to avoid oscillation; verifier starts at most once ("cannot loop").
4. Named stop reasons / escalation after N consecutive assessment failures; refusals and malformed answers treated as assessment errors, not scores.
5. Registry-only config: per-responsibility TOML with min_threshold beside checks; target repo cannot supply config. Matches registry-only selectors.
6. Append-only JSONL event timeline + state.json enabling replay of saved inputs with changed thresholds and post-hoc labeling (their stated route to calibration; needs labels and ablations they list as missing).
7. Capability-gated actions degrade (steer -> stop/retry) when backend cannot support them: model as available/unavailable.
8. Batching checks sharing an evidence selection into one request (blog: multi-question requests cost little extra) - implementable locally with one grammar-constrained call returning a JSON of probabilities from a small local model; calibrate ourselves (blog gives no recipe beyond "RLCD").
9. Gaps vs our wishlist: neither source has evidence reports with passed/failed/unverified provenance or asked/not-asked states; Foreman only has "verification results" as observation input. Choice/Score types in blog give vector+confidence, but no two-threshold scheme (Foreman uses single threshold per check).
