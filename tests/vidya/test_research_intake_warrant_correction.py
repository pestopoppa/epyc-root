import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import research_intake as a
import intake_assertion_kinds
validator_path = ROOT / '.claude/skills/research-intake/scripts/validate_intake.py'
spec = importlib.util.spec_from_file_location('intake_validator_under_test', validator_path)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
from fold import fold, FT_RETRACT
from frames import make_frame
import yaml

AS_OF = '2026-10-06T00:00:00Z'

class MemoryLedger:
    def __init__(self, frames):
        self.frames = list(frames)
        self.calls = 0
        self.fail_at = None
    def read_all(self):
        return [SimpleNamespace(frame=f) for f in self.frames]
    def append(self, frame):
        self.calls += 1
        if self.calls == self.fail_at:
            raise OSError('simulated interrupted fsync sequence')
        self.frames.append(frame)

class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = Path(self.tmp.name) / 'filtered.yaml'
        self.entries = [dict(id='intake-2001', url='https://example.org/a',
                             key_claims=['first', 'second'], verification='stage1-unverified')]
        old = dict(self.entries[0], verification='dive-verified')
        self.old = a._frames_for_entry(old, AS_OF)
        self.ledger = MemoryLedger(self.old)
        self.targets = [dict(entry_id=old['id'], claim_id=f['assertion']['claim_id'],
                             old_support_frame_id=f['frame_id'])
                        for f in self.old if f['frame_type'] == a.FT_SUPPORT]
        self.manifest = dict(targets=self.targets)
    def args(self):
        self.index.write_text(yaml.safe_dump(self.entries))
        return dict(index_path=self.index, target_manifest=self.manifest, as_of=AS_OF,
                    expected_index_sha256=hashlib.sha256(self.index.read_bytes()).hexdigest(),
                    expected_manifest_sha256=hashlib.sha256(json.dumps(
                        self.manifest,sort_keys=True,separators=(',', ':')).encode()).hexdigest())
    def withdraw_args(self):
        by_id = {f['frame_id']: f for f in self.ledger.frames}
        for target in self.targets:
            old = by_id.get(target['old_support_frame_id'])
            if old is None: continue
            target.setdefault('frame_type', old['frame_type'])
            target.setdefault('reason', 'Reviewed scope repair: prior assertion is withdrawn from this current slot; dated history remains unchanged.')
            target.setdefault('old_assertion_sha256', hashlib.sha256(json.dumps(
                old['assertion'], sort_keys=True, separators=(',', ':')).encode()).hexdigest())
            slot = int(target['claim_id'].rsplit('_',1)[1])
            if slot < len(self.entries[0]['key_claims']):
                target.setdefault('current_claim_text_sha256', hashlib.sha256(
                    self.entries[0]['key_claims'][slot].encode()).hexdigest())
        return self.args()
    def run_emit(self):
        return a.emit_read_depth_correction(self.ledger, **self.args())
    def test_demotion_retry_and_unrelated_survives(self):
        unrelated = dict(id='intake-9999', url='https://example.org/b',
                         key_claims=['unrelated'], verification='dive-verified')
        self.ledger.frames += a._frames_for_entry(unrelated, AS_OF)
        first = self.run_emit()
        second = self.run_emit()
        self.assertEqual(len(first['appended_frame_ids']), 4)
        self.assertEqual(second['appended_frame_ids'], [])
        state = fold(self.ledger.frames, as_of=AS_OF)
        for target in self.targets:
            self.assertEqual(state.beliefs[target['claim_id']].pro.q, 1)
        self.assertEqual(state.beliefs['clm_intake_9999_00'].pro.q, 3)
        replacement_claims = {f['assertion'].get('claim_id') for f in self.ledger.frames[len(self.old)+3:]
                              if f['frame_type'] == a.FT_SUPPORT}
        self.assertEqual(replacement_claims, {t['claim_id'] for t in self.targets})
    def test_invalid_final_target_does_not_partially_append(self):
        self.targets[-1]['claim_id'] = 'clm_intake_9999_00'
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
    def test_partial_append_resumes_exact_events(self):
        self.ledger.fail_at = 3
        with self.assertRaises(OSError): self.run_emit()
        self.ledger.fail_at = None
        report = self.run_emit()
        self.assertEqual(len(report['appended_frame_ids']), 2)
        self.assertEqual(len({f['frame_id'] for f in self.ledger.frames}), len(self.ledger.frames))
    def test_manifest_digest_is_externally_pinned(self):
        args = self.args()
        self.manifest['unreviewed_extra'] = True
        with self.assertRaises(ValueError): a.emit_read_depth_correction(self.ledger, **args)
        self.assertEqual(self.ledger.calls, 0)
    def test_index_digest_is_externally_pinned(self):
        args = self.args()
        self.index.write_text(self.index.read_text()+'\n')
        with self.assertRaises(ValueError): a.emit_read_depth_correction(self.ledger, **args)
        self.assertEqual(self.ledger.calls, 0)
    def test_duplicate_targets_and_extra_entries_refused(self):
        self.targets.append(dict(self.targets[0]))
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
        self.targets.pop()
        self.entries.append(dict(self.entries[0], id='intake-3001'))
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
    def test_preexisting_foreign_retraction_refused_by_effective_fold(self):
        self.ledger.frames.append(make_frame(frame_type=FT_RETRACT,
            assertion={'retracts': self.targets[-1]['old_support_frame_id']},
            provenance={'method': 'someone-else'}, actor='someone-else',
            authority_scope='research-verification', created_at=AS_OF))
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
    def test_generated_frame_validation_is_before_first_append(self):
        original = a.make_frame
        def fail_last(**kwargs):
            if kwargs['frame_type'] == a.FT_SUPPORT and kwargs['assertion']['claim_id'].endswith('_01'):
                if 'correction_method' in kwargs['provenance']:
                    raise ValueError('invalid final replacement')
            return original(**kwargs)
        with patch.object(a, 'make_frame', side_effect=fail_last):
            with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
    def test_changed_timestamp_cannot_resume_partial_retractions(self):
        self.ledger.fail_at = 2
        with self.assertRaises(OSError): self.run_emit()
        self.ledger.fail_at = None
        args = self.args()
        args['as_of'] = '2026-10-06T00:01:00Z'
        with self.assertRaises(ValueError): a.emit_read_depth_correction(self.ledger, **args)
    def test_invalid_later_entry_is_all_upfront(self):
        self.entries.append(dict(id='intake-3001', verification='dive-verified'))
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)

    def test_real_ledger_retry_preserves_hash_chain(self):
        from ledger import Ledger
        self.ledger = Ledger(Path(self.tmp.name) / 'ledger.jsonl')
        for frame in self.old: self.ledger.append(frame)
        self.run_emit()
        before = self.ledger.path.read_bytes()
        self.run_emit()
        self.assertEqual(before, self.ledger.path.read_bytes())
        self.assertEqual(self.ledger.verify(), [])
    def test_omitted_duplicate_active_warrant_refused(self):
        old_entry = dict(self.entries[0], verification='dive-verified')
        self.ledger.frames += a._frames_for_entry(old_entry, '2026-10-05T00:00:00Z')
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)
    def test_per_claim_overturned_is_not_silently_demoted(self):
        self.entries[0]['claim_corrections'] = [dict(claim_index=1, effect='overturned')]
        with self.assertRaises(ValueError): self.run_emit()
        self.assertEqual(self.ledger.calls, 0)

    def test_withdraw_only_retains_verified_sibling_and_is_idempotent(self):
        self.entries[0]['verification'] = 'dive-verified'
        self.entries[0]['key_claims'][0] = 'Record status: withdrawn from verified source scope'
        self.targets.pop()
        report = a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())
        self.assertEqual(len(report['appended_frame_ids']), 1)
        self.assertEqual(self.ledger.frames[-1]['frame_type'], FT_RETRACT)
        state = fold(self.ledger.frames, as_of=AS_OF)
        self.assertEqual(state.beliefs['clm_intake_2001_00'].pro.q, 0)
        self.assertEqual(state.beliefs['clm_intake_2001_01'].pro.q, 3)
        self.assertEqual(a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())['appended_frame_ids'], [])
        with self.assertRaises(ValueError): self.run_emit()
    def test_withdraw_only_wrong_native_target_refused(self):
        self.entries[0]['verification'] = 'dive-verified'
        self.targets[0]['old_support_frame_id'] = self.old[0]['frame_id']
        with self.assertRaises(ValueError): a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())
        self.assertEqual(self.ledger.calls, 0)
    def test_withdraw_only_invalid_after_valid_has_zero_mutation(self):
        self.entries[0]['verification'] = 'dive-verified'
        self.targets[-1]['claim_id'] = 'clm_intake_9999_00'
        with self.assertRaises(ValueError): a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())
        self.assertEqual(self.ledger.calls, 0)

    def opposition_fixture(self):
        self.entries[0]['verification'] = 'dive-verified'
        old = dict(self.entries[0], claim_corrections=[dict(claim_index=0,effect='overturned')])
        self.ledger = MemoryLedger(a._frames_for_entry(old, AS_OF))
        opposed = next(f for f in self.ledger.frames if f['frame_type'] == a.FT_OPPOSE)
        self.targets[:] = [dict(entry_id=old['id'], claim_id=opposed['assertion']['claim_id'],
                                old_support_frame_id=opposed['frame_id'])]
        self.entries[0]['key_claims'][0] = 'Current corrected assertion; prior false assertion remains explicitly refuted in dated history'
    def test_opposition_withdrawal_preserves_sibling_and_exact_retry(self):
        self.opposition_fixture()
        report = a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())
        self.assertEqual(len(report['appended_frame_ids']), 1)
        after = fold(self.ledger.frames, as_of=AS_OF)
        self.assertEqual(after.beliefs['clm_intake_2001_00'].con.q, 0)
        self.assertEqual(after.beliefs['clm_intake_2001_01'].pro.q, 3)
        self.assertEqual(a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())['appended_frame_ids'], [])
    def test_opposition_wrong_direction_or_scope_has_zero_mutation(self):
        self.opposition_fixture()
        args = self.withdraw_args()
        self.targets[0]['frame_type'] = a.FT_SUPPORT
        args = self.args()
        with self.assertRaises(ValueError): a.emit_warrant_withdrawal(self.ledger, **args)
        self.assertEqual(self.ledger.calls, 0)
        self.targets[0]['frame_type'] = a.FT_OPPOSE
        self.targets[0]['current_claim_text_sha256'] = '0'*64
        with self.assertRaises(ValueError): a.emit_warrant_withdrawal(self.ledger, **self.args())
        self.assertEqual(self.ledger.calls, 0)
    def test_opposition_invalid_late_target_has_zero_mutation(self):
        self.opposition_fixture()
        self.targets.append(dict(self.targets[0], old_support_frame_id='missing-final-frame'))
        with self.assertRaises(ValueError): a.emit_warrant_withdrawal(self.ledger, **self.withdraw_args())
        self.assertEqual(self.ledger.calls, 0)

class RecordStatusTests(unittest.TestCase):
    def entry(self,verification='dive-verified'):
        return dict(id='intake-2001',url='https://example.org/a',key_claims=['source finding','administrative read status'],verification=verification,dive_corrections='Dated old finding remains historical.')
    def mark(self,e):
        e['claim_assertion_kinds']=[dict(claim_index=1,kind='record_status',current_claim_text_sha256=hashlib.sha256(e['key_claims'][1].encode()).hexdigest(),reason='Reviewed current record status, not source evidence.')]
        return e
    def ingest(self,entries,ledger):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'index.yaml';path.write_text(yaml.safe_dump(entries))
            return a.ingest_intake_index(ledger,index_path=path,as_of=AS_OF)
    def test_default_frame_bytes_unchanged(self):
        for verification in ['stage1-unverified','dive-verified','dive-overturned']:
            e=self.entry(verification)
            frames=a._frames_for_entry(e,AS_OF)
            self.assertEqual(len([f for f in frames if f['frame_type']==a.FT_CLAIM]),2)
            self.assertEqual(len([f for f in frames if f['frame_type'] in (a.FT_SUPPORT,a.FT_OPPOSE)]),2)
            self.assertTrue(all('assertion_kind' not in f['assertion'] for f in frames if f['frame_type']==a.FT_CLAIM))
            explicit=copy.deepcopy(e);explicit['claim_assertion_kinds']=[]
            self.assertEqual(frames,a._frames_for_entry(explicit,AS_OF))
    def test_explicit_source_claim_frames_unchanged(self):
        e=self.mark(self.entry());e['claim_assertion_kinds'][0]['kind']='source_claim'
        legacy=copy.deepcopy(e);legacy.pop('claim_assertion_kinds')
        self.assertEqual(a._frames_for_entry(e,AS_OF),a._frames_for_entry(legacy,AS_OF))
    def test_status_suppresses_both_directions_preserves_siblings_history(self):
        for verification,direction in [('dive-verified',a.FT_SUPPORT),('dive-overturned',a.FT_OPPOSE)]:
            e=self.mark(self.entry(verification));frames=a._frames_for_entry(e,AS_OF)
            evidence=[f for f in frames if f['frame_type'] in (a.FT_SUPPORT,a.FT_OPPOSE)]
            self.assertEqual(len(evidence),1);self.assertEqual(evidence[0]['frame_type'],direction)
            self.assertEqual(evidence[0]['assertion']['claim_id'],'clm_intake_2001_00')
            claims=[f for f in frames if f['frame_type']==a.FT_CLAIM]
            self.assertEqual(len(claims),2);self.assertEqual(claims[1]['assertion']['assertion_kind'],'record_status')
            self.assertEqual(len([f for f in frames if f['frame_type']==a.FT_CORRECTION]),1)
    def test_uncertain_stays_existing_grade_rule(self):
        e=self.mark(self.entry());e['claim_corrections']=[dict(claim_index=1,effect='uncertain',note='Historical scope note')]
        self.assertFalse(any(f['frame_type'] in (a.FT_SUPPORT,a.FT_OPPOSE) and f['assertion']['claim_id']=='clm_intake_2001_01' for f in a._frames_for_entry(e,AS_OF)))
        legacy=copy.deepcopy(e);legacy.pop('claim_assertion_kinds')
        evidence=[f for f in a._frames_for_entry(legacy,AS_OF) if f['frame_type']==a.FT_SUPPORT and f['assertion']['claim_id']=='clm_intake_2001_01']
        self.assertEqual(len(evidence),1)
        self.assertEqual(evidence[0]['assertion']['grade']['Q'],'Verified')
    def test_fresh_ordinary_ingest_no_status_warrant(self):
        ledger=MemoryLedger([]);report=self.ingest([self.mark(self.entry())],ledger)
        self.assertEqual(report['claims_seen'],2);self.assertEqual(sum(report['grade_distribution'].values()),1)
        self.assertEqual(len([f for f in ledger.frames if f['frame_type']==a.FT_SUPPORT]),1)
        self.assertEqual(len([f for f in ledger.frames if f['frame_type']==a.FT_CLAIM]),2)
    def test_bad_late_entry_zero_appends(self):
        bad=self.mark(self.entry());bad['key_claims'][1]+=' changed'
        ledger=MemoryLedger([])
        with self.assertRaises(ValueError):self.ingest([self.entry(),bad],ledger)
        self.assertEqual(ledger.calls,0)
    def test_malformed_metadata_adapter_validator_agree(self):
        mutations=[lambda e:e.update(claim_assertion_kinds=None),lambda e:e.update(claim_assertion_kinds={}),lambda e:e['claim_assertion_kinds'].append(copy.deepcopy(e['claim_assertion_kinds'][0])),lambda e:e['claim_assertion_kinds'][0].update(claim_index=True),lambda e:e['claim_assertion_kinds'][0].update(claim_index=-1),lambda e:e['claim_assertion_kinds'][0].update(claim_index=2),lambda e:e['claim_assertion_kinds'][0].update(kind='maybe'),lambda e:e['claim_assertion_kinds'][0].update(reason=' '),lambda e:e['claim_assertion_kinds'][0].update(reason=4),lambda e:e['claim_assertion_kinds'][0].update(current_claim_text_sha256='0'*64),lambda e:e['claim_assertion_kinds'][0].update(current_claim_text_sha256='A'*64),lambda e:e['claim_assertion_kinds'].append('bad')]
        for mutate in mutations:
            e=self.mark(self.entry());mutate(e)
            for fn in [a._validated_assertion_kinds,v._validated_assertion_kinds]:
                with self.subTest(mutate=mutate,fn=fn),self.assertRaises(ValueError):fn(e)
    def test_exact_unicode_text_binding(self):
        self.assertIs(a._validated_assertion_kinds, v._validated_assertion_kinds)
        self.assertIs(a._validated_assertion_kinds, intake_assertion_kinds.validate_assertion_kinds)
        e=self.entry();e['key_claims'][1]='status\u00a0text';self.mark(e)
        self.assertEqual(a._validated_assertion_kinds(e),v._validated_assertion_kinds(e))
        e['key_claims'][1]='status text'
        with self.assertRaises(ValueError):a._frames_for_entry(e,AS_OF)
    def test_withdraw_accepts_status_claim_without_fresh_warrant(self):
        fixture=CorrectionTests(methodName='test_withdraw_only_retains_verified_sibling_and_is_idempotent')
        fixture.setUp()
        try:
            fixture.entries=[self.mark(self.entry())]
            fixture.targets=[t for t in fixture.targets if t['claim_id']=='clm_intake_2001_01']
            fixture.manifest['targets']=fixture.targets
            args=fixture.withdraw_args()
            sibling=next(f for f in fixture.ledger.frames if f['frame_type']==a.FT_SUPPORT and f['assertion']['claim_id']=='clm_intake_2001_00')
            before=list(fixture.ledger.frames)
            a.emit_warrant_withdrawal(fixture.ledger,**args)
            added=fixture.ledger.frames[len(before):]
            self.assertEqual(len([f for f in added if f['frame_type']==FT_RETRACT]),1)
            self.assertFalse(any(f['frame_type'] in (a.FT_SUPPORT,a.FT_OPPOSE) for f in added))
            state=fold(fixture.ledger.frames,as_of=AS_OF)
            self.assertNotIn(sibling['frame_id'],state.beliefs['clm_intake_2001_00'].retracted_support)
        finally: fixture.doCleanups()


if __name__ == '__main__': unittest.main()
