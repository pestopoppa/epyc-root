"""Prospective producer-authored R18 symbol comparison; never retrofits old runs."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

AUTHORITY = 'measurement'
SOURCE_KIND = 'autokernel-r18-symbols'
ADAPTER_ID = 'vidya.adapters.autokernel_r18_symbols/v1'
SCHEMA = 'epyc.autokernel.r18_symbol_capture.v1'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native_rows(path):
    path=Path(path); root=path.parent
    try:
        terminal=json.loads(path.read_text()); begin=json.loads((root/'begin.json').read_text())
        if terminal.get('schema') != SCHEMA or begin.get('schema') != SCHEMA: return ()
        if terminal.get('state') != 'complete': return ()
        if terminal['begin_sha256'] != sha(root/'begin.json'): raise ValueError('begin digest mismatch')
        if not isinstance(begin.get('synthetic'), bool): raise ValueError('missing synthetic scope')
        if not begin['synthetic']:
            if begin['dependency_manifest']['sha256'] not in ('4c36a479297aa435589ee4604f68d516fe3efdacd535d80c8fc1b6bf1772d425', '5adb079828658d11dd393fa61f3e59712872ae635102c2543c7c9d8823c927fd', '5350aac873b0b3626851912dc44c1d3579467edacb6a999e4acfd70f83a587fd'): raise ValueError('dependency manifest differs from v10 comparator closure')
            pins={'comparator':'08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61', 'anchor_cpu':'3f4edd2fc0f1e78003735be59db987d43c4bc0e6a8f821bc419d7b6f492346c0', 'anchor_hip':'f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'}
            if begin['source']['head'] != 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115' or any(begin['inputs'][k]['sha256'] != v for k,v in pins.items()): raise ValueError('not pinned v10')
        detail=terminal['detail']; result_path=Path(begin['result'])
        full, parent = detail['full_result'], detail['parent_outcome']
        if sha(full['path']) != full['sha256'] or sha(parent['path']) != parent['sha256']: raise ValueError('parent outcome changed')
        full_data, parent_data = json.loads(Path(full['path']).read_text()), json.loads(Path(parent['path']).read_text())
        if (full_data.get('partial') is not False or parent_data.get('partial') is not False
                or full_data.get('exit_code') != detail['returncode'] or parent_data.get('exit_code') != detail['returncode']
                or full_data.get('reason') not in ('independent_cpu_hip_symbol_identity_pass', 'independent_cpu_hip_symbol_identity_valid_negative')): raise ValueError('incomplete parent run')
        if not begin['synthetic'] and detail['capture_script'] != begin['inputs']['set_extractor']: raise ValueError('extractor binding mismatch')
        if sha(result_path) != detail['result_sha256'] or sha(root/'sets/manifest.json') != detail['sets_manifest_sha256']: raise ValueError('result digest mismatch')
        manifest=json.loads((root/'sets/manifest.json').read_text()); result=json.loads(result_path.read_text())
        if manifest['native_result_sha256'] != detail['result_sha256'] or manifest['native_rc'] != detail['returncode']: raise ValueError('manifest result mismatch')
        if manifest['comparator_sha256'] != begin['inputs']['comparator']['sha256']: raise ValueError('comparator mismatch')
        for v in list(begin['inputs'].values()) + list(begin['dependencies'].values()) + [begin['dependency_manifest'], detail['capture_script']]:
            if sha(v['path']) != v['sha256']: raise ValueError('source dependency changed')
        if result.get('schema') != 'r18a.independent_symbol_identity.v1' or 'error' in result: raise ValueError('invalid comparator result')
        if [x['sha256'] for x in manifest['inputs']] != [begin['inputs'][k]['sha256'] for k in ('anchor_cpu','candidate_cpu','anchor_hip','candidate_hip')]: raise ValueError('input binding mismatch')
        rows=result['comparisons']; surfaces=('cpu','hip_host','hip_device')
        if set(rows)!=set(surfaces): raise ValueError('incomplete surfaces')
        expected={f'{s}-{r}.json' for s in surfaces for r in ('anchor','candidate')}
        if set(manifest['artifacts_sha256']) != expected: raise ValueError('incomplete symbol sets')
        for name, digest in manifest['artifacts_sha256'].items():
            if sha(root/'sets'/name)!=digest: raise ValueError('symbol set changed')
        for surface in surfaces:
            a=json.loads((root/'sets'/f'{surface}-anchor.json').read_text()); c=json.loads((root/'sets'/f'{surface}-candidate.json').read_text())
            if a != sorted(set(a)) or c != sorted(set(c)): raise ValueError('invalid set')
            row=rows[surface]
            if (row['anchor_count'] != len(a) or row['candidate_count'] != len(c) or row['added'] != sorted(set(c)-set(a)) or row['removed'] != sorted(set(a)-set(c))): raise ValueError('sets disagree with comparator')
        verdict=all(not row['added'] and not row['removed'] for row in rows.values())
        if result['symbol_identity_pass'] is not verdict or detail['verdict'] is not verdict or detail['returncode'] != (0 if verdict else 1): raise ValueError('verdict mismatch')
        return ({'path':str(path), 'sha256':sha(path), 'begin':begin, 'terminal':terminal, 'result':result},)
    except (OSError, ValueError, KeyError, TypeError) as exc: raise ProjectionError(f'R18 source refused: {exc}') from exc

@register(SOURCE_KIND)
def project(row):
    if row not in native_rows(row['path']): raise ProjectionError('R18 row changed')
    b,t,r=row['begin'],row['terminal'],row['result']; passed=t['detail']['verdict']
    return ClaimTuple(measurement_id='r18-symbol:'+row['sha256'], metric='r18_symbol_identity', value=int(passed),
        date=t['finished_at'], category='CANDIDATE', metric_direction='higher_better', unit='comparison',
        claim=('Independent CPU, HIP host and gfx90a symbol sets '+('matched' if passed else 'differed')+
               ' against the recorded v10 anchors; symbol identity only, not production recipe equivalence'),
        protocol_id='', attestation_path=row['path'], attestation_sha256=row['sha256'], attestation_locator=row['path'],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={'backend':'cpu','build_sha':b['source']['head'],'surface':'autokernel-r18-symbols-synthetic' if b['synthetic'] else 'autokernel-r18-symbols'},
        observation={'outcome_native':'pass' if passed else 'valid_negative'},
        extra={'synthetic':b['synthetic'],'adapter':ADAPTER_ID,'source':b['source'],'inputs':b['inputs'], 'dependencies':b['dependencies'],
               'comparisons':r['comparisons'], 'symbol_sets_manifest_sha256':t['detail']['sets_manifest_sha256']})
