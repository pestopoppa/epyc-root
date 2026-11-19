#!/usr/bin/env python3
"""Classify the one diagnostic only after identity/trace/residency evidence."""
def classify(request, evidence_ok):
    if not evidence_ok: return 'invalid', 'identity, trace or residency not established'
    hint=request.get('outcome_hint'); checks=request.get('checks',{})
    if hint=='timeout': return 'timeout', 'request timeout'
    if hint=='thinking' or checks.get('no_think') is False: return 'failure', 'thinking reopened'
    if hint=='complete' and checks.get('complete') and checks.get('gold_exact') is False: return 'failure', 'wrong gold'
    if hint=='complete' and checks and all(checks.values()): return 'pass', 'one sentinel and native trace passed'
    return 'invalid', 'incomplete or invalid transport'
