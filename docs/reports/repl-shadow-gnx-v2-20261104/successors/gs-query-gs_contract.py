"""Native custody checks only; no quality verdict or grading policy."""
import hashlib
import json


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def seal(record):
    if 'record_sha256' in record:
        raise ValueError('record already sealed')
    return {**record,'record_sha256':digest(canonical(record))}


def validate(record,context_bytes):
    r=dict(record); claimed=r.pop('record_sha256',None)
    if claimed != digest(canonical(r)):
        raise ValueError('record seal mismatch')
    if r.get('context_sha256') != digest(context_bytes):
        raise ValueError('context digest mismatch')
    ctx=json.loads(context_bytes)
    if ctx.get('schema')!='epyc.gs-frozen-query-native-context.v1' or r.get('cohort_sha256')!=ctx.get('cohort_sha256'):
        raise ValueError('context scope mismatch')
    if r.get('phase')!=ctx.get('phase') or not r.get('captured_at'):
        raise ValueError('phase or timestamp mismatch')
    if not r.get('id'):
        raise ValueError('missing query id')
    if r.get('status')=='error':
        if not r.get('error_type'):raise ValueError('missing error type')
    elif type(r.get('token_count_eg2')) is not int or r['token_count_eg2']<1:
        raise ValueError('invalid token count')
    return r
