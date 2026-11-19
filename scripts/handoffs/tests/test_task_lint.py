#!/usr/bin/env python3
"""Targeted tests for task_lint_v2: the three v5 fixes + regression tests for the v4 fixes. Run: python3 -I scripts/handoffs/tests/test_task_lint.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); import task_lint as L
INF = ("- [ ] **X-1** [inference] measure decode t/s of Qwen3.8-27B Q8_0 on the C5 champion build with llama-bench, metric tg128 (higher better),"
       " rule keep if ≥0.95× control, region gpu")
def _all(txt): r, w = L.publish_findings(txt); return r + w   # refusals + warnings
def t(name, cond): print(('PASS ' if cond else 'FAIL ') + name); return cond
def _run():
    ok = True
    # v5-1 publish fails on field h (pending operator choice)
    ok &= t('publish WARNS (not refuses) on pending operator choice', not any('pending operator choice' in w for w in L.publish_text(INF + ", est 600 s from run r1; stop-on-futility; operator to decide whether to adopt"))) and t('publish warning lists pending operator choice', any('pending operator choice' in w for w in L.publish_findings(INF + ", est 600 s from run r1; stop-on-futility; operator to decide whether to adopt")[1])) and t('pending operator choice is reported', any('pending operator choice' in w for w in _all(INF + ", est 600 s from run r1; operator to decide whether to adopt")))
    ok &= t('publish allows issued authorization', not any('pending operator choice' in w for w in _all(INF + ", est 600 s from run r1 (operator 2026-10-25: authorized one bounded window)")))
    # v5-2 est provisional requires a bounded pilot clause
    ok &= t('bare est provisional warned (estimate field)', any('incomplete' in w and 'estimate' in w for w in _all(INF + ", est provisional")))
    ok &= t('est provisional + bounded pilot accepted', not any('estimate' in w for w in _all(INF + ", est provisional ~900 s; pilot: bounded n=6 launches/arm")))
    ok &= t('est from a measured run accepted', not any('estimate' in w for w in _all(INF + ", est 600 s from run r1")))
    # ws58 2026-11-02: no run citation is required; a plain numeric est passes
    ok &= t('plain numeric est accepted (no run-cited rule)', not any('estimate' in w for w in _all(INF + ", est 600 s; stop-on-futility")))
    ok &= t('identity refusal names the exact field to add', any('add region:' in w for w in _all("- [ ] **X-2** [inference] measure decode t/s of Qwen3.8-27B Q8_0, rule keep if >= 1, est 600 s; stop-on-futility")))
    # operator 2026-11-03: publish REFUSES only on missing model/build identity or missing stop rule; the rest WARN
    ok &= t('relaxed: model/build missing refuses', any('quant_build' in w for w in L.publish_text("- [ ] **X-3** [inference] measure decode t/s, rule keep if >= 1, region gpu, est 600 s; stop-on-futility")))
    ok &= t('relaxed: missing metric/rule/region/estimate only warns', (lambda r, w: not r and any('identity fields incomplete' in x for x in w))(*L.publish_findings("- [ ] **X-4** [inference] run the Qwen3.8-27B Q8_0 champion build; stop-on-futility")))
    ok &= t('relaxed: NEEDS tag warns, does not refuse', (lambda r, w: not r and any('NEEDS tags' in x for x in w))(*L.publish_findings(INF + ", est 600 s; stop-on-futility NEEDS-OWNER")))
    ok &= t('relaxed: non-inference warns, does not refuse', (lambda r, w: not r and any('non-inference' in x for x in w))(*L.publish_findings("- [ ] **X-5** [non-inference] implement the scorer adapter")))
    ok &= t('relaxed: roll-up and standing hold warn', (lambda r, w: not r and any('roll-up' in x for x in w) and any('standing' in x for x in w))(*L.publish_findings(INF + ", est 600 s; stop-on-futility [roll-up] STANDING CONSTRAINT: keep off")))
    ok &= t('relaxed: no stop rule still refuses', any('stop rule' in w for w in L.publish_text(INF + ", est 600 s")))
    # v5-3 own block excludes nested descendants
    parent = "- [ ] **P-1** wire the scorer into run.py (non-inference deliverable)\n  - [ ] **P-1.a** measure t/s with llama-bench on the GPU, operator to decide whether to adopt"
    r = L.score2(parent, 1)
    ok &= t('nested child does not make parent inference', r['class'] == 'non-inference')
    ok &= t('nested child decision does not flag parent h', 'h' not in r['fails'])
    ok &= t('own_block strips descendants', 'P-1.a' not in L.own_block(parent))
    # v4 regressions
    ok &= t('deliverable validation: scorer build is non-inference despite t/s mention', L.exec_type("- [ ] build the FAIL_TO_PASS scorer; report t/s in the log")[0] == 'non-inference')
    ok &= t('deliverable validation: an A/A pair is inference (ws58 2026-11-02)', L.exec_type("- [ ] **M4-X** same-frame A/A at np4/65536 on the MI210")[0] == 'inference')
    ok &= t('deliverable validation: run X against our local endpoint is inference', L.exec_type("- [ ] Run EvalPerf against our local endpoint")[0] == 'inference')
    ok &= t('issued authorization is not operator-decision class', L.score2("- [ ] compare one backend against the incumbent on a sealed workload (operator ruling Q1, 2026-09-29: local models only)")['class'] != 'operator-decision')
    ok &= t('standing constraint recognised', L.decision_kind("- [ ] re-calibrate floors. OPERATOR HOLD 2026-10-24: DO NOT LAUNCH AUTOKERNEL") == 'standing-constraint')
    ok &= t('NEEDS-OPERATOR tag never a migrate failure', L.score2("- [ ] decide whether to adopt X NEEDS-OPERATOR")['tags'] == ['OPERATOR'])
    ok &= t('old approval does not suppress a later unresolved choice', L.decision_kind("- [ ] run the window (operator 2026-10-25: authorized one bounded window). Then the operator must choose between keeping or reverting the knob") == 'pending-choice')
    ok &= t('dated operator decision alone is issued', L.decision_kind("- [ ] CH-27 bounded recal run (operator decision 2026-10-25 via decision tool): hold lifted ONLY for ONE window") == 'issued-authorization')
    ok &= t('inference task without stop rule fails s / publish refuses', 's' in L.score2(INF + ", est 600 s from run r1")['fails'] and any('sufficiency' in w for w in L.publish_text(INF + ", est 600 s from run r1")))
    ok &= t('inference task with stop rule passes s', 's' not in L.score2(INF + ", est 600 s from run r1; stop rule: stop-on-futility only (gate-class), look every 6 launches")['fails'])
    ok &= t('non-inference task never fails s', 's' not in L.score2("- [ ] wire the scorer into run.py")['fails'])
    ok &= t('numeric child refused', L.score2("- [ ] **DF2-12.1.3** do part three")['numeric_child'])
    ok &= t('roll-up detected', L.score2("- [ ] **R-1** [roll-up] non-dispatchable parent")['rollup'])
    # ws58 2026-11-02 (BRF-T1-1 fold 7): an href is not prose — repointing a link must never change the verdict
    w4 = ("- [ ] **W4 — promotion workflow + first cohort** (recurring, ~half day/month): monthly pass — promote rows when wired."
          " First cohort: `edit_transaction_auto_routing` (A2 rollout contract prepared in [`multi-file-coding-completion-capability.md`]({})).")
    a = L.score2(w4.format('multi-file-coding-completion-capability.md'))
    b = L.score2(w4.format('benchmark-suites.md#track-multi-file-coding-completion-capability'))
    ok &= t('href text does not classify the box', (a['class'], a['fails']) == (b['class'], b['fails']) and b['class'] != 'inference')
    ok &= t('mutation: the same words in prose do classify', L.score2(w4.format('x.md') + " Then benchmark the model endpoint with llama-bench.")['class'] == 'inference')
    ok &= t('field f still reads hrefs (retired scratch path)', 'f' in L.score2("- [ ] wire the scorer, see [log](/mnt/raid0/llm/tmp/wt-old/run.log)")['fails'])
    ok &= t('prose keeps link text, drops target', L.prose("see [`a.md`](bench/b.md#x) and https://bench.example/x") == "see [`a.md`] and ")
    print('ALL PASS' if ok else 'SOME FAILED'); return ok


def test_task_lint():
    assert _run()


if __name__ == '__main__':
    sys.exit(0 if _run() else 1)
