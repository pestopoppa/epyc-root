"""Replay RI-25's exact private JSON/JSONL byte prefixes; emit counts and hashed locators only."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

ROLES = {'worker_math', 'worker_general', 'worker_summarize'}
REQUIRED = {'family', 'relative_path', 'prefix_bytes', 'sha256', 'device', 'inode', 'verified_at_utc', 'format'}

class PrefixError(ValueError):
    """A selected source prefix cannot be replayed exactly."""

def read_manifest(path: str | os.PathLike[str]) -> list[dict[str, str]]:
    with open(path, newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise PrefixError('manifest is missing required columns')
        rows = list(reader)
    seen=set()
    for row in rows:
        rel=row['relative_path']
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or not rel or '\\' in rel:
            raise PrefixError(f'invalid relative path in manifest: {rel!r}')
        if rel in seen: raise PrefixError(f'duplicate manifest path: {rel}')
        seen.add(rel)
        if row['family'] not in {'progress','candidate'}: raise PrefixError(f'unknown family: {row["family"]}')
        if row['format'] not in {'json','jsonl'}: raise PrefixError(f'unknown format: {row["format"]}')
        try:
            if int(row['prefix_bytes']) < 0 or int(row['device']) < 0 or int(row['inode']) <= 0: raise ValueError
        except ValueError: raise PrefixError(f'invalid numeric manifest metadata: {rel}')
        if len(row['sha256']) != 64 or any(c not in '0123456789abcdef' for c in row['sha256']):
            raise PrefixError(f'invalid sha256: {rel}')
        if not row['verified_at_utc'].endswith('Z'): raise PrefixError(f'capture timestamp must be UTC Z: {rel}')
    return rows

def _safe_path(root: Path, rel: str) -> Path:
    root=root.resolve(strict=True)
    path=root/rel
    cursor=root
    for part in Path(rel).parts:
        cursor=cursor/part
        if cursor.is_symlink(): raise PrefixError(f'symlink in source path: {rel}')
    try: path.resolve(strict=True).relative_to(root)
    except (FileNotFoundError, ValueError): raise PrefixError(f'source path missing or outside root: {rel}')
    return path

def _walk(value: Any, path: str='$'):
    if isinstance(value, dict):
        for key, child in value.items(): yield from _walk(child, f'{path}.{key}')
    elif isinstance(value, list):
        for index, child in enumerate(value): yield from _walk(child, f'{path}[{index}]')
    elif isinstance(value, str):
        yield path, value

def _row_strings(row: dict[str, Any]):
    if row['format']=='json':
        try: obj=json.loads(row['_bytes'])
        except (json.JSONDecodeError, UnicodeDecodeError): return [(1,None,'invalid_json')]
        return [(1,path,value) for path,value in _walk(obj)]
    out=[]
    for line_no, raw in enumerate(row['_bytes'].splitlines(),1):
        try: obj=json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError): out.append((line_no,None,'invalid_json')); continue
        out.extend((line_no,path,value) for path,value in _walk(obj))
    return out

def replay_entry(root: str | os.PathLike[str], entry: dict[str, str]) -> dict[str, Any]:
    path=_safe_path(Path(root),entry['relative_path'])
    before=os.stat(path,follow_symlinks=False)
    if not os.path.isfile(path): raise PrefixError(f'not a regular file: {entry["relative_path"]}')
    if (before.st_dev,before.st_ino)!=(int(entry['device']),int(entry['inode'])):
        raise PrefixError(f'rotated/replaced source: {entry["relative_path"]}')
    size=int(entry['prefix_bytes'])
    if before.st_size<size: raise PrefixError(f'source shorter than frozen prefix: {entry["relative_path"]}')
    h=hashlib.sha256(); remaining=size; rows=0; total_values=0; invalid=0
    generic=0; marker_count=0; role_counts=Counter(); hits=[]
    def consume(obj,line_no):
        nonlocal total_values,generic,marker_count
        for field,value in _walk(obj):
            total_values+=1; lower=value.lower(); generic+=lower.count('delegat')
            count=lower.count('delegate:')
            if not count: continue
            marker_count+=count; tail=lower.split('delegate:',1)[1]
            token=tail.split()[0].strip(chr(34)+chr(39)+',]}') if tail.split() else ''
            digest=hashlib.sha256(value.encode()).hexdigest()[:16]
            if token in ROLES: classification=token;role_counts[token]+=count
            else: classification='UNMAPPED:'+hashlib.sha256(token.encode()).hexdigest()[:16]
            hits.append({'relative_path':entry['relative_path'],'line':line_no,'field_path':field,'value_sha256_prefix':digest,'classification':classification,'occurrences':count})
    with open(path,'rb') as f:
        if entry['format']=='json':
            raw=f.read(size)
            if len(raw)!=size: raise PrefixError(f'source shortened during read: {entry["relative_path"]}')
            h.update(raw); rows=1
            try: consume(json.loads(raw),1)
            except (json.JSONDecodeError,UnicodeDecodeError): invalid=1
            remaining=0
        else:
            while remaining:
                raw=f.readline(remaining)
                if not raw: raise PrefixError(f'source shortened during read: {entry["relative_path"]}')
                remaining-=len(raw);h.update(raw);rows+=1
                try: consume(json.loads(raw),rows)
                except (json.JSONDecodeError,UnicodeDecodeError): invalid+=1
    after=os.stat(path,follow_symlinks=False)
    if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):
        raise PrefixError(f'source rotated during read: {entry["relative_path"]}')
    if h.hexdigest()!=entry['sha256']:
        raise PrefixError(f'frozen-prefix sha256 drift: {entry["relative_path"]}')
    return {'family':entry['family'],'relative_path':entry['relative_path'],'prefix_bytes':size,'rows':rows,'string_values':total_values,'invalid_records':invalid,'generic_delegat_substrings':generic,'delegate_colon_occurrences':marker_count,'requested_role_occurrences':dict(role_counts),'hits':hits}

def scan(root: str | os.PathLike[str], manifest: str | os.PathLike[str], *, family: str | None=None, path_filter: str | None=None) -> dict[str, Any]:
    entries=read_manifest(manifest)
    if family is not None and family not in {'progress','candidate'}: raise PrefixError(f'unknown family: {family}')
    if path_filter is not None and path_filter not in {r['relative_path'] for r in entries}:
        raise PrefixError(f'path filter not present in manifest: {path_filter}')
    selected=[r for r in entries if (family is None or r['family']==family) and (path_filter is None or r['relative_path']==path_filter)]
    if not selected: raise PrefixError('manifest selection is empty')
    result=[replay_entry(root,r) for r in selected]
    families={}
    for fam in ('progress','candidate'):
        rows=[r for r in result if r['family']==fam]
        if rows:
            families[fam]={'files':len(rows),'prefix_bytes':sum(r['prefix_bytes'] for r in rows),'records':sum(r['rows'] for r in rows),'invalid_records':sum(r['invalid_records'] for r in rows),'string_values':sum(r['string_values'] for r in rows),'generic_delegat_substrings':sum(r['generic_delegat_substrings'] for r in rows),'delegate_colon_occurrences':sum(r['delegate_colon_occurrences'] for r in rows)}
    return {'manifest_file_count':len(entries),'selected_file_count':len(result),'families':families,'requested_role_occurrences':{role:sum(r['requested_role_occurrences'].get(role,0) for r in result) for role in sorted(ROLES)},'unmapped_hit_count':sum(h['classification'].startswith('UNMAPPED:') for r in result for h in r['hits']),'hits':[h for r in result for h in r['hits']],'files':[{k:v for k,v in r.items() if k!='hits'} for r in result]}

def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,help='orchestrator root matching manifest relative paths')
    parser.add_argument('--manifest',required=True,help='prefix_manifest.tsv')
    parser.add_argument('--family',choices=('progress','candidate'))
    parser.add_argument('--path',dest='path_filter',help='optional exact relative_path from manifest')
    parser.add_argument('--output',help='optional JSON output path; otherwise stdout')
    args=parser.parse_args(argv)
    try: result=scan(args.root,args.manifest,family=args.family,path_filter=args.path_filter)
    except PrefixError as exc: parser.error(str(exc))
    rendered=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.output: Path(args.output).write_text(rendered)
    else: print(rendered,end='')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
