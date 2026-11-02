"""Deployment-owned A/A enrollment; empty fields intentionally refuse runs.

Real and keeper qualification plans are independent, pre-reviewed bindings. A
qualification result is always marked as such; it is never a real measurement.
"""
import os

EXECUTION_ENABLED = False
PLAN_PATH = ''
PLAN_SHA256 = ''
DRYRUN_PLAN_PATH = ''
DRYRUN_PLAN_SHA256 = ''


def selected():
    mode = os.environ.get('FILLER_DRYRUN', '0')
    if mode not in ('0', '1'):
        raise RuntimeError('invalid A/A qualification mode')
    dry = mode == '1'
    path = DRYRUN_PLAN_PATH if dry else PLAN_PATH
    digest = DRYRUN_PLAN_SHA256 if dry else PLAN_SHA256
    if not (EXECUTION_ENABLED and path and digest):
        raise RuntimeError('A/A enrollment not configured')
    if dry and (path == PLAN_PATH or digest == PLAN_SHA256):
        raise RuntimeError('qualification binding must differ from real binding')
    return path, digest, dry
