# EXP-09 pilot disposition

Original row `brf-exp09-pilot-20261102` is **inconclusive / REVISE harness** (rc=75), not a completed STOP or EXPAND decision. The native capture has 37/48 cells: control 12, verified quote 9, shape header 8, pointer only 8. The control source identity passed and the planted mismatch was rejected in 9/9 quote cells. All completed cells retain raw answers and selected evidence.

The operational futility look fired at 6.592 + 3 < 9.717. Five unparseable answers reached exactly 256 completion tokens (four shape-header, one verified-quote), confounding this stop. Observed arm means are unequal-denominator exploratory summaries, not a balanced comparison: control accuracy 0.80975; verified quote 0.73244; shape header 0.5; pointer only 0.27075. Retention means are in SUMMARY.json. The reference failed-ID list is capped at ten and matching uses substring inclusion; this pilot does not establish exact full-log recall.

The next row repeats the frozen 12 logs and scorer with a 1024-token evaluator answer budget, preserving the worker-summary budget and pinned control. Incomplete/futility outcomes remain inconclusive; do not combine repaired outputs with these originals. Parent TOC-SP-3 stays open for the complete experiment and product change.

Native results SHA-256: `cb8f455daa1ddacee266a8e3dbf83aa63a3f23a55ed7f2d6854e6629c4ba95da`. Files in this directory preserve the original result, job, identity, launcher, manifest and row spec as captured. Corpus paths in these original manifests describe original custody; the successor must own independent prepared inputs. No production activation or served-latency claim follows.

Successor `brf-exp09-answerbudget-r2-20261104` was published after the four-CPU smoke PASS (actual cell required by smoke predicate). Its partial rc=75 smoke termination is expected qualification cleanup, not a science verdict. The keeper owns the long run. Successor input/code/spec pins and the native qualification receipt are retained under `successor/`.
