#!/usr/bin/env python3
"""NON-AUTHORITATIVE proposal test; synthetic fixtures only, never an admission tool."""
import copy
import sys
from pathlib import Path

benchmark=Path('/workspace/repos/epyc-inference-research/scripts/benchmark')
sys.path.insert(0,str(benchmark))
import cpu_prefill_v8_regression_runner as validator
import test_cpu_prefill_v8_regression_runner as fixtures


def proposed48(samples):
    # Private process, synthetic fixtures only. The repository validator, the current
    # interpreter's callers, and its 96-thread default are restored in all outcomes.
    old=(validator.CONFIGURED_CPU_COUNT, validator.MIN_TARGET_CORE_EQUIVALENTS)
    try:
        validator.CONFIGURED_CPU_COUNT=48
        validator.MIN_TARGET_CORE_EQUIVALENTS=36.0
        return validator.validate_monitor_samples(samples)
    finally:
        validator.CONFIGURED_CPU_COUNT,validator.MIN_TARGET_CORE_EQUIVALENTS=old


def must_fail(samples):
    try: proposed48(samples)
    except RuntimeError: return
    raise AssertionError('synthetic invalid sequence was accepted')


def main():
    hz=validator.CLOCK_TICKS
    # Existing fixture generates 10 one-second intervals; all values are synthetic.
    good=fixtures.monitor_series([(38*hz,36*hz)]*10)
    result=proposed48(good)
    assert result['thresholds']['configured_cpu_count']==48
    assert result['thresholds']['minimum_target_core_equivalents']==36.0
    assert result['sustained_window']['signed_external_core_equivalents']==2.0
    must_fail(fixtures.monitor_series([(38*hz,36*hz-1)]*10))
    must_fail(fixtures.monitor_series([(38*hz,36*hz)]*9))
    for busy in (35*hz,40*hz):
        proposed48(fixtures.monitor_series([(busy,36*hz)]*10))
    for busy in (35*hz-1,40*hz+1):
        must_fail(fixtures.monitor_series([(busy,36*hz)]*10))
    for mutation in ('swap','ownership','contamination'):
        changed=copy.deepcopy(good)
        if mutation=='swap': changed[1]['swap']['pswpin']=1
        elif mutation=='ownership': changed[1]['target']['ownership_changed']=True
        else: changed[1]['contamination']['exact_llama']=[{'pid':7}]
        must_fail(changed)
    malformed=copy.deepcopy(good); malformed[0]['cpu_counter_bracket']={}; must_fail(malformed)
    assert validator.CONFIGURED_CPU_COUNT==96 and validator.MIN_TARGET_CORE_EQUIVALENTS==72.0
    # The very same 36-core synthetic series must still fail the existing validator.
    try: validator.validate_monitor_samples(good)
    except RuntimeError: pass
    else: raise AssertionError('existing 96-thread default changed')
    print('PASS: proposed 48-thread fixtures only; existing 96-thread defaults intact')

if __name__=='__main__': main()
