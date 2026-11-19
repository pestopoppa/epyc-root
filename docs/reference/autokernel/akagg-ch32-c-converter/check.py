#!/usr/bin/env python3
"""Verify pinned group-C converter prerequisite using Git objects only."""
import json, subprocess
REPO='/mnt/raid0/llm/llama.cpp'
C5='c72ec82f5417bb2937310326120f149b665e8400'
C1='a4cb4c61fd9d9c2066c7c1747821d3d65b8943bd'
C2='7e3eeee0480902c90cbdff172f407dc063cf0770'
P='6e62ba538478202094edc6c100c782719e310aa3'
def git(*a):return subprocess.check_output(['git','-C',REPO,*a],text=True)
def show(rev,path):return git('show',rev+':'+path)
def ancestor(a,b):
 rc=subprocess.run(['git','-C',REPO,'merge-base','--is-ancestor',a,b]).returncode
 if rc not in (0,1):raise RuntimeError('git ancestry error')
 return rc==0
path='conversion/base.py'
c5,pre,p,c1=(show(r,path) for r in (C5,P+'^',P,C1))
c2=show(C2,'conversion/h2o_lightning.py');patch=git('show','--format=',C1,'--',path)
for name in ('def load_hparams_guess(', 'def register_hparams_loader(', '_hparams_loaders'):
 assert name not in c5 and name not in pre and name in p and name in c1, name
assert 'ModelBase.load_hparams_guess(dir_model)' in patch
assert '@ModelBase.register_hparams_loader(_is_h2o_lightning_checkpoint)' in c2
assert 'ModelBase.load_hparams(dir_model, False, guess=False)' in c2
assert ancestor(P,C1) and ancestor(C1,C2) and not ancestor(P,C5)
print(json.dumps({'schema':'akagg.ch32.c-converter.v1','revisions':{'c5':C5,'c1':C1,'c2':C2,'converter_registry_introducer':P},'evidence':{'registry_and_guess_absent_from_c5':True,'registry_and_guess_introduced_by_prerequisite':True,'c1_patch_uses_guess_registry':True,'c2_uses_registration_and_guess_false':True,'prerequisite_ancestor_of_c1':True},'scope':'Unchanged converter source requires equivalent registry and guess behavior. Full-commit minimality, conversion success and runtime compatibility unproved.'},indent=2,sort_keys=True))
