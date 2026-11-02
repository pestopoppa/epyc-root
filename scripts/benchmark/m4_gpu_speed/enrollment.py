"""Deployment-owned enrollment; an empty enrollment refuses all real runs.

Replace only after independent review of the complete plan and producer source.
Never populate this file from a measurement row or environment variable.
"""
CAPTURE_ROOT = ""
PLAN_PATH = ""
PLAN_SHA256 = ""
SOURCE_SEALS = ()  # (absolute path, SHA-256) pairs, including the native producer

# Fixed deployment-owned grant authority and common cgroup guardian are prerequisites.
GRANTS_DIR = "/mnt/raid0/llm/tmp/compute-flags/grants"
HOLD_DIR = "/mnt/raid0/llm/tmp/compute-flags"
EXECUTION_ENABLED = False

# Optional independent test-only binding. Never use this plan for measurements.
DRYRUN_CAPTURE_ROOT = ""
DRYRUN_PLAN_PATH = ""
DRYRUN_PLAN_SHA256 = ""
DRYRUN_GRANTS_DIR = ""
DRYRUN_HOLD_DIR = ""
