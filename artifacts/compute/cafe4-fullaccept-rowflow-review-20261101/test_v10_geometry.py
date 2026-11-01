#!/usr/bin/env python3
"""Abstract sampled+draft verification contracts; not a native llama or GPU test."""
import unittest
V=11

def scores(state):
    # Include absolute state, so every corruption is observable independent of argmax.
    target=(state*7+3)%V
    return tuple((1000 if i==target else 0) + state for i in range(V))
def greedy(state): return max(range(V), key=lambda i:scores(state)[i])
def transition(state, tok): return (state*43+tok*17+23)%65521

def check_case(width, cut, fault=None, *, snapshot_capacity=64, target_rc=0, rm_ok=True):
    if not 1<=width<=16 or not 0<=cut<=width:
        return {'status':'UNKNOWN','reason':'invalid width/cut'}
    if fault not in (None,'skip_rollback','state_corruption','altered_replay_input'):
        return {'status':'UNKNOWN','reason':'unknown fault mode'}
    if target_rc!=0:
        return {'status':'UNKNOWN','reason':'decode refusal'}
    if cut<width and (snapshot_capacity<width+1-cut or not rm_ok):
        return {'status':'UNKNOWN','reason':'partial rollback refusal'}
    state0=71; sampled=greedy(state0)
    # Independent serial reference: each state is after sampled + k draft tokens.
    reference=[transition(state0,sampled)]; ref_tokens=[]
    for _ in range(width):
        token=greedy(reference[-1]);ref_tokens.append(token)
        reference.append(transition(reference[-1],token))
    proposed=ref_tokens.copy()
    if cut<width: proposed[cut]=(proposed[cut]+1)%V
    # Actual target verification consumes sampled + all proposed drafts in one batch.
    batch=[sampled]+proposed; states=[state0]; rows=[]
    for tok in batch:
        states.append(transition(states[-1],tok)); rows.append(scores(states[-1]))
    # Target logits at row j predict proposed draft j. Never copy oracle IDs to target output.
    accepted=0
    for j,tok in enumerate(proposed):
        predicted=max(range(V),key=lambda i:rows[j][i])
        if predicted != tok: break
        if rows[j]!=scores(reference[j]):
            return {'status':'UNKNOWN','reason':'pre-rollback row drift'}
        accepted+=1
    if accepted!=cut: return {'status':'UNKNOWN','reason':'unexpected actual cut'}
    # Full acceptance: consume sampled + all drafts and choose bonus; no rollback.
    if accepted==width:
        if fault is not None:
            return {'status':'UNKNOWN','reason':'rollback fault requested in full-accept path'}
        bonus=max(range(V),key=lambda i:rows[-1][i])
        return {'status':'PASS' if rows[-1]==scores(reference[width]) and bonus==greedy(reference[width]) else 'MISMATCH',
                'sampled':sampled,'batch_rows':len(batch),'actual_cut':accepted,
                'rollback_attempted':False,'bonus':bonus,'expected_bonus':greedy(reference[width])}
    # Artificial extra boundary replay for partial cuts, not the literal server rollback recipe.
    retain_count=1+accepted
    keep=retain_count-1
    if fault=='skip_rollback': rollback_state=states[-1]
    elif fault=='state_corruption': rollback_state=(states[keep]+1)%65521
    else: rollback_state=states[keep]
    replay=batch[keep]
    if fault=='altered_replay_input': replay=(replay+1)%V
    replayed=transition(rollback_state,replay)
    expected=reference[accepted]
    return {'status':'PASS' if scores(replayed)==scores(expected) else 'STATE_MISMATCH',
            'sampled':sampled,'batch_rows':len(batch),'actual_cut':accepted,'keep_index':keep,'rollback_attempted':True,
            'extra_boundary_removal_count':width+1-accepted,
            'retained_tokens':batch[:retain_count],'replay_token':replay,
            'post_replay_logits_match':scores(replayed)==scores(expected),
            'altered_input':fault=='altered_replay_input'}

class Geometry(unittest.TestCase):
    def test_all_cuts_including_zero_and_full(self):
        for d in range(1,17):
            for cut in range(d+1):
                with self.subTest(d=d,cut=cut):
                    r=check_case(d,cut)
                    self.assertEqual(r['status'],'PASS')
                    self.assertEqual(r['batch_rows'],d+1)
                    self.assertEqual(r['actual_cut'],cut)
                    if cut==d:
                        self.assertFalse(r['rollback_attempted'])
                        self.assertEqual(r['bonus'],r['expected_bonus'])
                    else:
                        self.assertTrue(r['rollback_attempted'])
                        self.assertEqual(r['keep_index'],cut)
                        self.assertEqual(r['extra_boundary_removal_count'],d+1-cut)
    def test_state_corruption_preserves_input(self):
        good=check_case(5,2); bad=check_case(5,2,'state_corruption')
        self.assertEqual(bad['replay_token'],good['replay_token'])
        self.assertFalse(bad['altered_input'])
        self.assertEqual(bad['status'],'STATE_MISMATCH')
    def test_skipped_removal_has_distinct_state(self):
        self.assertEqual(check_case(5,2,'skip_rollback')['status'],'STATE_MISMATCH')
    def test_altered_input_is_distinct_fault_class(self):
        good=check_case(5,2); bad=check_case(5,2,'altered_replay_input')
        self.assertNotEqual(bad['replay_token'],good['replay_token'])
        self.assertTrue(bad['altered_input'])
        self.assertEqual(bad['status'],'STATE_MISMATCH')
    def test_refusals_are_unknown_not_detection(self):
        self.assertEqual(check_case(5,5,snapshot_capacity=0,rm_ok=False)['status'],'PASS')
        self.assertEqual(check_case(5,2,'unrecognized')['status'],'UNKNOWN')
        self.assertEqual(check_case(5,5,'skip_rollback')['status'],'UNKNOWN')
        self.assertEqual(check_case(5,2,snapshot_capacity=4)['status'],'PASS')
        for kwargs in ({'snapshot_capacity':3},{'target_rc':1},{'rm_ok':False}):
            self.assertEqual(check_case(5,2,**kwargs)['status'],'UNKNOWN')
        for d,cut in ((0,0),(17,1),(3,-1),(3,4)):
            self.assertEqual(check_case(d,cut)['status'],'UNKNOWN')
if __name__=='__main__': unittest.main()
