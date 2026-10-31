import hashlib,os,pathlib
D=pathlib.Path(__file__).resolve().parent; V=D.parent/'venv312'; files=[D/'job.py',D/'collect.py',*sorted((D/'source').rglob('*.py')),D.parent/'smoke-supervisor.py',D.parent/'smoke_admission.py',*sorted((D.parent/'engine').glob('*')),pathlib.Path('/usr/bin/python3.12')]
files += [p for p in V.rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and not p.name.endswith('.pyc')]
files += [pathlib.Path(p) for p in ['/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/manifest/clips.jsonl','/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/manifest/pairs.jsonl','/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/qa/qa_tail_gates_report.json','/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-v1/pins/silero_vad_v6.onnx','/mnt/raid0/llm/tmp/cs-47-20261020/dl/smart-turn-v3.2-cpu.onnx','/mnt/raid0/llm/tmp/cs-47-20261020/clips/tt1-p0001-a.wav','/mnt/raid0/llm/tmp/cs-46-20261020/export/encoder_stream_80ms.onnx','/mnt/raid0/llm/tmp/cs-46-20261020/export/encoder_stream_160ms.onnx','/mnt/raid0/llm/tmp/cs-46-20261020/export/decoder_joint_self_fp32.onnx','/mnt/raid0/llm/tmp/cs-46-20261020/dl/decoder_joint-model.onnx','/mnt/raid0/llm/tmp/cs-46-20261020/dl/vocab.txt']]
with open(D/'SOURCES.sha256','w') as out:
 for p in files:
  h=hashlib.sha256()
  with open(p,'rb') as f:
   for b in iter(lambda:f.read(4<<20),b''): h.update(b)
  out.write(h.hexdigest()+'  '+str(p)+'\n')
print('pinned',len(files),'files')
