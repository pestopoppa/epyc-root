"""Prospective bridge from a frozen LEX2 dev score and native bundle to Speech rows.

Do not use on a historical run: only rows with contemporaneous capture can pass
strict adapter validation. The caller supplies all non-score context; none is inferred.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


def verify_score_replay(score_path, scorer_dir, tmp_parent):
    """Re-run the declared original scorer against its native cohort and compare bytes.

    The replay must have the same immutable sources, data and results; it never opens test.
    A mere digest of a caller-supplied report is not a source binding.
    """
    source=Path(scorer_dir).resolve(); score_path=Path(score_path)
    spec=json.loads((source/'SCORER-PREDECLARED.json').read_text())
    def sha(path):
        h=hashlib.sha256()
        with Path(path).open('rb') as f:
            for block in iter(lambda:f.read(1048576),b''): h.update(block)
        return h.hexdigest()
    for relative, expected in spec['source_sha256'].items():
        if sha(source/relative) != expected: raise ValueError('pinned scorer source mismatch: '+relative)
    with tempfile.TemporaryDirectory(prefix='lex2-replay-',dir=tmp_parent) as td:
        dest=Path(td)
        for name in ('score_dev.py','grid_job.py'): shutil.copyfile(source/name,dest/name)
        for name in ('SCORER-PREDECLARED.json','SOURCE-SHA256SUMS','CONVERSATION-CONTEXTS.json',
                     'DOMAIN-LEXICON-PROPOSAL.json','research-scorer-snapshot','run'):
            (dest/name).symlink_to(source/name,target_is_directory=(source/name).is_dir())
        runner=("import pathlib,runpy,sys;sys.path.insert(0,sys.argv[1]);import grid_job;"
                "grid_job.N=pathlib.Path(sys.argv[2]);runpy.run_path(sys.argv[1]+'/score_dev.py',run_name='__main__')")
        proc=subprocess.run([sys.executable,'-c',runner,str(dest),str(source/'install/bin/nemo-speech')],
                            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=840,check=False)
        if proc.returncode != 0: raise ValueError('frozen scorer replay failed: '+proc.stderr[-2000:])
        if sha(dest/'DEV-SELECTION.json') != sha(score_path):
            raise ValueError('score is not reproduced by pinned native inputs')


def emit(adapter, score_path, output_dir, run_id, producer, cells, harness, *, scorer_dir, emitted_at=None):
    score_path=Path(score_path)
    verify_score_replay(score_path,scorer_dir,output_dir)
    score=json.loads(score_path.read_text())
    if score.get('schema')!='cs8.lex2.dev-selection.v1' or score.get('test_opened') is not False:
        raise ValueError('expected dev-only frozen score')
    records=[]
    for key, source_fields in cells.items():
        cell=score['cells'][key]
        bundle=json.loads(Path(source_fields['native_capture_path']).read_text())
        if score.get('dev_manifest_sha256') != source_fields.get('dev_manifest_sha256') or score.get('raw_terminal_sha256') != bundle.get('terminal_sha256') or score.get('scorer_predeclared_sha256') != source_fields.get('scorer_predeclared_sha256'):
            raise ValueError('score predeclaration, raw terminal, or dev manifest mismatch')
        for item in bundle['items']:
            attempt_path=Path(item['attempt_path']).resolve(); disposition_path=Path(item['disposition_path']).resolve()
            if attempt_path.parent != (Path(scorer_dir)/'run').resolve() or disposition_path.parent != attempt_path.parent:
                raise ValueError('capture is not in scorer native run directory')
            attempt=json.loads(attempt_path.read_text())
            disposition=json.loads(disposition_path.read_text())
            result_path=Path(disposition['result_path']).resolve()
            if not attempt_path.name.endswith('.belief-attempt.json') or result_path != attempt_path.with_name(attempt_path.name.replace('.belief-attempt.json','.result.json')) or disposition_path != attempt_path.with_name(attempt_path.name.replace('.belief-attempt.json','.belief-disposition.json')):
                raise ValueError('native capture and scorer result identity mismatch')
            actual='|'.join(map(str,(attempt['engine'],attempt['scope'],attempt['configured_alpha'])))
            if actual != key: raise ValueError('score cell and native arm mismatch')
        if cell.get('n') != source_fields.get('n'):
            raise ValueError('native count / scored count mismatch')
        for score_column, case_policy in (("folded", "casefold"), ("sensitive", "case_sensitive")):
            measurement=cell[score_column]
            counts=measurement['counts']; tp=counts['tp']; fp=counts['fp']; fn=counts['fn']
            metrics={'lexicon_keyword_f':measurement['f'],
                     'lexicon_term_precision':tp/(tp+fp) if tp+fp else None,
                     'lexicon_term_recall':tp/(tp+fn) if tp+fn else None}
            # The declared masked WER is casefolded only, and must not be duplicated.
            if score_column == 'folded':
                metrics['lexicon_non_list_word_wer']=measurement['non_list_wer']
            fields=dict(source_fields)
            fields['lex2_native_schema']='epyc.cs8.lex2.prospective.v1'
            fields['case_policy']=case_policy
            fields.update(keyword_f=metrics['lexicon_keyword_f'],term_precision=metrics['lexicon_term_precision'],
                          term_recall=metrics['lexicon_term_recall'],non_list_word_wer=metrics.get('lexicon_non_list_word_wer'))
            for metric,value in metrics.items():
                if value is None: continue
                records.append(dict(record_kind='stt_lexicon_trial',subject=key+':'+case_policy,metric=metric,value=value,unit='ratio',
                    metric_direction=adapter.METRIC_DIRECTIONS[metric],category='CANDIDATE',protocol_id=None,
                    harness=harness,fields=fields))
    if not records: raise ValueError('no defined score values')
    return adapter.write_belief_measurements(output_dir,run_id=run_id,producer=producer,
        results_path=score_path,records=records,emitted_at=emitted_at)
