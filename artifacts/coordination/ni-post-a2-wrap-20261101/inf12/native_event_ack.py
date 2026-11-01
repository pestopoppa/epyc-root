"""ACK each distinct native qualification child only after its source-specific validation."""
import json
import os
import pathlib
import subprocess
import sys

import native_proof
import native_full_event

FIRST = 'Accurate_Retrieval__eventqa_65536__base'
FULL = 'Accurate_Retrieval__eventqa_full__base'


def write_once(path, payload):
    path = pathlib.Path(path)
    with path.open('x') as f:
        json.dump(payload, f, sort_keys=True, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())


def handle_event(tag, event_path, ack_path, run_dir, manifest_path, phase, cutoff_event=None, nonce=None):
    run_dir = pathlib.Path(run_dir); ack_path = pathlib.Path(ack_path)
    if ack_path.exists(): raise RuntimeError('native event already ACKed')
    if phase not in ('normal','cutoff'): raise RuntimeError('unknown qualification phase')
    if tag == FIRST:
        first_path = run_dir/'FIRST-REQUEST.json'
        if first_path.exists(): raise RuntimeError('duplicate first native event')
        write_once(first_path,native_proof.first_request(event_path,manifest_path,phase))
        if phase == 'cutoff':
            if not cutoff_event or not nonce: raise RuntimeError('cutoff trigger lacks keeper path/nonce')
            subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('native_cutoff_event.py')),
                            str(first_path),str(cutoff_event),str(nonce)],check=True)
    elif tag == FULL and phase == 'normal':
        if not (run_dir/'FIRST-REQUEST.json').is_file():
            raise RuntimeError('full shape appeared before first native event')
        write_once(run_dir/'FULL-SHAPE-EVENT.json',native_full_event.validate_live(event_path,manifest_path))
    else:
        raise RuntimeError('unexpected native fixture shape or phase')
    with ack_path.open('x') as f:
        f.write('validated\n');f.flush();os.fsync(f.fileno())


if __name__ == '__main__':
    tag,event,ack,run,manifest,phase,*rest=sys.argv[1:]
    handle_event(tag,event,ack,run,manifest,phase,*(rest+[None,None])[:2])
