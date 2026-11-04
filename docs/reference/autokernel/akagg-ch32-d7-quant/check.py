#!/usr/bin/env python3
"""Inspect the pinned D7 quantizer delta and C5 prerequisite surfaces; no checkout."""
import json
import subprocess

REPO = '/mnt/raid0/llm/llama.cpp'
C5 = 'c72ec82f5417bb2937310326120f149b665e8400'
D3 = '19cce6919992fdffd92e0ac152caaf1e2b8f254e'
D4 = '19ff817fb25e9a1b838b1d7f9f4325f7bf9779c4'
D7 = '889f2ec96deacbc2d8a9a67dbe181eaa43a2fb3b'

def git(*args):
    return subprocess.check_output(['git', '-C', REPO, *args], text=True)

def show(rev, path):
    return git('show', f'{rev}:{path}')

def ancestor(a, b):
    p = subprocess.run(['git', '-C', REPO, 'merge-base', '--is-ancestor', a, b], check=False)
    if p.returncode not in (0, 1):
        raise RuntimeError(f'ancestry check failed: {p.returncode}')
    return p.returncode == 0

quant = 'src/llama-quant.cpp'
conv = 'conversion/lfm3.py'
base, before, after, d4parent, d4 = (show(r, quant) for r in (C5, D7 + '^', D7, D4 + '^', D4))
rules = {
    'encoder_convolution': 'name.rfind("a.conv1d.", 0) != 0',
    'depthwise_convolution': 'name.find("conv_dw") == std::string::npos',
    'codec_all': 'name.rfind("a.gen.wav.", 0) != 0',
    'codec_quant_only': 'name.rfind("a.gen.wav.quant.", 0) != 0',
}
flags = {label: {rev: rule in source for rev, source in [('c5', base), ('d4_parent', d4parent), ('d4', d4), ('d7_parent', before), ('d7', after)]} for label, rule in rules.items()}
for label in ('encoder_convolution', 'depthwise_convolution'):
    assert flags[label] == {'c5': False, 'd4_parent': False, 'd4': True, 'd7_parent': True, 'd7': True}, (label, flags[label])
assert flags['codec_all'] == {'c5': False, 'd4_parent': False, 'd4': True, 'd7_parent': True, 'd7': False}
assert flags['codec_quant_only'] == {'c5': False, 'd4_parent': False, 'd4': False, 'd7_parent': False, 'd7': True}
conv_before, conv_after = show(D7 + '^', conv), show(D7, conv)
codec_f16 = 'if new_name.startswith("a.gen.wav."):'
assert codec_f16 in conv_before and codec_f16 not in conv_after
for marker in ('new_name.startswith("a.conv1d.")', '"conv_dw" in new_name', 'new_name.startswith("a.gen.wav.quant.")'):
    assert marker in conv_before and marker in conv_after, marker
assert 'class LFM3AudioMmprojModel' not in show(D3, conv)
assert 'class LFM3AudioMmprojModel' in show(D4, conv)
assert ancestor(D3, D4) and ancestor(D4, D7)
print(json.dumps({
    'schema': 'akagg.ch32.d7-quant-source-check.v1',
    'revisions': {'c5': C5, 'd3': D3, 'd4': D4, 'd7': D7},
    'd3_ancestor_of_d4': True, 'd4_ancestor_of_d7': True,
    'quantizer_rules': flags,
    'conversion': {'d3_has_audio_class': False, 'd4_has_audio_class': True, 'd7_removes_codec_f16_exclusion': True, 'd7_retains_encoder_depthwise_and_codec_quant_exemptions': True},
    'scope': 'Pinned source text evidence only; neither minimal full-commit chain nor runtime behavior established.'
}, indent=2, sort_keys=True))
