"""Write ungraded native CAFE-4 case/arm custody; no retrospective warrant.

The launcher must take the live /proc sample while its owned child is running,
read the official grant while held, and pass those observations here. This
writer rechecks their seals; it cannot authenticate a forged caller or recover
observations the launcher did not capture.
"""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from capture_records import parse_native_arms, CaptureError

HEX = re.compile(r'^[0-9a-f]{64}$')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _filehash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def _write_new(path, data):
    with open(path, 'xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())


def _stat(path):
    s=Path(path).stat()
    return dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)


def _grant(path, grant_root, row_id, observed_at):
    p=Path(path).resolve(strict=True); root=Path(grant_root).resolve(strict=True)
    if p.parent != root or p.name != row_id+'.grant': raise CaptureError('not the row grant')
    raw=p.read_bytes()
    try:
        pairs=[x.split('=',1) for x in raw.decode('ascii').split()]
        if any(len(x)!=2 for x in pairs) or len({x[0] for x in pairs})!=len(pairs):raise ValueError()
        fields=dict(pairs)
        if fields.get('kind')=='rowflow-dryrun' or 'dryrun' in fields.get('schema',''):raise ValueError()
        start=dt.datetime.strptime(fields['start'],'%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp()
        end=dt.datetime.strptime(fields['end'],'%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp()
        captured_at=time.time()
        if not fields['regions'] or not start<=observed_at<end or not start<=captured_at<end:raise ValueError()
    except (KeyError,UnicodeError,ValueError):raise CaptureError('invalid or nonofficial grant')
    return {'path':str(p),'sha256':_hash(raw),'text':raw.decode('ascii'),'captured_at':captured_at,'sample_at':observed_at,'regions':fields['regions']}


def _mapped_file(raw, path):
    expected=Path(path).resolve(strict=True); st=expected.stat()
    for line in raw.splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)!=6: continue
        try:
            major,minor=(int(x,16) for x in fields[3].split(':'))
            if (major,minor,int(fields[4]),fields[5])==(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino,str(expected)):
                return True
        except ValueError: continue
    return False


def _validate_context(c, grant_root):
    if not isinstance(c,dict) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',c.get('row_id','')):raise CaptureError('row id')
    if c.get('phase')!='official' or c.get('device')!='cpu' or type(c.get('case_index')) is not int or not 1<=c['case_index']<=8:raise CaptureError('phase, device or case')
    if not isinstance(c.get('sample_time'),(int,float)) or not isinstance(c.get('pid'),int) or c['pid']<=0 or not isinstance(c.get('pid_start_ticks'),int):raise CaptureError('missing process sample')
    if not isinstance(c.get('affinity'),list) or not c['affinity'] or any(type(x) is not int or x<0 for x in c['affinity']):raise CaptureError('missing affinity')
    grant=_grant(c['grant_path'],grant_root,c['row_id'],c['sample_time'])
    model=c['model']
    if not HEX.fullmatch(model.get('sha256','')) or _stat(model['path']) != model.get('stat') or model.get('hash_mode')!='preflight-full-stat-bound':raise CaptureError('model preflight or stat')
    build=c['build']; required=('receipt','compiler','compiler_meta','candidate','source_code','bridge','source_patch','prompt_manifest','runtime_manifest')
    for name in required:
        item=build[name]
        if not HEX.fullmatch(item.get('sha256','')) or _filehash(item['path'])!=item['sha256']:raise CaptureError('build '+name)
    if build.get('source_commit')!='ffc1bac82eeca6f9099e1ccd9ba49703c460a115':raise CaptureError('source commit')
    receipt=json.loads(Path(build['receipt']['path']).read_text())
    if (receipt.get('source_commit')!=build['source_commit'] or receipt.get('mode')!='build' or
        receipt.get('candidate_sha256')!=build['source_code']['sha256'] or receipt.get('bridge_sha256')!=build['bridge']['sha256'] or
        receipt.get('patch_sha256')!=build['source_patch']['sha256'] or receipt.get('frozen_prompt_manifest_sha256')!=build['prompt_manifest']['sha256'] or
        build['candidate']['sha256'] not in receipt.get('files',{}).values() or build['compiler_meta']['sha256'] not in receipt.get('files',{}).values()):raise CaptureError('build receipt binding')
    compiler_cache=Path(build['compiler_meta']['path']).read_text(errors='strict')
    match=re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$',compiler_cache,re.M)
    if not match or os.path.realpath(match.group(1))!=os.path.realpath(build['compiler']['path']):raise CaptureError('compiler identity')
    prompt_manifest=json.loads(Path(build['prompt_manifest']['path']).read_text())
    if prompt_manifest.get('model',{}).get('path')!=model['path'] or prompt_manifest.get('model',{}).get('sha256')!=model['sha256'] or prompt_manifest.get('model',{}).get('stat')!=model['stat']:raise CaptureError('model preflight binding')
    try: expected_prompt=prompt_manifest['prompts'][c['case_index']]['ids']
    except (KeyError,IndexError,TypeError):raise CaptureError('prompt manifest')
    if not isinstance(expected_prompt,list) or not expected_prompt or any(type(x) is not int or x<0 for x in expected_prompt):raise CaptureError('invalid prompt IDs')

    if not isinstance(c.get('argv'),list) or len(c['argv'])!=3 or c['argv'][1]!=model['path'] or c['argv'][2]!=str(c['case_index']):raise CaptureError('request argv')
    libraries=c['mapped_libraries']
    if not isinstance(libraries,dict) or not libraries or not c.get('model_mapped') or not HEX.fullmatch(c.get('proc_maps_sha256','')):raise CaptureError('live mapping')
    for path,h in libraries.items():
        if not HEX.fullmatch(h) or _filehash(path)!=h:raise CaptureError('mapped library')
    executable=build['candidate']
    if os.path.realpath(c['argv'][0])!=os.path.realpath(executable['path']):raise CaptureError('executable mismatch')
    maps=Path(c['proc_maps_path']).read_bytes()
    if _hash(maps)!=c['proc_maps_sha256']:raise CaptureError('mapping sample tampered')
    maps_text=maps.decode('utf-8')
    if not all(_mapped_file(maps_text,p) for p in [model['path'],executable['path'],*libraries]):raise CaptureError('expected mapped inode absent')
    expected_paths={str(Path(p).resolve()) for p in libraries}
    for line in maps_text.splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)==6 and ('/libggml' in fields[5] or '/libllama' in fields[5]) and str(Path(fields[5]).resolve()) not in expected_paths:raise CaptureError('foreign mapped ggml or llama')
    if not isinstance(c.get('child_rc'),int) or not isinstance(c.get('child_reaped'),bool):raise CaptureError('missing child terminal state')
    return grant, expected_prompt


def _native_summary(raw, case_index):
    text=raw.decode('utf-8','strict')
    refs=re.findall(r'^CAFE4_GEOMETRY_REFS prompt=(\d+) off_batch_serial=([^ ]+) off_ckpt_serial=([^ ]+) off_batch_ckpt=([^ ]+) observe_batch_serial=([^ ]+) observe_ckpt_serial=([^ ]+) observe_batch_ckpt=([^\s]+)$',text,re.M)
    rows=re.findall(r'^CAFE4_MTP_ROLLBACK width=(\d+) accepted=(\d+) selected=(\d+) faulted=(\d+) off_error=([^ ]+) observe_error=([^ ]+) fault_error=([^ ]+) off_observe=([^ ]+) fault_observe=([^ ]+) tolerance=([^\s]+)$',text,re.M)
    if len(refs)!=1 or len(rows)!=1 or int(refs[0][0])!=case_index:raise CaptureError('native numerical summary absent')
    numbers=list(map(float,refs[0][1:]))+list(map(float,rows[0][4:]))
    if not all(math.isfinite(n) and n>=0 for n in numbers):raise CaptureError('nonfinite native numerical summary')
    names=('off_batch_serial','off_ckpt_serial','off_batch_ckpt','observe_batch_serial','observe_ckpt_serial','observe_batch_ckpt','off_error','observe_error','fault_error','off_observe','fault_observe','tolerance')
    return {'reference_and_outcomes':dict(zip(names,numbers)),'width':int(rows[0][0]),'accepted':int(rows[0][1]),'selected':int(rows[0][2]),'faulted':int(rows[0][3]),'expected':'matched nonfault and separately injected target fault','observed_result_line': 'PASS' if 'RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges' in text else 'UNKNOWN'}


def write_case(directory, context, native_log, grant_root):
    """Write once; incomplete/tampered records remain UNKNOWN with the raw log.

    No model weights are hashed here: their digest comes from full-stat-bound
    preflight. Native arms have separate exact byte segments and SHA-256 seals.
    The caller must run this during the official grant, before grant deletion.
    """
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    if not isinstance(native_log,bytes):raise TypeError('native_log must be bytes')
    _write_new(root/'native.log',native_log)
    errors=[]; grant=None; arms=[]; expected_prompt=None
    try:grant,expected_prompt=_validate_context(context,grant_root)
    except (CaptureError,KeyError,TypeError,ValueError,OSError) as e:errors.append('provenance: '+str(e))
    try:arms=parse_native_arms(native_log)
    except (CaptureError,UnicodeError) as e:errors.append('native: '+str(e))
    summary=None
    try:
        summary=_native_summary(native_log,context['case_index'])
        if arms and (summary['width']!=len(arms[0]['tokens']['draft']) or summary['accepted']!=arms[0]['tokens']['partial']['accepted'] or summary['selected']!=arms[1]['selected'] or summary['faulted']!=arms[2]['faulted']):raise CaptureError('summary does not match native arms')
    except (CaptureError,KeyError,TypeError,ValueError,UnicodeError) as e:errors.append('summary: '+str(e))
    if arms and expected_prompt is not None and any(a['tokens']['prompt']!=expected_prompt for a in arms):errors.append('native: prompt IDs differ from sealed manifest')
    if not isinstance(context,dict) or context.get('child_reaped') is not True or context.get('child_rc') != 0:errors.append('child incomplete or nonzero')
    for arm in arms:
        data=arm.pop('native_segment').encode();_write_new(root/(arm['arm']+'.native.log'),data)
        arm['native_segment_path']=arm['arm']+'.native.log'
        _write_new(root/(arm['arm']+'.json'),json.dumps(arm,sort_keys=True).encode()+b'\n')
    record={'schema':'cafe4.geometry.native-case.v1','capture_status':'UNKNOWN' if errors else 'CAPTURED_UNGRADED','errors':errors,'native_log':'native.log','native_log_sha256':_hash(native_log),'native_summary':summary,'grant':grant,'context':context,'arms':[{k:v for k,v in arm.items() if k!='tokens'} for arm in arms],'scope':'native custody only; no grading, historical warrant, performance or CAFE-4 closure'}
    encoded=json.dumps(record,sort_keys=True,separators=(',',':')).encode();_write_new(root/'case.json',encoded+b'\n');_write_new(root/'case.sha256',(_hash(encoded)+ '  case.json canonical-json-without-newline\n').encode())
    return record
