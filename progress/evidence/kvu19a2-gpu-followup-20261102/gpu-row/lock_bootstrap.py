#!/usr/bin/env python3
"""Compile catalog-verified private lock source; never import shared bytecode."""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parent

def verified_sources(root=ROOT):
    entries=json.loads((root/'lock-catalog.json').read_text())['modules']
    sources={}
    for item in entries:
        path=root/item['path']
        if root.resolve() not in path.resolve().parents:raise ValueError('catalog path escape')
        source=path.read_bytes()
        if hashlib.sha256(source).hexdigest()!=item['sha256']:raise ValueError('private lock source changed: '+item['module'])
        sources[item['module']]=(str(path),source)
    return sources

class PrivateSource(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    def __init__(self,sources):self.sources=sources
    def find_spec(self,fullname,path=None,target=None):
        if fullname in self.sources:return importlib.util.spec_from_loader(fullname,self)
        if fullname.startswith('src.'):raise ModuleNotFoundError('outside private lock catalog: '+fullname)
    def create_module(self,spec):return None
    def exec_module(self,module):
        path,source=self.sources[module.__name__]
        module.__file__=path
        exec(compile(source,path,'exec'),module.__dict__)

def install(root=ROOT):
    loader=PrivateSource(verified_sources(root))
    for name in ('src','src.runtime'):
        package=types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    sys.meta_path.insert(0,loader)
    return loader

def main():
    install()
    from src.runtime import region_lock_cli
    return region_lock_cli.main()
if __name__=='__main__':sys.exit(main())
