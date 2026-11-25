# 2026-11-25 — pipeline-mgmt

## Publish outage: INSTALL.manifest gaps (root cause: new modules not in the manifest)

- **Outage**: publish ~12:14-12:47Z; reclaim-at-filing ~11:54-13:2xZ. New modules were not added to INSTALL.manifest, so the deployed rowflow lacked them.
- **Fixes**: `family_strikes` + `estimate_history` (0f25f2a25); `keep_failed` (218793b4c, after 421a2f4ca). A manifest-coverage test (92f2a927c) found the keep_failed gap.

## Changes

| Item | Commits |
|---|---|
| ak_gate harness | 8545b50ec, 8bb2d9e06, 6820416db, aa32438ba, fb2ddbe80, 2e2de9fdf; A ac90f161b; B bd99b5c66 |
| Generator gap fixes | 4a3e4add4 |
| Waste-audit remediations R2/R3/R5/R6/R7 | fe7f62b35, fe1de3b52, fbd84419e, 2fae96236, bc6beba9c |
| R8 (smoke hold release, keeper wake) | 05d00706f |
| Evidence keep | dbadf99d5 |
| Narrow HOST-DRAIN (operator-approved) | e0552f74a, ee2beb1ec, 9cdaf78f8 |
| Audit doc | docs/design/ak-waste-audit-20261125.md (d10a97ec0) |

Reviews: `/mnt/raid0/llm/tmp/review-akgate-20261125.md`, `/mnt/raid0/llm/tmp/review-r8-keep-20261125.md` (F7/F8/F2 trims in flight in another agent).
Boxes already filed and ticked by their agents: AKWASTE-R2..R7, AKW-R8, PM-HOST-DRAIN-NARROW.

## Codex lanes

cx12, cx14, cx17, cx18, cx19 landed; cx20 not ticked. **Operator-relevant**: the "5 unassisted" bar was met only for code-writing; Claude ran the tests and pushed every lane.

## Derived actionables filed (churn-pipeline track)

- PM-CODEX-UNASSISTED-DEF: redefine unassisted (own tests on cores 84-87, push via serialized_push); 5 such lanes before the PM-CODEX-DISPATCH-DETERMINISTIC port.
- PM-REPLAY-RECEIPT-ENFORCE: flip PREFLIGHT_ENFORCE replay_receipt; update 3 tests in test_ak_gate.py.
- PM-R8-KEEP-TRIMS-FOLLOWUP: F3, F4, F9 (F7/F8/F2 in flight elsewhere).

## Evening section (after the 13:40Z wrap-up 2eef96cbe)

Everything below is on main. "Live" means canary-passed and DEPLOYED.json-verified (see Lessons); the keeper/rowflow changes went live by 0385ea351, 3af820d85, 9f9752310 or e3faa5b0b.

| Area | Change (SHA) |
|---|---|
| Keeper / rowflow | GPU firefox-floating fix + host-drain via quiet gate ab3d269c6; cx39 drain skip for GPU-blocked host a742a28f6; cx40 GPU-first host deferral (operator order) d889f290f; cx51 all drain paths 1e87c4c89; cx53 smoke hold a77d8d538; STOP-park 45abd83e4; owner alert restored 218785eb9; superseded display 8c9702cf8; WAIT-FOR-SMOKE fix 6badfc9da; cx50 deploy-gate fix |
| ak_gate / generator | rehearsal 2176c8459, ca9270d6a; tbo witness exemption 1ddcc1147; tbo not-supported 97f02f270; cx37 rc0 1606363e0; cx38 --fix-ref 3a354f2da; cx34 one check path bd718f467; cx36 install xdir 4d62abfef; cx41 futility refuse d36e4f6ec; cx42 --futility f4f72374e; cx46 colon trap f59a43db7; cx47 n_prompts 856393ae5; cx48 total decide ba37fc3b3; cx49 unit reuse 2f3630a29; cx52 noise_arm dde30ee4e; cx54 argv exists 7710c5f48; cx56 full-shape smoke a23d2a921; cx57 reuse key semver bac0af30b; smoke-budget override hotfix 029c0e5f9; cx29 sampler/load 16e2c9a35; canary cx32 502373dc3; cx33 family strike harness 05e3855e1 |
| Codex dispatcher | port 54bef0e4c; filters 4ae80eb29, b8e99728f; cx27 4aa725ab4; cx35 (xrepo) dcf99a6da; cx31 (bulk scope) 08eebbd0e; PM-CODEX-DISPATCH-DETERMINISTIC ticked e65b3e694 |
| Disk | scratch_worktree helper 5bd4fbd3c; per-tick reap 1d697aae2; archive-then-reclaim ~66 GB + 3 stale dirs + refactor-01a16fc3; trash sweeps. Free space 210 GB -> 338 GB |
| Box audit wave | applied 873d9468d, fa34a7fe1, a90348135, 208692c15; 6 routed via /mnt/raid0/llm/tmp/box-audit-20261125/OWNER-NOTES.md; 16 lanes re-running overnight |

**Still in flight (not done):** cx58 smoke deadline (REPORT exists, not verified live here), cx59 multi-prompt A/A (no cx59-REPORT yet), the next deploy, the A3B canary watcher (/mnt/raid0/llm/tmp/pm-r8h-resume.sh).

### Lessons (honest)

- Production was stuck on 01c127dbc from about 15:01Z to 16:14Z while I reported fixes as live. A merged SHA is not a deployed one.
- Parallel deploy loops overwrote each other's logs, so the evidence for what deployed was partly destroyed.
- Harness traps shipped live (colon trap, n_prompts, argv, reuse key, smoke budget). Rule now: a change is "live" only after a canary passes and DEPLOYED.json shows the SHA.
- My own build claim blocked AutoKernel quiet rows: a self-placed claim starved the rows it was meant to serve.
- 12 full runs were wasted by harness faults before the full-shape smoke (cx56) existed; the smoke should have preceded the first full run.

## Derived actionables filed (evening, churn-pipeline track)

PM-TRASH-SWEEP-ROBUST (needs operator approval, safety script), PM-ROOT-OWNED-SOURCE, PM-IODIE-HALF-RULE, PM-SINGLE-DEPLOY-LOOP, PM-SMOKE-AA-ALL-PROMPTS (open: cx59 not reported DONE), PM-STALE-ROW-SWEEP.
