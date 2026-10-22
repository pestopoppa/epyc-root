# 2026-10-22 workspace-f8

## Overnight 2026-10-21/22

Results recorded in the handoffs (evidence under `/mnt/raid0/llm/tmp/`):

- **PB-HOL-1 budget-on arms** (`gpu-serving-tie-in-program.md`, ticked): A-on 3593 ms, B-on 83352 ms (23.2x), B-on-nodec 63980 ms vs off arms A 3217.5 / B 70932 (22.05x). The prefill budget does not relieve slot-order HOL (confounded by `-b`/`-ub` 512 -> 2048). M4 ordering fix filed. DI-126 and KVU-16g-2 notes updated.
- **PB-QCOST-1** re-validation: frozen model FAIL (held-out MAPE 12.84% n=1, 26.32% n=4, biased low); refit passes (2.4%, 3.83%). Indicative only: ran beside KVU-12 np8 CPU timing with host threads 184-191 contended. Uncontended confirmation filed.
- **KPF-18 item 3 (G1 repeats, ended rc1=0 rc2=0)**: cumulative over all six item-3 records, fork vs no-fork token-identical 17/21, A/A 20/21, min prefix 43 both. Fork divergences: group 0 at token 43 (once), group 3 at token 161 (3 of 3 passes); A/A divergence: group 0 at token 43 (once). Observation grade; group-3 check filed.
- **KVU-12.4 / 12.5 redo**: np4 L64k ABA NO_DIFFERENCE (PROPOSED-until-ratified; unified -22.78% decode sum against a 12.48% anchor floor, weak). np8 L64k pair CONFOUNDED (unified gpu_busy_frac 0.47 vs split 0.0). s4 hit its 12,000 s cap (rc 125). Bank build and mtp-off np8 done; pool-full step skipped for time.
- Operator decisions of 2026-10-21 recorded: DP-1 = (a), DP-4 = (A) (queue rows removed), VB-AP-SPINUP-AP3-SCOPED added; SEC-SECRETS-1 D9 ack, SEC-ART-3 allowlist, SEC-EXEC-6 revoke (operator task added), AKX-AUTO-6 owner = workspace-f8.
