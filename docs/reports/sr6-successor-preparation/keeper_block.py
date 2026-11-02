#!/usr/bin/env python3
"""Connect SR-6's sampled bench-lock proof to guarded block capture.

This module is not a launcher or a complete row: its caller must authenticate
all supplied pins and paths, establish the authoritative exposure inventory,
server identity and residency, continuous ownership and in-flight STOP, and
prove that no descendant escapes session cleanup. No compute starts at import.
"""
from bench_claim import FullHostBenchClaim
from guarded_block import capture_guarded_block
from keeper_admission import KeeperAdmission


def capture_keeper_block(*, env, row_id, grant_path, stop_path, guard_sha256,
                         output, block, sampler, sampler_sha256, spawn,
                         verify_ready_and_identity, port, timeout_s,
                         max_response_bytes):
    """Capture one block only after the bound keeper and bench claims pass.

    The same admission object is passed to the guarded block, whose existing
    lifecycle and request path recheck it at their own boundaries. A successful
    return is capture only, not a measurement or an authorization verdict.
    """
    claim = FullHostBenchClaim(row_id, guard_sha256)
    admission = KeeperAdmission(env=env, row_id=row_id, grant_path=grant_path,
                                stop_path=stop_path, ownership_check=claim)
    if admission() is not True:
        raise ValueError('keeper or bench claim not established')
    return capture_guarded_block(output=output, block=block, sampler=sampler,
        sampler_sha256=sampler_sha256, admission=admission, spawn=spawn,
        verify_ready_and_identity=verify_ready_and_identity, port=port,
        timeout_s=timeout_s, max_response_bytes=max_response_bytes)
