#!/usr/bin/env python3
import importlib.util, json, math, os, pathlib, subprocess, sys, time
D=pathlib.Path('/mnt/raid0/llm/tmp/akagg-ch26b-r2-20261101')
INPUT=D/'input'
BUILD='/mnt/raid0/llm/kernels/builds/cpu-20261021-49550eda5-c-nemotron'
ROOT='/mnt/raid0/llm/worktrees/research-ds41-run10'
if subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip() != '5d947693cc5fc245f7a85f5ccf144edfb6dfe4c9': raise SystemExit('REFUSED research source moved')
if subprocess.run(['git','-C',ROOT,'diff','--quiet','HEAD','--']).returncode: raise SystemExit('REFUSED dirty research tracked source')
spec=importlib.util.spec_from_file_location('ds41gate',INPUT/'gate_1017.py')
g=importlib.util.module_from_spec(spec); sys.modules[spec.name]=g; spec.loader.exec_module(g)
g.BASE=INPUT; g.SEPT_SNAPSHOT=INPUT/'sept_launch.snapshot.json'; g.MANIFEST=INPUT/'prompt-manifest.ds41-decode.json'; g.MODEL_PIN=INPUT/'model_identity_1017.json'; g.GGUF_META=INPUT/'gguf_meta.py'; g.LOCK_TAG='filler-akagg-ch26b-1017-c2-r2-20261101'
phase='dryrun' if os.environ.get('FILLER_DRYRUN')=='1' else 'full'
out=INPUT/phase
if out.exists(): raise SystemExit('REFUSED phase output already exists; use a fresh successor')
old_install=g.install_measure_wrapper
def install(serving,out_dir,boot_timeout_s,log_name='launches.jsonl',echo=True):
    old_install(serving,out_dir,boot_timeout_s,log_name,echo)
    measure=serving._measure_once
    def wrapped(recipe,build_dir,port,*args,**kwargs):
        stop=os.environ.get('FILLER_STOPFILE','')
        if (stop and pathlib.Path(stop).exists()) or time.time() >= int(os.environ['FILLER_DEADLINE']): raise SystemExit(75)
        val=measure(recipe,build_dir,port,*args,**kwargs)
        if str(pathlib.Path(build_dir).resolve()) != BUILD or not math.isfinite(val) or val <= 0: raise SystemExit('REFUSED invalid measured unit')
        rec={'phase':phase,'build':BUILD,'status':'ok','tok_s':val,'recorded_ns':time.time_ns()}
        with open(D/'measured.jsonl','a') as f: f.write(json.dumps(rec)+'\n'); f.flush(); os.fsync(f.fileno())
        if stop and pathlib.Path(stop).exists(): raise SystemExit(75)
        return val
    serving._measure_once=wrapped
    return measure
g.install_measure_wrapper=install
raise SystemExit(g.main(['calibrate','--pairs','24','--cmp-pairs','5','--build',BUILD,'--port','18741','--out',str(out),'--execute']))
