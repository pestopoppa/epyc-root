#!/usr/bin/env python3
"""FOLD-GATE-SPEC-CORRECTNESS-V2: the canonical STEP C (spec-vs-nospec correctness) for fold-gpu gate rows.

Replaces the retired step-4 clause "C(n) spec-vs-nospec first divergence char >= C(n-1) floor" (c21-fold-gpu-20261124-r2 FAIL at
232 < 365: a single draw of a near-tie, 2 reps). Source: /mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r4/job.py (SOURCE_JOB_SHA256).

STEP C, in one paragraph: per arm (REF, CAND) x (spec, nospec) a FRESH server per unit, R_CORE=6 ABBA reps, one gated greedy request
at n_probs 0 (the served fast paths: n_probs > 0 switches off LLAMA_DEVICE_ACCEPT greedy-fast verify, the overlapped verify and the
tree batch). Each fork's margin comes from a teacher-forced probe (n_predict 1, n_probs 2) on a nospec server of the same build.
NEAR_TIE iff margin < 0.05 nat AND both fork tokens are the probe's top-2; else HARD. REAL_DEFECT iff any HARD CAND spec-vs-nospec
fork, or median(x_cand) < p10(aa_cand) AND median(x_cand) < p10(x_ref). A HARD fork repeating in >= 2 spec reps stops early.

The code lives in step_c_block.txt (host-job globals listed in its header) and is spliced between marker lines:
    # STEP_C_BEGIN  /  # STEP_C_END
CLI: fold_step_c.py splice <job.py>   (idempotent; rewrites in place)   |   fold_step_c.py check <job.py>
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.join(HERE, 'step_c_block.txt')
SOURCE_JOB_SHA256 = '96763e6ed26e684cc081ddf0e22262e61035451a1d9defe80bd1a7e9d97fa856'
BEGIN = '# STEP_C_BEGIN'
END = '# STEP_C_END'
R3_HEAD = '# ----------------------------------------------------------------------------------------------------- [r3] STEP C correctness'
TAIL_ANCHOR = '\ndef server27_argv('
REQUIRED = ('def fork_table(', 'def correctness(', 'def probe_session(', 'def run_correctness(', 'NEAR_TIE_NAT = 0.05',
            "{ta[k], tb[k]} == {t1['id'], t2['id']}", 'n_probs=2', 'def gen(base, prompt, n_predict=N_PREDICT, n_probs=0')
RETIRED = ('agree[arm] = min(pl)', 'clauses.append(f"CORRECTNESS: C19 spec diverges', 'def step4(')


def block_source():
    s = open(BLOCK).read()
    for r in REQUIRED:
        assert r in s, f'step_c_block.txt lacks {r!r}'
    return s if s.endswith('\n') else s + '\n'


def wrapped():
    return f'{BEGIN}\n{block_source()}{END}\n'


def splice(job_src):
    """Return job_src with its STEP C region replaced by the canonical block. Raises ValueError if the job has no STEP C region
    (an old-style step-4 job cannot be spliced mechanically: clone the r4-style job instead)."""
    if BEGIN in job_src and END in job_src:
        a = job_src.index(BEGIN)
        b = job_src.index(END, a) + len(END)
        return job_src[:a] + wrapped().rstrip('\n') + job_src[b:]
    if R3_HEAD in job_src and TAIL_ANCHOR in job_src:
        a = job_src.index(R3_HEAD)
        b = job_src.index(TAIL_ANCHOR, a)
        return job_src[:a] + wrapped().rstrip('\n') + '\n\n' + job_src[b:]
    raise ValueError('job has no STEP C region (no markers, no r3 heading): old step-4 job; clone the r4-style job')


def check(job_src):
    """(ok, reasons): the job carries exactly the canonical STEP C block, no retired step-4 clause, and a synthetic STEP C selftest."""
    why = []
    if BEGIN not in job_src or END not in job_src:
        return False, ['no STEP_C markers']
    a = job_src.index(BEGIN); b = job_src.index(END, a) + len(END)
    if job_src[a:b] != wrapped().rstrip('\n'):
        why.append('STEP C region differs from the canonical block')
    for r in RETIRED:
        if r in job_src:
            why.append(f'retired step-4 text present: {r!r}')
    if 'synthetic STEP C' not in job_src:
        why.append('job selftest has no synthetic STEP C case')
    return not why, why


if __name__ == '__main__':
    cmd, p = sys.argv[1], sys.argv[2]
    s = open(p).read()
    if cmd == 'splice':
        out = splice(s)
        if out != s:
            open(p, 'w').write(out)
        print('spliced', p)
    elif cmd == 'check':
        ok, why = check(s)
        print('OK' if ok else 'FAIL ' + '; '.join(why))
        sys.exit(0 if ok else 1)
    else:
        sys.exit('usage: fold_step_c.py splice|check <job.py>')
