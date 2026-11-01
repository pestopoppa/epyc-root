"""Completion predicate for exhausted work, not a scientific pass predicate."""
import hashlib,json,sys
from pathlib import Path

def complete(run_dir, expected_clips, expected_cells):
    run=Path(run_dir);terminal=run/'TERMINAL.json'
    x=json.loads(terminal.read_text()); counts=x['counts']
    if x['mode']!='full' or x['original_clips']!=expected_clips or x['cells']!=expected_cells:
        return False
    if set(counts)!={'ok','failure','unknown'} or any(type(v) is not int or v < 0 for v in counts.values()):return False
    if sum(counts.values()) != expected_clips*expected_cells:return False
    if counts['unknown']:
        m=json.loads((run/'EXHAUSTED.json').read_text())
        return (x['state']=='inconclusive_exhausted' and x['partial'] is True
                and m.get('schema')=='cs8.lex2.inconclusive_exhausted.v1'
                and m.get('terminal_sha256')==hashlib.sha256(terminal.read_bytes()).hexdigest()
                and m.get('unknown_n')==counts['unknown'] and m.get('scientific_completion') is False)
    return x['partial'] is False and x['state']==('incomplete_raw' if counts['failure'] else 'complete_raw')

if __name__=='__main__':
    try: ok=complete(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]))
    except (OSError,ValueError,KeyError,IndexError,json.JSONDecodeError):ok=False
    raise SystemExit(0 if ok else 1)
