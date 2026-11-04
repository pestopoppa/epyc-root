"""Pure byte-provenance view for DEBUG5 UTF8 token display lines.

Native grid bytes are NEVER transcoded, repaired, padded or synthesized.
Only non-ASCII nongrid display lines are omitted from the parser view. The
complete original capture, every excluded range and the line offset map stay.
"""
import re
import hashlib
import json

HEADER=re.compile(rb'find_slot: stream\[\d+\], n =\s*\d+, used =\s*\d+, head =\s*\d+, size =\s*(\d+), n_swa =\s*\d+')
NATIVE_DEBUG=rb'\d+(?:\.\d+)+ D '
SSE=re.compile(rb'^\d+\.\d{3} '+NATIVE_DEBUG+rb'(?:No parser definition detected, assuming pure content parser\.'+NATIVE_DEBUG+rb')?srv\s+operator\(\): http: streamed chunk: data: ')
AUX=re.compile(rb'^\d+\.\d{3} \d+(?:\.\d+)+ D srv\s+(?:stop: all tasks already finished, no need to cancel|operator\(\): http: streamed chunk: :)\n$')

def native_sse(line):
    match=SSE.match(line)
    if not match:return False
    try: event=json.loads(line[match.end():].decode('utf-8'))
    except (UnicodeDecodeError,ValueError):raise ValueError('malformed native SSE log')
    if not isinstance(event,dict) or type(event.get('index')) is not int or not isinstance(event.get('tokens'),list) or not isinstance(event.get('content'),str):
        raise ValueError('unrecognized native SSE schema')
    if any(type(token) is not int or token<0 for token in event['tokens']):
        raise ValueError('invalid native SSE token id')
    return True

def build(raw):
    chunks=[];mapping=[];excluded=[];original=view=0;owners=positions=0;phase=None
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b'\n'):raise ValueError('truncated original native line')
        interleaved=native_sse(line) or AUX.fullmatch(line) is not None
        match=None if interleaved else HEADER.search(line)
        if match:
            if phase is not None:raise ValueError('new header before complete grid in raw capture')
            size=int(match[1]);owners=size//256;positions=size//64;phase='owners'
        try:line.decode('ascii');ascii_line=True
        except UnicodeDecodeError:ascii_line=False
        if interleaved:
            excluded.append({'original_start':original,'original_end':original+len(line),
                             'sha256':hashlib.sha256(line).hexdigest(),'reason':'recognized native SSE or exact cancellation log'})
        elif not ascii_line:
            line.decode('utf-8',errors='strict')
            if phase is not None:raise ValueError('non-ASCII inside actual native grid')
            excluded.append({'original_start':original,'original_end':original+len(line),
                             'sha256':hashlib.sha256(line).hexdigest(),'reason':'non-ASCII nongrid native display line'})
        else:
            chunks.append(line);mapping.append((view,view+len(line),original,original+len(line)));view+=len(line)
            body=line.split(b' ',1)[1][:-1] if b' ' in line else b''
            if phase=='owners' and re.fullmatch(rb'[0-3M.]{256} \*',body):
                owners-=1
                if owners==0:phase='positions'
            elif phase=='positions' and len(body) in (320,322):
                positions-=1
                if positions==0:phase=None
        original+=len(line)
    if phase is not None:raise ValueError('incomplete grid in original native capture')
    return b''.join(chunks),mapping,excluded

def original_range(mapping,start,end):
    first=next(item for item in mapping if item[0]==start)
    last=next(item for item in mapping if item[1]==end)
    return first[2],last[3]

def original_segments(mapping,start,end):
    selected=[item for item in mapping if start<=item[0] and item[1]<=end]
    if not selected or selected[0][0]!=start or selected[-1][1]!=end:
        raise ValueError('view range is not aligned to native lines')
    if any(a[1]!=b[0] for a,b in zip(selected,selected[1:])):
        raise ValueError('view range has unmapped bytes')
    segments=[]
    for _,_,lo,hi in selected:
        if segments and segments[-1][1]==lo:segments[-1][1]=hi
        else:segments.append([lo,hi])
    return segments
