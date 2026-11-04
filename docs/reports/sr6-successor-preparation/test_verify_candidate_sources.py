import copy
import unittest
from unittest.mock import patch
from pathlib import Path
import verify_candidate_sources as check


class CandidateSourceTests(unittest.TestCase):
    def setUp(self):
        self.content = b'first line\nsource excerpt\nthird line\n'
        self.blob = 'a' * 40
        self.rows = []
        for w in range(1, 4):
            for c in ('code', 'rag', 'prose'):
                for n in range(5):
                    ident=f'{w}-{c}-{n}'
                    prompt=f'Unique question {ident}\n\nsource excerpt'
                    self.rows.append({'id': ident, 'class': c, 'window': f'w{w}',
                        'seed': len(self.rows), 'prompt': prompt,
                        'prompt_sha256': check.sha(prompt.encode()),
                        'source': {'repository':'llama.cpp', 'revision':'b'*40,
                            'path':'some/file', 'git_blob':self.blob,
                            'file_sha256':check.sha(self.content), 'line_start':2, 'line_end':2}})
        self.candidate={'schema':'sr6.raw-candidate-corpus.v1', 'prompts':self.rows}
        self.inventories=[{'prompt_sha256':['c'*64]}, {'prompt_sha256':['d'*64]}]

    def run_verify(self):
        def git(repo, *args):
            return (self.blob+'\n').encode() if args[0]=='rev-parse' else self.content
        with patch.object(check,'run_git',side_effect=git):
            return check.verify(self.candidate, self.inventories, Path('/unused'))

    def test_valid_balanced_source_checked_only(self):
        self.assertEqual(self.run_verify()['status'], 'SOURCE_CHECK_ONLY_NOT_PUBLICATION_AUTHORITY')

    def test_rejects_tampered_source_and_exclusions(self):
        self.rows[3]['source']['file_sha256']='e'*64
        with self.assertRaises(ValueError): self.run_verify()
        self.rows[3]['source']['file_sha256']=check.sha(self.content)
        self.inventories[0]['prompt_sha256'].append(self.rows[3]['prompt_sha256'])
        with self.assertRaises(ValueError): self.run_verify()

    def test_rejects_fabricated_excerpt_and_unbalanced_partition(self):
        self.rows[3]['source']['line_start']=3
        self.rows[3]['source']['line_end']=3
        with self.assertRaises(ValueError): self.run_verify()
        self.rows[3]['source']['line_start']=2
        self.rows[3]['source']['line_end']=2
        self.rows[3]['window']='w2'
        with self.assertRaises(ValueError): self.run_verify()

    def test_rejects_duplicate_seed_and_missing_inventory(self):
        self.rows[3]['seed']=self.rows[0]['seed']
        with self.assertRaises(ValueError): self.run_verify()
        self.rows[3]['seed']=3
        self.inventories.pop()
        with self.assertRaises(ValueError): self.run_verify()

if __name__=='__main__': unittest.main()
