#!/usr/bin/env python3
"""Offline cursor replay for KVU-12.5. Never imports or calls a real tokenizer/model.

Input is an explicit transcript of operations plus tokenizer counts. Missing transcript
ranges remain unknown; this tool does not choose a replacement cohort or offsets.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

class FakeTokenizer:
    """Deterministic test double: ceil(chars / chars_per_token), optionally scripted."""
    def __init__(self, chars_per_token=4, scripted=None, strict=False):
        self.cpt = chars_per_token
        self.scripted = list(scripted or [])
        self.calls = 0
        self.strict = strict
    def count(self, text):
        self.calls += 1
        if self.scripted:
            return self.scripted.pop(0)
        if self.strict:
            raise ValueError('tokenizer_counts exhausted before replay completed')
        return (len(text) + self.cpt - 1) // self.cpt

class Replay:
    def __init__(self, text, tokenizer):
        self.text, self.tok, self.cursor = text, tokenizer, 0
        self.rows = []
    def take(self, n, label):
        if self.cursor + n > len(self.text):
            self.cursor = 0
            wrapped = True
        else:
            wrapped = False
        before = self.cursor
        end = min(self.cursor + max(0, n), len(self.text))
        self.cursor += n
        self.rows.append(dict(label=label, start=before, advanced_end=self.cursor,
                              selected_end=end, requested_chars=n, wrapped=wrapped))
        return self.text[before:end]
    def doc(self, ntok, ratio, label):
        nch = int(ntok * ratio); start = self.cursor
        for attempt in range(4):
            self.cursor = start
            t = self.take(nch, f'{label}:adapt{attempt}')
            n = self.tok.count(t)
            if abs(n-ntok) <= max(8, ntok//400): break
            nch = int(nch * ntok / max(n, 1))
        for trim in range(8):
            if n <= ntok: break
            old_len = len(t)
            t = t[:max(1, len(t)-int((n-ntok)*len(t)/max(n,1)*1.05)-1)]
            n = self.tok.count(t)
            self.rows.append(dict(label=f'{label}:trim{trim}', selected_chars=len(t),
                                  tokenizer_input_chars=old_len, cursor_rollback=False))
        if n > ntok: raise ValueError(f'{label}: make_doc failed to fit token budget')
        self.rows.append(dict(label=label, tokens=n, target_tokens=ntok,
                              returned_chars=len(t), cursor=self.cursor))
        return t

def replay(text, ops, chars_per_token=4, scripted=None, strict=False):
    r=Replay(text, FakeTokenizer(chars_per_token, scripted, strict=strict))
    for i, op in enumerate(ops):
        label=op.get('label', f'op{i}')
        if op['kind']=='take': r.take(int(op['nchars']), label)
        elif op['kind']=='doc': r.doc(int(op['ntok']), float(op['ratio']), label)
        else: raise ValueError(f'unsupported operation kind: {op["kind"]}')
    if strict and r.tok.scripted:
        raise ValueError(f'{len(r.tok.scripted)} unused tokenizer_counts remain after replay')
    return dict(status='EXACT_FOR_SUPPLIED_TRANSCRIPT', corpus_chars=len(text),
                final_cursor=r.cursor, tokenizer_calls=r.tok.calls, intervals=r.rows)

def historical_report(exposure):
    """Conservative audit projection: absent raw ops/tokenizer responses => unknown offsets."""
    units=exposure['exact_logical_units']
    # Some exposure facts (notably the fixed warm-up) are descriptive scalars,
    # not request-unit dictionaries. Preserve them verbatim instead of assuming
    # every value has the same shape.
    logical={}
    for key, value in units.items():
        if isinstance(value, dict):
            logical[key]={q:v for q,v in value.items() if q in (
                'completed','submitted_wave0_streams','server_slot_task_pairs',
                'completed_waves','planned_but_not_submitted_suffixes',
                'all_request_results_200','in_archived_partial')}
        else:
            logical[key]=value
    return dict(schema='epyc.kvu125.offset-replay.v1', status='UNKNOWN_CURSOR_INTERVALS',
      corpus_sha256=exposure['corpus_sha256'], corpus_chars=exposure['corpus_chars'],
      exact_logical_units=logical,
      cursor_intervals='UNKNOWN', exact_char_or_byte_ranges=None,
      reason='Archived evidence has no raw make_doc/take operation transcript or per-call /tokenize responses. Exact logical request exposure cannot invert the adaptive cursor and trim behavior.',
      selection_authority='NOT_ESTABLISHED', replacement_offsets='NOT_SELECTED', compute=False)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--exposure',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True); p.add_argument('--transcript',type=Path); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); data=json.loads(a.exposure.read_text()); text=a.corpus.read_text(errors='ignore')
    digest=hashlib.sha256(text.encode()).hexdigest()
    if digest != data['corpus_sha256'] or len(text)!=data['corpus_chars']:
        raise SystemExit('corpus content binding mismatch')
    if a.transcript:
        tr=json.loads(a.transcript.read_text())
        counts=tr.get('tokenizer_counts')
        if not isinstance(counts,list) or any(type(x) is not int or x < 0 for x in counts):
            raise SystemExit('exact replay requires tokenizer_counts: a list of nonnegative integers')
        result=replay(text,tr['operations'],scripted=counts,strict=True)
        result['transcript_sha256']=hashlib.sha256(a.transcript.read_bytes()).hexdigest()
    else: result=historical_report(data)
    result['exposure_sha256']=hashlib.sha256(a.exposure.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(result['status'])
if __name__=='__main__': main()
