# 2026-11-02 — research intake: Jev harness engineering + DeepSeek Super-agent essay (ws58)

- Ingested intake-2604..2616 (13 entries; 11 dive-verified, 3 GUI-expansion entries stage1-unverified); re-encounter notes on intake-146, intake-1472, intake-2603. Two Stage-2b waves for the Jev source, one for the essay. No compute used.
- Verdicts: autopilot and backlog churn gain most from typed judgments, evidence reports, named stop enums and threshold replay; AutoKernel already largely conforms. Latent fail-open found: `epyc-orchestrator orchestration/repl_memory/q_judge.py:153-157` scores an unavailable judge as an answered 1.
- Super-agent essay argues against per-event fresh sessions; tonight's churn slot-thrash (61 of 63 AUTO-STARTs with `rows=-`) traced to `handoff_sessions.py:735-831` admitting on open tasks with no start cooldown.
- GUI: spec-first loop JSON, hub Mermaid viewer, replay stepper, threshold-only round-trip edits.
- Stage-3 task lines JEV-1..6 and SA-1..4 prepared in `research/deep-dives/ws58-jev-20261102/README.md`; NOT applied — awaiting operator plan approval.
- [belief: cc]

## Source 3 (same session): LLM wiki / Obsidian second brain → operator transparency

- Ingested intake-2617..2621 (all dive-verified; intake-2621 via Stage-2b wave 1); re-encounter notes on intake-268 (Karpathy gist) and intake-270 (qmd).
- Finding: our claim layer (quote-hashed anchors, vidya CONFLICTED verdicts, cite-check) is stronger than the pattern; our human readability is weaker (append-only compiled pages, no hub page for wiki/ledger, lint lacks wiki orphans/unsourced/conflicted-citation passes, no walkable claim→commit chain, MEMORY.md truncated).
- Build path KT-1..KT-5 prepared in `research/deep-dives/ws58-jev-20261102/knowledge-transparency.md`; one shared hub renderer can serve loop design (JEV-5) and knowledge inspection (KT-3). NOT applied — awaiting operator approval.
- [belief: cc]
