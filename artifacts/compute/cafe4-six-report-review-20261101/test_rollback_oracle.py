#!/usr/bin/env python3
"""Synthetic contract fixtures only; never infer llama.cpp or hardware correctness."""
import unittest
VOCAB=7

def logits(state):
    return tuple(-abs(((state * 17 + 11) % VOCAB) - i) for i in range(VOCAB))
def greedy(state):
    return max(range(VOCAB), key=lambda token: logits(state)[token])
def advance(state, token):
    return (state * 31 + token * 13 + 5) % 997
def reference(seed, n):
    rows=[]; state=seed
    for _ in range(n):
        scores=logits(state); token=greedy(state)
        rows.append((state, scores, token)); state=advance(state,token)
    return rows, state
def experiment(seed, width, accept, fault=None):
    if not (2 <= width <= 64 and 0 < accept < width):
        raise ValueError('need a strict partial cut and bounded batch')
    oracle,_=reference(seed,width+3)
    draft=[row[2] for row in oracle[:accept]] + [(row[2]+1)%VOCAB for row in oracle[accept:width]]
    if fault=='wrong_accepted_proposal': draft[0]=(draft[0]+1)%VOCAB
    snapshots=[seed]; verify_rows=[]; state=seed
    for token in draft:
        verify_rows.append((state, logits(state), greedy(state)))
        state=advance(state,token); snapshots.append(state)
    accepted_ok=all(verify_rows[i][1] == oracle[i][1] and verify_rows[i][2] == draft[i]
                    for i in range(accept))
    keep=accept-1
    state=snapshots[keep] if fault!='skip_rollback' else snapshots[width]
    replay=draft[accept-1]
    state=advance(state,replay)
    if fault=='corrupt_state': state=(state+1)%997
    continuation_ok=True
    for i in range(accept,width+3):
        if logits(state) != oracle[i][1] or greedy(state) != oracle[i][2]:
            continuation_ok=False
        state=advance(state,oracle[i][2])
    return {'accepted_ok':accepted_ok,'continuation_ok':continuation_ok,
            'rollback_attempted':1,'compared_accepted':accept,
            'compared_continuation':width+3-accept,'pass':accepted_ok and continuation_ok}
class OracleContract(unittest.TestCase):
    def test_positive_all_partial_cut_points(self):
        for width in range(2,17):
            for cut in range(1,width):
                with self.subTest(width=width,cut=cut):
                    result=experiment(17,width,cut)
                    self.assertTrue(result['pass'])
                    self.assertEqual(result['rollback_attempted'],1)
                    self.assertGreater(result['compared_accepted'],0)
                    self.assertGreater(result['compared_continuation'],0)
    def test_wrong_proposal_cannot_be_accepted_by_copying_oracle_ids(self):
        result=experiment(17,6,3,'wrong_accepted_proposal')
        self.assertFalse(result['accepted_ok']);self.assertFalse(result['pass'])
    def test_rollback_skipped_fails_state_witness(self):
        result=experiment(17,6,3,'skip_rollback')
        self.assertTrue(result['accepted_ok']);self.assertFalse(result['continuation_ok'])
    def test_corrupt_state_fails_without_changing_expected_tokens(self):
        result=experiment(17,6,3,'corrupt_state')
        self.assertTrue(result['accepted_ok']);self.assertFalse(result['continuation_ok'])
    def test_vacuous_and_oversized_cases_refuse(self):
        for width,cut in [(0,0),(1,0),(4,0),(4,4),(65,1)]:
            with self.assertRaises(ValueError):experiment(17,width,cut)
if __name__=='__main__':unittest.main()
