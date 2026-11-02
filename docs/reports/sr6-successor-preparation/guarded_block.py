#!/usr/bin/env python3
"""Compose SR-6's keeper, request and session-drain seams, not a runnable row.

Callers must prove grant region ownership, session containment, server identity,
residency, runtime pins and authoritative exposure inventory. The drain helper
cannot detect children that leave the session. In-flight STOP is not enforced.
"""
from pathlib import Path

from block_controller import execute_block
from keeper_admission import KeeperAdmission
from session_drain import drain_session
from verified_post import VerifiedPost


def capture_guarded_block(*, output, block, sampler, sampler_sha256, admission,
                          spawn, verify_ready_and_identity, port, timeout_s,
                          max_response_bytes, drain=None):
    """Capture one block with one common keeper check and scoped session drain.

    spawn must return a session leader created by spawn_session and clean up on
    exceptions. Identity and region-ownership adapters remain external evidence.
    A successful return is capture only, not an inference or performance verdict.
    """
    if not isinstance(admission, KeeperAdmission):
        raise ValueError('keeper admission object required')
    if not isinstance(output, Path) or not callable(spawn) or not callable(verify_ready_and_identity):
        raise ValueError('output and lifecycle adapters required')
    post = VerifiedPost(port=port, timeout_s=timeout_s,
                        max_response_bytes=max_response_bytes,
                        deadline=admission.deadline, stop_file=admission.stop_path,
                        admission_check=admission)
    return execute_block(output=output, block=block, sampler=sampler,
                         sampler_sha256=sampler_sha256, admission_check=admission,
                         spawn=spawn, verify_ready_and_identity=verify_ready_and_identity,
                         post=post, drain=drain if drain is not None else drain_session)
