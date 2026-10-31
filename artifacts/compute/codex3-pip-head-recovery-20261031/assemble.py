"""Prospective offline reconstruction; all network and predictor inference prohibited."""
import os,sys,json,hashlib,socket,datetime,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_DATASETS_OFFLINE']='1';os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']='True'
sha=lambda b:hashlib.sha256(b).hexdigest()
def deny(*a,**k):raise RuntimeError('network disabled for saved-response reconstruction')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
A=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-head-assembly-20261031-0530/ORIGIN-AUDIT.json').read_bytes());inventory=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-pool2-r30-v2-20261031/HEAD-0-34-AUDIT.json').read_bytes());outputs=[];markdowns={}
C=D/'output'/'RECOVERY-START.json'
def verify_inputs():
 c=json.loads(C.read_bytes())
 if c['schema']!='pip02-offline-assembly-recovery-start/v1' or c['script_sha256']!=sha(Path(__file__).read_bytes()):raise RuntimeError('recovery source pin')
 for name,digest in c['inputs_sha256'].items():
  if sha(Path(name).read_bytes())!=digest:raise RuntimeError('recovery input changed: '+name)
 for row in inventory['rows']:
  for f in row['files']:
   if f['path'].endswith('.start'):
    path=Path(f['path']);missing=path.with_name(path.name[:-len('.start')]+'.finish.json')
    if missing.exists():raise RuntimeError('original finish appeared; refuse replacement')
 return c
capture=verify_inputs()
import importlib.util
old=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/venv-files.json').read_bytes())['files']
new=json.loads(Path('/mnt/micron/codex3-pip-relocatable-r25-20261030/venv-files-r9.json').read_bytes())['files']
if any(new.get(k)!=v for k,v in old.items()) or any('/__pycache__/' not in k or not k.endswith('.pyc') for k in new.keys()-old.keys()):raise RuntimeError('historical venv source closure changed')
spec=importlib.util.spec_from_file_location('original_venv_witness','/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029/venv_witness.py');vmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(vmod)
witness=vmod.Witness('/mnt/raid0/llm/venvs/paddleocr','/mnt/micron/codex3-pip-relocatable-r25-20261030/venv-files-r9.json','254e35f1edf3fcc3a880825e6f05874a9174c71f78d67ff6eb4c0d536afb4588','/mnt/micron/codex3-pip-relocatable-r25-20261030/venv-dirs-r9.json','7d4ce147150cdb7b32e9548c4857ddb68f8c995e75dd6136a346cc657063ff1e',lambda:True)
import httpx
from paddleocr import PaddleOCRVL
from paddlex.inference.pipelines.paddleocr_vl.pipeline import gather_imgs,PaddleOCRVLResult
class Offline(httpx.AsyncBaseTransport):
 def __init__(self,region):self.region=region;self.ordinal=0;self.network_calls=0
 async def handle_async_request(self,request):
  if request.method!='POST' or not str(request.url).endswith('/v1/chat/completions'):raise RuntimeError('unexpected offline request')
  if self.ordinal>=len(self.region):raise RuntimeError('extra native request')
  start,response=self.region[self.ordinal];actual=await request.aread();expected=bytes.fromhex(start['body_hex'])
  if actual!=expected or sha(actual)!=start['body_sha256']:raise RuntimeError('native request body differs at ordinal '+str(self.ordinal))
  self.ordinal+=1;return httpx.Response(response['status'],headers=response['headers'],content=bytes.fromhex(response['body_hex']),request=request)
 async def aclose(self):pass
for proof,row in zip(A['rows'],inventory['rows']):
 try:
  assert proof['verified'] and proof['index']==row['index'];page=row['page'];files=row['files'];layout_path=Path(next(f['path'] for f in files if f['path'].endswith('-layout.json')));layout=json.loads(layout_path.read_bytes());starts=sorted(Path(f['path']) for f in files if f['path'].endswith('.start.json'));region=[]
  for p in starts:region.append((json.loads(p.read_bytes()),json.loads(p.with_name(p.name.replace('.start.json','.result.json')).read_bytes())))
  original=Path(next(f['path'] for f in files if f['path'].endswith('.result') and not f['path'].endswith('.result.json')));expected=json.loads(original.read_bytes())['markdown'];image=Path('/mnt/raid0/llm/datasets/omnidocbench/images')/page['image']
  pipe=PaddleOCRVL(pipeline_version='v1.6',layout_detection_model_name='PP-DocLayoutV3',layout_detection_model_dir='/mnt/raid0/llm/models/PP-DocLayoutV3-paddle3.0.0',vl_rec_backend='llama-cpp-server',vl_rec_server_url='http://127.0.0.1:9/v1',vl_rec_max_concurrency=1,use_layout_detection=True,use_doc_orientation_classify=False,use_doc_unwarping=False,device='cpu')
  try:
   inner=pipe.paddlex_pipeline._pipeline
   if hasattr(inner,'layout_det_model'):
    def no_inference(*a,**k):raise RuntimeError('layout model inference forbidden')
    inner.layout_det_model.predict=no_inference
   im=inner.img_reader([str(image)])[0]
   if list(im.shape)!=layout['pixel_shape'] or str(im.dtype)!=layout['pixel_dtype'] or sha(im.tobytes())!=layout['pixel_sha256']:raise RuntimeError('decoded pixel identity mismatch')
   boxes=layout['boxes'];native_layout={'input_path':str(image),'page_index':None,'boxes':boxes};imgs=gather_imgs(im,boxes)
   sdk=inner.vl_rec_model.genai_client.openai_client;sdk.max_retries=0;transport=Offline(region);sdk._client._transport=transport
   settings=inner.get_model_settings(False,False,True,None,None,None,None,None,None)
   parsing,tables,spotting,imgs_out=inner.get_layout_parsing_results(images=[im],layout_det_results=[native_layout],imgs_in_doc=[imgs],use_chart_recognition=settings['use_chart_recognition'],use_seal_recognition=settings['use_seal_recognition'],use_ocr_for_image_block=settings['use_ocr_for_image_block'],vlm_kwargs={'repetition_penalty':None,'temperature':0,'top_p':None,'min_pixels':None,'max_pixels':None,'max_new_tokens':None},merge_layout_blocks=settings['merge_layout_blocks'],layout_shape_mode='auto')
   if transport.ordinal!=len(region):raise RuntimeError('not all original requests replayed')
   result=PaddleOCRVLResult({'input_path':str(image),'page_index':None,'page_count':None,'width':im.shape[1],'height':im.shape[0],'doc_preprocessor_res':{'output_img':im},'layout_det_res':native_layout,'table_res_list':tables[0],'parsing_res_list':parsing[0],'spotting_res':spotting[0],'imgs_in_doc':imgs_out[0],'model_settings':settings})
   md=result.markdown['markdown_texts'];markdowns[page['index']]=md;outputs.append({'index':page['index'],'replayed':transport.ordinal,'network_calls':transport.network_calls,'expected_sha256':sha(expected.encode()),'actual_sha256':sha(md.encode()),'byte_identical':md==expected})
  finally:pipe.close()
 except BaseException as e:outputs.append({'index':row['index'],'error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc()})
if len(outputs)!=2 or not all(x.get('byte_identical') and x.get('network_calls')==0 for x in outputs):
 print(json.dumps(outputs,indent=2));sys.exit(1)
verify_inputs();witness.check()
import importlib.util
writer_path=Path('/mnt/raid0/llm/tmp/inf51-streamingllm-full-20261029/bounded_writer.py')
spec=importlib.util.spec_from_file_location('native_recovery_writer',writer_path);wmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(wmod)
w=wmod.Writer(D/'output',8*1024*1024,resume=True)
try:
 csha=sha(C.read_bytes());created=[]
 for row in outputs:
  idx=row['index'];payload={'schema':'pip02-prospective-recovery-page/v1','index':idx,'original_markdown_sha256':row['expected_sha256'],'markdown':markdowns[idx],'reconstructed_markdown_sha256':row['actual_sha256'],'replayed_region_count':row['replayed'],'network_calls':0,'recovery_start_sha256':csha,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};raw=(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode();name=f'page-{idx:04}.recovery.json';w.create(name,raw);created.append({'index':idx,'path':str(D/'output'/name),'sha256':sha(raw)})
 verify_inputs();witness.check()
 payload={'schema':'pip02-offline-assembly-recovery-finish/v1','start_path':str(C),'start_sha256':csha,'pages':created,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_model_requests':0,'network_calls':0};w.create('RECOVERY-FINISH.json',(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode())
finally:w.close()
print(json.dumps(outputs,indent=2))
