#!/usr/bin/env python3
import hashlib,json,os,sys
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def full_complete(root):
    root=Path(root)
    try:
        result_path=root/'full-result.json'
        r=json.loads(result_path.read_text())
        provenance=r['provenance']; comparison=r['comparison']; cr=comparison['record']
        if (r.get('schema')!='epyc.r18a.full_build_result.v2' or r.get('mode')!='full'
                or r.get('partial') is not False or r.get('exit_code')!=0
                or r.get('completion_eligible') is not True or r.get('terminal_state')!='complete'):
            return False
        if (provenance.get('source_commit')!='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
                or provenance.get('source_tree')!='a7c564ffbac0a86ce648ef6f11c1748c81a6560d'
                or not provenance.get('source_claim_sha256')
                or not provenance.get('production_recipe_sha256')
                or not provenance.get('verified_anchor_inputs_sha256')
                or not provenance.get('verified_anchor_closure_sha256')):
            return False
        if (comparison.get('state')!='pass' or comparison.get('returncode')!=0
                or not comparison.get('sha256') or not isinstance(cr,dict)
                or cr.get('schema')!='r18a.independent_symbol_identity.v1'
                or cr.get('symbol_identity_pass') is not True):
            return False
        rows=cr.get('comparisons',{})
        if set(('cpu','hip_host','hip_device'))-set(rows):return False
        if any(row.get('added') or row.get('removed') for row in rows.values()):return False
        comparison_path=Path(comparison['path'])
        if sha(comparison_path)!=comparison['sha256'] or json.loads(comparison_path.read_text())!=cr:return False
        terminal_path=root/'full-terminal.jsonl'
        result_sha=sha(result_path)
        matches=[]
        for line in terminal_path.read_text().splitlines():
            try:t=json.loads(line)
            except ValueError:continue
            if t.get('run_id')==r.get('run_id') and t.get('full_result_sha256')==result_sha:
                matches.append(t)
        if len(matches)!=1:return False
        t=matches[0]
        if not (t.get('schema')=='epyc.r18a.full_comparison_terminal.v1'
                and t.get('state')=='complete' and t.get('completion_eligible') is True
                and t.get('comparison',{}).get('state')=='pass'
                and t.get('comparison',{}).get('sha256')==comparison['sha256']
                and t.get('rowflow_result_filed') is True):
            return False
        filed=Path(t['rowflow_result_file'])
        if filed.is_symlink() or not filed.is_file():return False
        filed_records=[json.loads(line) for line in filed.read_text().splitlines() if line.strip()]
        return (len(filed_records)==1
                and filed_records[0].get('schema')=='epyc.r18a.full_comparison_terminal.v1'
                and filed_records[0].get('run_id')==t.get('run_id')
                and filed_records[0].get('full_result_sha256')==result_sha
                and filed_records[0].get('full_result')==r
                and filed_records[0].get('completion_eligible') is True
                and filed_records[0].get('comparison',{}).get('state')=='pass')
    except (OSError,ValueError,KeyError,TypeError):
        return False


def main():
    if os.environ.get('FILLER_DRYRUN')=='1':return 1
    root=Path(sys.argv[1] if len(sys.argv)>1 else '/mnt/raid0/llm/tmp/refactor-r18a-v10-independent-symbols-r3-20261101-candidate-b7/scratch/full')
    return 0 if full_complete(root) else 1


if __name__=='__main__':raise SystemExit(main())
