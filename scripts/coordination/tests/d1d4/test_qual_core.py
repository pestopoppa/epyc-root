#!/usr/bin/env python3
"""Pure controls; a separate R6-admitted fixture test exercises the child path."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'qualify_launcher.py'
spec = importlib.util.spec_from_file_location('qualify_launcher', SOURCE)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

class QualificationCore(unittest.TestCase):
    def test_production_cutoff_requires_observed_deadline(self):
        with tempfile.TemporaryDirectory() as td:
            flags=Path(td);nonce='c'*64;qdir=flags/'qual'/nonce;qdir.mkdir(parents=True)
            (qdir/'proof-normal.json').write_text(json.dumps({'id':'row','nonce':nonce,'phase':'normal'}))
            (qdir/'proof-cutoff.json').write_text(json.dumps({'id':'row','nonce':nonce,'phase':'cutoff','partial':True}))
            old_load=q.load_manifest;old_qual=os.environ.get('WS58_QUAL');old_nonce=os.environ.get('WS58_QUAL_NONCE')
            q.load_manifest=lambda _:{'id':'row','production':True}
            os.environ['WS58_QUAL']='1';os.environ['WS58_QUAL_NONCE']=nonce
            try:
                with self.assertRaisesRegex(q.Refused,'active STOP or deadline'):
                    q.engine_partial(Path('/unused'),flags,nonce)
            finally:
                q.load_manifest=old_load
                if old_qual is None:os.environ.pop('WS58_QUAL',None)
                else:os.environ['WS58_QUAL']=old_qual
                if old_nonce is None:os.environ.pop('WS58_QUAL_NONCE',None)
                else:os.environ['WS58_QUAL_NONCE']=old_nonce

    def test_placement_maps_smt_and_refuses_wrong_claim(self):
        self.assertEqual(q.placement_local('132-133','cpu',0,'')['quarters'],['q1'])
        with self.assertRaisesRegex(q.Refused,'exceeds synthetic admitted pair'):
            q.placement_local('132-133','cpu',0,'0-95')
        with self.assertRaisesRegex(q.Refused,'maps to no region'):
            q.placement_local('132-133','cpu',1,'')

    def test_context_and_prompt_are_separate(self):
        m={'production':True,'request_manifest_sha256':'a'*64,'production_recipe':{'sha256':'d'*64},'kv_cache_mode':'split','n_ctx_required':262144,'per_slot_n_ctx_required':65536,
           'n_parallel_required':4,'prompt_tokens_required':200}
        first={'ok':True,'scope':'TARGET_SCRATCH_SERVER','production_recipe_sha256':'d'*64,'kv_cache_mode':'split','n_ctx_total':262144,'n_ctx_per_slot':65536,'total_slots':4,'manifest_sha256':'a'*64,'prompt_tokens':200}
        self.assertTrue(q.first_request_ok(m,first))
        self.assertFalse(q.first_request_ok(m,dict(first,n_ctx_per_slot=32768)))
        self.assertFalse(q.first_request_ok(m,dict(first,prompt_tokens=199)))
        self.assertFalse(q.first_request_ok(m,dict(first,prompt_tokens=201)))

    def test_manifest_hash_ignores_only_keeper_mutables(self):
        m = {'id':'row', 'qualification':{'receipt':'/fixed'}, 'hold':None}
        first = q.manifest_digest(m)
        m['hold'] = 'breaker'; m['keeper_log'] = [{'state':'wait'}]
        self.assertEqual(first, q.manifest_digest(m))
        m['qualification']['receipt'] = '/other'
        self.assertNotEqual(first, q.manifest_digest(m))

    def test_policy_park_margin(self):
        m={'scratch_root':'/tmp', 'est_output_GiB':3, 'job_floor_gib':150}
        old=q.load_manifest
        q.load_manifest=lambda _p:m
        try:
            self.assertTrue(q.disk_wait(Path('/ignored'),154.9))
            self.assertFalse(q.disk_wait(Path('/ignored'),155))
        finally:q.load_manifest=old

    def test_nonce_state_replay_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); manifest=root/'m.json'; manifest.write_text('{}')
            old=q.load_manifest
            q.load_manifest=lambda _: {'id':'row', 'production':False,'qualification':{'receipt':str(root/'receipt')},'hold':None}
            try:
                nonce='a'*64; p=q.store_path(root,nonce); p.parent.mkdir()
                p.write_text(json.dumps({'kind':'epyc.qual.nonce.v1','id':'row','manifest_sha256':q.manifest_digest(q.load_manifest(manifest)), 'receipt':str(root/'receipt'),'state':'issued'}))
                q.read_state(manifest,root,nonce,'issued')
                with self.assertRaises(q.Refused):q.read_state(manifest,root,nonce,'passed')
                d=json.loads(p.read_text());d['manifest_sha256']='0'*64;p.write_text(json.dumps(d))
                with self.assertRaises(q.Refused):q.read_state(manifest,root,nonce,'issued')
            finally:q.load_manifest=old

if __name__=='__main__':unittest.main()
