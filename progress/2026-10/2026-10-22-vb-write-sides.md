# 2026-10-22 VB write sides (3c4ca599)

Ten belief-kernel write sides landed in root `scripts/vidya/adapters/` (no inference). Each: capture writer + strict reader + registered projection, shared grade only, README rows appended, ingest source registered.

| task | module | tests |
|---|---|---|
| VB-HIL15A-WRITE | hil15a_auc.py | test_hil15a_auc.py (7) |
| VB-DRIPREVIEW-WRITE | repl_preview.py | test_repl_preview.py (8) |
| VB-RTEPFX2-WIRE | rte_pfx2_capture.py (+chunk_kv kind) | test_rte_pfx2_capture.py (7) |
| VB-AK-PAIRED-LOADGEN-WRITE, VB-AKRSG-WRITE | autokernel_legacy_serving.py claim text; research branch vb-write-akpl-3c4ca599 (unpushed) | test_autokernel_paired_loadgen_serving.py (4) |
| VB-HSPROF1-WRITE | hs_prof1_profile_arms.py; research branch hsprof1-belief-write (unpushed) | test_hs_prof1_profile_arms.py (27) |
| VB-RUS2-PROBE-WIRE | rus2_probe.py | test_rus2_probe.py (11) |
| VB-EV19-GOLD-SELFCHECK-WIRE | ev19_gold_selfcheck.py | test_ev19_gold_selfcheck.py (10) |
| VB-OOLONG-WIRE | oolong.py | test_oolong_adapter.py (11) |
| VB-YARN-AGG-1 | yarn_gate_agg.py (schema epyc.yarn_gate_decision.v1 in docstring) | test_yarn_gate_agg.py (15) |

Open producer-side calls (owned by other agents): HIL driver, run_repl_preview.py, rte_pfx2_role_recipe.py, yarn_gate runner, oolong window runner, gold_self_check, rus2 probe; the s5-hsprof1-beam job must repin research to hsprof1-belief-write and set EPYC_ROOT. Pre-existing: harness_improvement writes protocol_id "observation:none" (non-empty), so its observation rows grade Witnessed.
