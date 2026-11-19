import hashlib,json,os,pathlib,sys
B=pathlib.Path(__file__).resolve().parent
ID='kpf50-own-child-map-acquisition-r3-20261105'
def require(v):
    if not v: raise ValueError('qualification evidence incomplete')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def permission(r):return r['status']=='UNKNOWN' and any(x in r.get('reason','') for x in ('PermissionError','Operation not permitted','Permission denied'))
def identity(r,parent):
    require(type(r['pid']) is int and r['pid']>0 and r['ppid']==parent and type(r['birth_ticks']) is int and r['birth_ticks']>0)
    require(r['state'] not in ('Z','X') and len(r['stat_sha256'])==64)
def clocks(r):require(r['clock']=='CLOCK_MONOTONIC_RAW' and 0<r['pre_spawn_clock_ns']<=r['begin_ns']<=r['end_ns'])
try:
    receipt=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(B/'out'/'RESULT.json')))
    raw=receipt.read_bytes();r=json.loads(raw)
    mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
    root=pathlib.Path(r['root']).resolve();require(root.parent==B/'out'/mode)
    require((root/'RESULT.json').read_bytes()==raw)
    require(r['id']==ID and r['mode']==mode and r['scientific_validity']=='UNKNOWN')
    require(len(r['affinity'])==(4 if mode=='smoke' else 24) and len(set(r['affinity']))==len(r['affinity']))
    allowed={'SMOKE_REFUSAL_OBSERVED','SMOKE_ACQUISITION_QUALIFIED'} if mode=='smoke' else {'ACQUISITION_QUALIFIED'}
    require(r['status'] in allowed)
    cases={x['case']:x for x in r['records']};require(len(cases)==len(r['records']))
    require(cases['zero-padding-control']['canonical_range']=='420000-763000' and cases['zero-padding-control']['padded_mutation_rejected'] is True)
    malformed=cases['malformed-bound']['record'];clocks(malformed)
    require(malformed['status']=='UNKNOWN' and 'invalid read bound' in malformed['reason'] and malformed['mappings']==[])
    honest=cases['honest']['record'];clocks(honest);identity(honest['before'],r['supervisor_pid'])
    expected_cases={'zero-padding-control','malformed-bound','honest'}
    actual_children=[honest]
    if r['status']=='SMOKE_REFUSAL_OBSERVED':
        require(mode=='smoke' and permission(honest))
    else:
        expected_cases.add('denied');denied=cases['denied']['record'];actual_children.append(denied)
        clocks(denied);identity(denied['before'],r['supervisor_pid']);require(permission(denied))
        require(honest['status']=='OBSERVED_FILE_RANGES' and honest['mechanism']=='parent-pinned-inherited-fd')
        identity(honest['after'],r['supervisor_pid'])
        require((honest['before']['pid'],honest['before']['birth_ticks'])==(honest['after']['pid'],honest['after']['birth_ticks']))
        require(digest(honest['maps_raw'].encode())==honest['maps_sha256']==honest['maps_after_sha256'])
        rawmaps={line.split(None,5)[0]:line.split(None,5) for line in honest['maps_raw'].splitlines()}
        pins=r['pinned_files'];require(set(pins)=={'executable','private_dso'})
        expected={}
        runtime=json.loads((B/'runtime.json').read_text())
        require(pins['executable']['sha256']==runtime[pins['executable']['path']])
        require(pins['private_dso']['sha256']==runtime['/lib/x86_64-linux-gnu/libm.so.6'])
        require(pathlib.Path(pins['private_dso']['path']).resolve()==root/'libggml-qualification-private.so')
        for pin in pins.values():
            p=pathlib.Path(pin['path']);data=p.read_bytes();st=p.stat();require(digest(data)==pin['sha256'])
            expected[pin['fd']]=(pin,data,st)
        seen=set();require(honest['mappings'])
        for row in honest['mappings']:
            require(row['status']=='OBSERVED_FILE_RANGE')
            fd=row['parent_retained_fd'];pin,data,st=expected[fd];seen.add(fd)
            require(row['spawn_inherited_fd']==fd)
            require(row['file_stat_pre_spawn']==row['file_stat_before']==row['file_stat_after'])
            require(row['file_sha256_pre_spawn']==row['file_sha256_before']==row['file_sha256_after']==pin['sha256'])
            require(row['file_stat_before'][:3]==[st.st_dev,st.st_ino,st.st_size])
            parts=rawmaps[row['range']];require(len(parts)==6 and 'x' in parts[1] and row['permissions']==parts[1])
            require(row['file_offset']==int(parts[2],16) and row['dev']==parts[3] and row['inode']==int(parts[4])==st.st_ino and row['pathname_observed']==parts[5])
            major,minor=(int(x,16) for x in row['dev'].split(':'));require((major,minor)==(os.major(st.st_dev),os.minor(st.st_dev)))
            begin,end=(int(x,16) for x in row['range'].split('-'));require(row['observed_bytes']==end-begin)
            start=row['file_offset'];require(len(data[start:start+end-begin])==end-begin and digest(data[start:start+end-begin])==row['range_sha256'])
            require(honest['begin_ns']<=row['clock_ns']<=honest['end_ns'])
        require(seen==set(expected))
    require(set(cases)==expected_cases and len(r['cleanup'])==len(actual_children))
    for child,cleanup in zip(actual_children,r['cleanup']):
        require(child['supervisor_pid']==r['supervisor_pid'])
        require(cleanup['pid']==child['before']['pid'] and cleanup['birth_ticks']==child['before']['birth_ticks'])
        require(cleanup['captured_process_absent'] is True and cleanup['descendants_verified'] is False and type(cleanup['returncode']) is int)
    good=True
except (OSError,ValueError,KeyError,TypeError,IndexError):good=False
sys.exit(0 if good else 1)
