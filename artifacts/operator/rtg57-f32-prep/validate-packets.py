import ctypes,datetime,importlib.util,json,os,pathlib,subprocess,time
B=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion')
assert set(os.sched_getaffinity(0))=={72,73}
assert not list(pathlib.Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*'))
if ctypes.CDLL(None).prctl(36,1,0,0,0)!=0: raise OSError('subreaper')
spec=importlib.util.spec_from_file_location('owned','/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/helpers/owned_session.py');owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
header=next(x for x in pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/FILLERS.md').read_text().splitlines() if x.startswith('| filler-id |'))
for suffix,id in [('packet','rtg57-c5-vkq-t48'),('t96/packet','rtg57-c5-vkq-t96')]:
 D=B/suffix; V=D/'private-admit';V.mkdir(exist_ok=True);(V/'grants').mkdir(exist_ok=True)
 assert (D/'STOP').is_file() and not pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants',id+'.grant').exists()
 rowline=next(x for x in (D/'ROW.md').read_text().splitlines() if x.startswith('| '+id+' |'))
 fields=[x.strip() for x in rowline.strip().strip('|').split('|')];assert len(fields)==18
 env=os.environ.copy();env.update({'FILLER_GRANTS_DIR':str(V/'grants'),'FILLER_STATE_DIR':str(V/'state'),'FILLER_PREFLIGHT':'1','FILLER_POLL':'1'})
 with (V/'poller.log').open('wb') as log: child=subprocess.Popen(['/bin/bash',str(D/'launch.sh')],env=env,start_new_session=True,stdout=log,stderr=subprocess.STDOUT)
 owner=owned.OwnedSession(child)
 try:
  for _ in range(100):
   assert child.poll() is None
   if b'filler_run12.sh' in pathlib.Path(f'/proc/{child.pid}/cmdline').read_bytes():break
   time.sleep(.03)
  else:raise AssertionError('no private engine')
  fields[2]=str(D/'launch.sh')+f'; pid={child.pid}; temporary private admission only';fields[7]='ARMED';fields[12]='y'
  row=V/'ROW-TEMP-ARMED.md';row.write_text(header+'\n|'+'|'.join(['---']*18)+'|\n| '+' | '.join(fields)+' |\n')
  def run(name,args,env=None):
   with (V/name).open('wb') as f:p=subprocess.run([str(x) for x in args],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45)
   if p.returncode: raise RuntimeError(f'{suffix}: {name} rc={p.returncode}: {(V/name).read_text()[-1200:]}')
  run('validator.log',['/usr/bin/python3','-I','-B','/mnt/raid0/llm/tmp/compute-flags/validate_fillers.py','--file',row,'--row',id,'--for-grant'])
  ge=os.environ.copy();ge['GRANT_OK_TEST_FILLERS']=str(row)
  run('grant-ok.log',['/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh',id,'110','--window-s','5700','--regions','0-95','--pid',str(child.pid)],ge)
  start=datetime.datetime.now(datetime.timezone.utc).replace(second=0,microsecond=0);end=start+datetime.timedelta(seconds=5700)
  grant=V/'NORMAL-PRIVATE.grant';grant.write_text(f'regions=0-95 start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n')
  run('normal-admit.log',['/usr/bin/python3','-B',D/'deps/dryrun_check.py','admit','--id',id,'--row-file',row,'--grant',grant,'--min-window-s','5100','--require-proof','--engine',D/'deps/filler_run12.sh'])
  print(id,'PRIVATE admission checks PASS; no canonical grant')
 finally:
  result=owner.drain();(V/'drain.json').write_text(json.dumps(result,indent=2)+'\n')
  if result.get('drained') is False: raise RuntimeError('temporary poller not drained')
