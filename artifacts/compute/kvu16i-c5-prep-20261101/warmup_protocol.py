#!/usr/bin/env python3
"""Prospective, deterministic C5 replay warm-up; not the historical row-4c warm-up."""
import hashlib
import json
from pathlib import Path

C2 = Path('/mnt/raid0/llm/tmp/ds41-c95/contexts/C2/prompt.inline.txt')
C4 = Path('/mnt/raid0/llm/tmp/ds41-c95/contexts/C4/prompt.inline.txt')
C2_SHA = '581599a025264f1ef162b0c1e01136142be4f57d0d0c6500df301e036dec5845'
C4_SHA = '8ee1975dfd09493161fccf3f9b9d64c8c6f43c0095f3b8d2f541c0bc09e6a4b8'
TASK = '\n\n---\nSummarize the key technical constraints in the material above.'

def bodies(c2=C2, c4=C4):
    a, b = c2.read_bytes(), c4.read_bytes()
    if hashlib.sha256(a).hexdigest() != C2_SHA or hashlib.sha256(b).hexdigest() != C4_SHA:
        raise ValueError('warm-up context hash mismatch')
    text = a.decode('utf-8') + '\n\n' + b.decode('utf-8')
    if len(text) < 100000:
        raise ValueError('warm-up context shorter than declared character slice')
    return [ {'messages':[{'role':'user', 'content':text[:n] + TASK}], 'max_tokens':64, 'stream':True}
            for n in (100000,10000) ]

def hashes():
    return [hashlib.sha256(json.dumps(body).encode()).hexdigest() for body in bodies()]

if __name__ == '__main__':
    print('\n'.join(hashes()))
