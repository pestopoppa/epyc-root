# 2026-11-09 apr2 rtg08-evl47-pip04-code

Branches: root `apr2/rtg08-evl47-pip04-code-20261109`, root `apr2/rtg08-evl47-pip04-code-correctionfix-20261109`
(salvage cherry-pick), orchestrator `apr2/rtg08-evl47-pip04-code-20261109`. Nothing pushed or landed.

- EVL-47: Canary B frontier assertion + synthetic controls (`canary_b_frontier.py`, tests 4 passed; controls verified
  through the real orchestrator journal -> archive path). R18-D A/A adapter `ak-r18d-aa`, source wiring, tests, filing
  under `data/vidya/run-filings/2026-11-08/`; the real capture is REFUSED as a floor (all 136 invocations
  `clock_stable=false`). Correction-fix salvage prepared on its own branch; pending corrections still 312.
- RTG-08: CTX-HO-3 implemented (`resume_state`), TOC-CMP-5 tests (orchestrator). CTX-HO-1 blocked: Appendix C not
  readable verbatim. TOC-CMP-2/3/4, DCP-9a/10/10b/15 not started.
- PIP-04: ODL-013 r2 and R36 65-page evidence copied (text only, SHA256 manifests bind raw); SX-6 sentinel driver
  (orchestrator); SLIDERS 0.1-0.2 documents, 0.3 premise found wrong. G14 install not done.
- Canonical ledger untouched (sha256 prefix 09603091 before and after). Scratch: `/mnt/raid0/llm/tmp/apr2-vidya`,
  `/mnt/raid0/llm/tmp/apr2-canary-probe`.
