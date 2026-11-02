#!/usr/bin/env python3
"""R11 two SMT CPU admission, extending A6's exact affinity check with grant overlap refusal."""
import datetime
import os
from pathlib import Path
import shutil
import importlib.util
import time
_original_path = "/mnt/raid0/llm/tmp/c3-final-image-controls-20261030/gpu-controls/prep_admission.py"
_spec = importlib.util.spec_from_file_location("c3_original_prep_admission", _original_path)
original_admission = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(original_admission)
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')

def live(cpus):
    pair=set(cpus)
    if len(pair)!=2 or any(c<96 or c>183 for c in pair) or set(os.sched_getaffinity(0))!=pair:
        raise RuntimeError('R11 requires exact two approved SMT CPUs 96-183')
    expected={int(t) for t in os.environ.get('R11_CPUS','').split(',') if t}
    if pair!=expected:
        raise RuntimeError('R11 declared CPU pair differs from actual affinity')
    if shutil.disk_usage('/mnt/raid0/llm').free<150*1024**3:
        raise RuntimeError('RAID free below150GiB')
    classes=original_admission.queue_classes((FLAGS/'FILLERS.md').read_text())
    now=time.time()
    for path in (FLAGS/'grants').glob('*.grant'):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('unsafe grant file')
        raw=path.read_text();parts=dict(token.split('=',1) for token in raw.split())
        if set(parts)!={'regions','start','end'}:
            raise RuntimeError('grant schema')
        start,end=[datetime.datetime.fromisoformat(parts[k].replace('Z','+00:00')).timestamp() for k in ('start','end')]
        if start>=end:
            raise RuntimeError('grant interval')
        if not start<=now<end:
            continue
        cls=classes.get(path.name[:-6])
        if cls not in original_admission.CLASSES:
            raise RuntimeError('unclassified active grant')
        claimed=original_admission.regions(parts['regions'])
        if pair & claimed:
            raise RuntimeError('active grant overlaps R11 SMT pair')
        if cls.startswith('block-timing') and {c-96 for c in pair} & claimed:
            raise RuntimeError('active timing grant owns R11 sibling physical cores')
    return {'cpus':sorted(pair),'checked_at':now,'raid_floor_gib':150}
