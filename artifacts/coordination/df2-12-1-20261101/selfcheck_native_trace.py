#!/usr/bin/env python3
"""Model-free parser contract check for prompt/decode and recurrent reuse markers."""
from __future__ import annotations

import pathlib

import native_trace


ROOT = pathlib.Path(__file__).resolve().parent
LOG = ROOT / 'SYNTHETIC-NATIVE.log'


def main():
    LOG.write_text('\n'.join((
        'DF2_NATIVE_REUSE_V1 slot=0 task=10 cache_prompt=1 n_past=0 old_prompt_tokens=0 seq_pos_min=-1 checkpoints=0',
        'DF2_NATIVE_BATCH_V1 batch=1 slot=0 task=10 phase=prompt prompt_len=1 prompt_fp=101 slot_tokens=4 decoded_subbatch_len=8 scheduler_batch_len=8 off=0',
        'DF2_NATIVE_BATCH_V1 batch=1 slot=1 task=11 phase=prompt prompt_len=1 prompt_fp=102 slot_tokens=4 decoded_subbatch_len=8 scheduler_batch_len=8 off=0',
        'DF2_NATIVE_BATCH_V1 batch=2 slot=0 task=10 phase=decode prompt_len=1 prompt_fp=101 slot_tokens=2 decoded_subbatch_len=2 scheduler_batch_len=2 off=0',
        'DF2_NATIVE_ROUND_V1 batch=2 slot=0 task=10 draft_n=4 accepted=2 rollback=2 decoded_subbatch_len=2 scheduler_batch_len=2 off=0',
        'DF2_NATIVE_REUSE_V1 slot=0 task=12 cache_prompt=1 n_past=3 old_prompt_tokens=12 seq_pos_min=0 checkpoints=1',
    )) + '\n')
    good = native_trace.parse(LOG)
    assert good['complete'] and not good['malformed']
    assert len(good['reuse_markers']) == 2 and good['reuse_markers'][0]['seq_pos_min'] == -1
    LOG.write_text(LOG.read_text().replace('phase=prompt', 'phase=decode'))
    bad = native_trace.parse(LOG)
    assert bad['complete']  # Syntax is valid; science binding must reject decode-only co-prefill.
    assert not any(row['phase'] == 'prompt' for row in bad['batch_markers'])
    print('native marker parse and prompt-phase discrimination PASS; synthetic only')


if __name__ == '__main__':
    main()
