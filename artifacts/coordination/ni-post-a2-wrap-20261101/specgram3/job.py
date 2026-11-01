import os, pathlib, subprocess, sys
D=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/specgram3')
def validate_claim():
    mode='qual' if os.environ.get('WS58_QUAL')=='1' or os.environ.get('WS58_R11_CALIBRATION')=='1' else 'quarter'
    cpus=os.environ.get('FILLER_CPUS','')
    subprocess.run([sys.executable,'-I',str(D/'cpu_claim.py'),mode,cpus],check=True,stdout=subprocess.DEVNULL)
def main():
    if len(sys.argv)>1 and sys.argv[1]=='complete':
        q=os.environ.get('WS58_QUAL')=='1'
        p=pathlib.Path(os.environ.get('FILLER_RESULTS_DIR',''))/os.environ.get('FILLER_QUAL_PHASE','')/'RESULT.json' if q else D/'out/RESULT.json'
        try: return 0 if __import__('json').loads(p.read_text()).get('complete') is True else 1
        except Exception:return 1
    validate_claim()
    if os.environ.get('FILLER_THREADS')!='24':
        print('REFUSED: production recipe requires FILLER_THREADS=24',file=sys.stderr);return 64
    if os.environ.get('WS58_QUAL')=='1' and os.environ.get('FILLER_QUAL_PHASE') not in ('normal','cutoff'):
        print('REFUSED: qualification phase missing',file=sys.stderr);return 64
    if os.environ.get('WS58_R11_CALIBRATION')=='1':
        from datetime import datetime,timezone
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        os.environ['FILLER_R11_CALIBRATION']='1';os.environ['FILLER_RESULTS_DIR']=str(D/'r11-calibration'/stamp)
        os.environ.setdefault('FILLER_DEADLINE',str(__import__('time').time()+285))
    os.execv(sys.executable,[sys.executable,'-I','-B',str(D/'job_base.py'),'full'])
if __name__=='__main__':
    try: raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print('REFUSED: numeric CPU claim invalid',file=sys.stderr);raise SystemExit(64)
