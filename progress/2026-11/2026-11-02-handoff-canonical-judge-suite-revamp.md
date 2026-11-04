# 2026-11-02 — handoff canonical-judge-suite-revamp

## 00:11Z — Document IFBench preparation and build an owner-controlled compute row

Consumed IFBench corpus and next-row preparation findings. Recorded the pinned corpus identity, size, scorer controls, sample join and unrun status in the handoff; acquisition and full-run boxes remain open pending durable corpus/closure review. The old launcher hardcodes a different owner, scratch directory and obsolete engine; dispatched a clean v3 row build and independent evidence review, plus LiveCodeBench v6 source-size inspection. Each output has an awaiting event; no compute was launched or published.

## 09:22Z — Reconcile completed CJ-7a and preserve IFBench and LCB sizing findings

Current origin/main already includes CJ-7a completion (handoff history commit a1e40c323). IFBench pinned corpus is 421,499 bytes; prepared source tree 2.1M, Python environment 35M, seeded NLTK 52M; offline scorer synthetic controls and network denial are in artifacts/compute/codex3-ifbench-prep-20261031/. Official LiveCodeBench lite test6.jsonl metadata at revision 0fe84c3912ea0c4d4a78037083943e8f0c4dd505 reports 134,303,240 bytes, SHA-256 bb4c364f71921c4495a6ad15abe1a927350b720009f4933e2e71f8af0f6fd1f5; official cumulative v6 window is May 2023–April 2025. Payload metadata is not a local disk measurement or proof of a post-cutoff slice. Earlier handoff checkbox edits remain preserved in stash canonical-judge-merge-recovery while index-check failure is diagnosed; they are not claimed committed. Dispatched IFBench row, CJ-7b and index diagnosis; no inference launched.
