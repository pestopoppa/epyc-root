# 2026-11-09 apr2 prep-memrout: published rows for the doable-during-hold work

- Published (rank >= 21, below AutoKernel): `m15-comp-auc-idmap-20261109` (21), `dripreview1-r3-20261109` (22, see below). `td16-label-word-bias-20261109` (23) is prepared and waits on the TD-16 stop-rule sentence landing on origin/main.
- M-15 smoke ran the 15 s job to the end: pooled AUC 0.5913 under the id_map resolution (control identical, 0 disagreements), in-sample 0.9985. A smoke does not count; the granted run files it. Output kept under `out.smoke-20261109T1332Z`.
- D-RI-PREVIEW-1.1 (a)(b) and TD-16 driver/job: orchestrator branch `apr2/prep-memrout-20261109`. M-12 judge recipe: research branch `apr2/prep-memrout-20261109`.
- Finding: the keeper job env has no `ss`; any job using `ss` or `filler_lib.sh fl_wait_own_port` waits out its 900 s and fails rc 7 (dripreview1-r2 smoke is the evidence). Jobs now use `/proc` (`scripts/benchmark/own_port_proof.py`). Other rows using `fl_wait_own_port` are exposed; the shared lib needs the same fix (not done here, deployed path).
- Finding: the publish lint resolves `handoff_task` against the stale view (`/mnt/raid0/llm/views/epyc-root-main`, HEAD 2c62d9458); line numbers there differ from origin/main (M-15 221 vs 243). Rows carry the task text in their decision rule.
- Not published, needs a live stack: RI-17, RI-19, TR-5.3. Not published, M-12 family/CFI-1/UTM-V3/V4/V6: need a reader server on the GPU, the 5-question judge smoke, B6 merge (`request_llm_judge_text`), and for UTM-V3/V4/V6 a human-labelled case set.
