"""PROPOSED ROOT adapter: source-authored SC55 labels, existing measurement ladder only."""
from claim_tuple import ClaimTuple, ProjectionError, register
import hashlib,os,stat,sys,types
from pathlib import Path

PROJECTION_NAME='graph-profiler-measurement'
ADAPTER_ID='vidya.adapters.graph_profile_measurement/v1'
AUTHORITY='measurement'

RESEARCH_ROOT=Path('/workspace/repos/epyc-inference-research')
SOURCE_PINS={
    'graph_profile_capture': 'a30ce214a9d33f8a8994d0e6064854f1fa0259df389000e7783d584e042fe05f',
    'graph_profile_reader': '70ab69e831c45a7344657dc267d1bdb82b7305677612b545ed7b1d118ea94b14',
}

def decoder_source(root,name,pin):
    path=Path(root)/'scripts/kernel_rnd/autokernel/loop'/(name+'.py')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);initial=os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or (before.st_dev,before.st_ino)!=(initial.st_dev,initial.st_ino):
            raise ProjectionError('SC55 decoder source locator is unsafe')
        chunks=[]
        while True:
            block=os.read(fd,1<<20)
            if not block:break
            chunks.append(block)
        raw=b''.join(chunks);after=os.fstat(fd);last=os.lstat(path)
        if (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns) or (after.st_dev,after.st_ino)!=(last.st_dev,last.st_ino) or hashlib.sha256(raw).hexdigest()!=pin:
            raise ProjectionError('SC55 decoder source identity differs from accepted pin')
        return path,raw
    finally:os.close(fd)

def decode(seal_ref, *, from_file=False):
    # Load only the two exact accepted files. No PYTHONPATH, private sibling tree or unchecked loader re-read.
    import uuid
    namespace='vidya_sc55_native_'+uuid.uuid4().hex
    package=types.ModuleType(namespace);package.__path__=[]
    owned={namespace:package};sys.modules[namespace]=package
    try:
        for name,pin in SOURCE_PINS.items():
            path,raw=decoder_source(RESEARCH_ROOT,name,pin)
            fullname=namespace+'.'+name;module=types.ModuleType(fullname)
            module.__file__=str(path);module.__package__=namespace
            owned[fullname]=module;sys.modules[fullname]=module;setattr(package,name,module)
            exec(compile(raw,str(path),'exec'),module.__dict__)
        if from_file:
            # Observe only sealed-file custody here; all run labels remain writer-authored.
            seal_ref=owned[namespace+'.graph_profile_capture'].receipt(Path(seal_ref).absolute())
        captured=owned[namespace+'.graph_profile_reader'].read(seal_ref)
        return (captured,seal_ref) if from_file else captured
    finally:
        for name,module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:del sys.modules[name]

def checked_decode(ref):
    try:return decode(ref)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        raise ProjectionError('SC55 retained originals or provenance refused') from exc

def label_complete(metadata, metric):
    return metadata['date'] is not None and metric['attestation_role'] is not None

def native_rows(seal_ref):
    try:capture=checked_decode(seal_ref)
    except ProjectionError:return ()
    metadata=capture['measurement_metadata']
    return tuple({'seal_ref':seal_ref,'measurement_id':metric['measurement_id']}
            for metric in metadata['metrics'] if label_complete(metadata,metric))

def native_rows_file(seal_path):
    if not isinstance(seal_path,(str,Path)):
        raise ProjectionError('SC55 file source requires a sealed-file path')
    try:capture,seal_ref=decode(seal_path,from_file=True)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        raise ProjectionError('SC55 sealed file custody or native provenance refused') from exc
    metadata=capture['measurement_metadata']
    return tuple({'seal_ref':seal_ref,'measurement_id':metric['measurement_id']}
            for metric in metadata['metrics'] if label_complete(metadata,metric))

@register(PROJECTION_NAME, source_class='measurement')
def project(native):
    if type(native) is not dict or set(native)!={'seal_ref','measurement_id'}:
        raise ProjectionError('SC55 native row requires its retained seal and recorded metric identity')
    capture=checked_decode(native['seal_ref'])
    metadata=capture['measurement_metadata']
    metrics=[item for item in metadata['metrics'] if item['measurement_id']==native['measurement_id']]
    if len(metrics)!=1:raise ProjectionError('missing or ambiguous recorded metric')
    metric=metrics[0]
    if not label_complete(metadata,metric):raise ProjectionError('missing native measurement labels; zero tuples')
    selector=metric['selector']
    records=capture['nodes' if selector['kind']=='node' else 'paths']
    matches=[row for row in records if row['idx' if selector['kind']=='node' else 'path']==selector['identity']]
    if len(matches)!=1:raise ProjectionError('missing native metric sample')
    record=matches[0];role=metric['attestation_role']
    original=capture['native_artifacts'][role] if role is not None else None
    # These counts are original native measurements, not newly invented experimental repeats.
    reps=record['evals'] if selector['kind']=='node' else capture['semantics']['accumulated_evals']
    return ClaimTuple(measurement_id=metric['measurement_id'],metric=metric['metric'],
        value=record[selector['field']],date=metadata['date'],
        category=metadata['category'],claim=metric['claim'],metric_direction=metric['metric_direction'],
        protocol_id=metadata['protocol_id'] if metadata['protocol_id'] is not None else '',
        reps=reps,reps_basis=metric['reps_basis'],unit=metric['unit'],
        attestation_path='',attestation_locator=original['path'] if original else '',
        attestation_sha256=original['sha256'] if original else '',
        attestation_present=True if original else None,attestation_verified=True if original else None,
        source_kind=PROJECTION_NAME,extra={'seal_sha256':native['seal_ref']['sha256'],
            'selector':selector,'native_labels_recorded_before_run':True,'protocol_id_present':metadata['protocol_id'] is not None,
            'thread_availability':capture['thread_availability'],
            'limitations':capture['limitations']+['instrumented profiler observation only; no production performance or promotion warrant',
                'native graph evaluations are not independent experimental repetitions']})
