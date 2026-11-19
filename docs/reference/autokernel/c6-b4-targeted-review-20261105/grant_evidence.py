"""Validate a captured rowflow grant without relying on inner-only environment."""
import hashlib,re

def validate(grant, expected_id, dry):
    if grant.get('FILLER_ID') != expected_id or grant.get('FILLER_NEEDGPU') != '1':
        raise ValueError('row identity or GPU class mismatch')
    if not re.fullmatch(r'[0-9,-]+', grant.get('FILLER_CPUS','')):
        raise ValueError('missing or invalid CPU witness')
    if not re.fullmatch(r'\d+', grant.get('FILLER_DEADLINE','')):
        raise ValueError('missing or invalid deadline')
    raw=grant.get('grant_text','')
    if not raw or hashlib.sha256(raw.encode()).hexdigest()!=grant.get('grant_sha256'):
        raise ValueError('grant snapshot digest mismatch')
    fields={}
    for item in raw.split():
        if '=' not in item: raise ValueError('invalid grant field')
        k,v=item.split('=',1)
        if k in fields: raise ValueError('duplicate grant field')
        fields[k]=v
    if any(not fields.get(k) for k in ('regions','start','end','holds')) or 'mi210_0' not in fields['regions'].split(','):
        raise ValueError('GPU grant regions or window absent')
    if dry and (fields.get('id')!=expected_id or fields.get('kind')!='rowflow-dryrun'):
        raise ValueError('smoke grant identity mismatch')
    if not dry and fields.get('kind')=='rowflow-dryrun':
        raise ValueError('synthetic grant on full result')
