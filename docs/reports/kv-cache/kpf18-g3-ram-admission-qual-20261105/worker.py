"""Synthetic private-filesystem exercise of exact retained RAM guard; no live admission."""
import importlib.util,json,os,sys,tempfile,time
from pathlib import Path
D=Path(__file__).resolve().parent
NOW=2000000000.; END=NOW+100

def load(name):
 s=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def epoch(n):
 import datetime
 return datetime.datetime.fromtimestamp(n,datetime.timezone.utc).isoformat()
def grant(start=NOW-1,end=END,regions='q0'):
 return f'regions={regions} start={epoch(start)} end={epoch(end)}'
def row(ident,memory='32'):
 cells=['']*18;cells[0]=ident;cells[5]=memory
 return '| '+' | '.join(cells)+' |'
def exercise(name,records,rows,available=288,missing_mem=False,unsafe=False):
 m=load(name)
 with tempfile.TemporaryDirectory(prefix='private-',dir=D) as tmp:
  root=Path(tmp);(root/'grants').mkdir()
  for ident,line in records:(root/'grants'/(ident+'.grant')).write_text(line)
  if unsafe:
   (root/'grants'/'other.grant').unlink();(root/'grants'/'other.grant').symlink_to(root/'absent')
  (root/'FILLERS.md').write_text('\n'.join(rows))
  mem=root/'meminfo';mem.write_text('Unknown: 1 kB\n' if missing_mem else f'MemAvailable: {available*1024**2} kB\n')
  m.FLAGS=root;m.time=type('Clock',(),{'time':staticmethod(lambda:NOW)})
  m.Path=lambda text:mem if str(text)=='/proc/meminfo' else Path(text)
  try:return {'outcome':'ACCEPT','other_gib':m.check('own',END)}
  except ValueError as exc:return {'outcome':'REFUSE','reason':str(exc)}

def main():
 own=[('own',grant())];other=[('other',grant())]
 cases=[
 ('active-own',own,[row('own')],256,False,False,'ACCEPT',0),
 ('future-own',[('own',grant(NOW+1))],[row('own')],256,False,False,'REFUSE',None),
 ('missing-own',[],[],256,False,False,'REFUSE',None),
 ('expired-own',[('own',grant(NOW-20,NOW))],[row('own')],256,False,False,'REFUSE',None),
 ('other-overlap',own+other,[row('other')],288,False,False,'ACCEPT',32),
 ('future-other-overlap',own+[('other',grant(NOW+1))],[row('other')],288,False,False,'ACCEPT',32),
 ('other-outside',own+[('other',grant(END,END+10))],[],256,False,False,'ACCEPT',0),
 ('memory-below-floor',own+other,[row('other')],287,False,False,'REFUSE',None),
 ('missing-memory',own,[],256,True,False,'REFUSE',None),
 ('malformed-grant',own+[('other','regions=q0 start=bad')],[row('other')],288,False,False,'REFUSE',None),
 ('missing-other-row',own+other,[],288,False,False,'REFUSE',None),
 ('duplicate-other-row',own+other,[row('other'),row('other')],288,False,False,'REFUSE',None),
 ('unknown-memory',own+other,[row('other','?')],288,False,False,'REFUSE',None),
 ('unsafe-grant',own+other,[row('other')],288,False,True,'REFUSE',None)]
 if os.environ.get('RAM_MODE')=='SMOKE_ONLY':cases=cases[:2]
 observations=[]
 for label,records,rows,mem,missing,unsafe,want,total in cases:
  for name in ('original','corrected'):
   observed=exercise(name,records,rows,mem,missing,unsafe)
   expected='ACCEPT' if name=='original' and label=='future-own' else want
   ok=observed['outcome']==expected and (total is None or observed.get('other_gib')==total)
   observations.append({'case':label,'implementation':name,'expected':expected,'observed':observed,'matched':ok})
   if not ok:raise RuntimeError(json.dumps(observations))
 Path(sys.argv[1]).write_text(json.dumps({'status':'PASS','controls':observations,'scope':'synthetic private flags/meminfo/time only; original known future-own acceptance recorded; no actual host or GPU admission'},indent=2)+'\n')
if __name__=='__main__':main()
