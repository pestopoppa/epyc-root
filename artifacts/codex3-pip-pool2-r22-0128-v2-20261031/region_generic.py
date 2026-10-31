"""Append-only HTTPX region transport; unknown requests are never redrawn."""
import datetime,hashlib,json,os,pathlib,time
import httpx

def put(path,obj,writer=None):
 raw=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if writer is not None:
  if path.parent!=writer.root:raise ValueError('checkpoint outside bounded writer')
  writer.create(path.name,raw);return
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(f.fileno())
 finally:os.close(fd)
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
class RegionTransport(httpx.AsyncBaseTransport):
 def __init__(self,inner,directory,endpoint,writer=None,prefix="",provenance=None,deadline_epoch=None,min_remaining_s=0,max_new_requests=None,shared_budget=None):
  self.inner=inner;self.directory=pathlib.Path(directory);self.endpoint=endpoint.rstrip('/')+'/chat/completions';self.ordinal=0;self.writer=writer;self.prefix=prefix;self.provenance=provenance;self.deadline_epoch=deadline_epoch;self.min_remaining_s=min_remaining_s;self.max_new_requests=max_new_requests;self.new_requests=0;self.shared_budget=shared_budget
  self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
 async def handle_async_request(self,request):
  if request.method!='POST' or str(request.url)!=self.endpoint: return await self.inner.handle_async_request(request)
  raw=await request.aread(); payload=json.loads(raw)
  if payload.get('stream',False):raise RuntimeError('streaming request not supported')
  if self.provenance and (payload.get('model')!='PaddleOCR-VL-1.6-0.9B' or payload.get('max_tokens')!=4096 or payload.get('temperature')!=0):raise RuntimeError('native request model or sampling bound changed')
  if len(raw)>8*1024**2:raise RuntimeError('request body exceeds checkpoint limit')
  key=f'{self.prefix}{self.ordinal:06d}';self.ordinal+=1; start=self.directory/(key+'.start.json');result=self.directory/(key+'.result.json');digest=hashlib.sha256(raw).hexdigest()
  if (self.writer.exists(start.name) if self.writer is not None else start.exists()):
   saved=json.loads(self.writer.read(start.name) if self.writer is not None else start.read_bytes())
   if saved.get('ordinal')!=self.ordinal-1 or saved.get('body_sha256')!=digest or saved.get('body_hex')!=raw.hex() or not saved_identity_matches((saved.get('provenance') or {}).get('identity'),(self.provenance or {}).get('identity')):raise RuntimeError('request identity or original provenance changed')
   if not (self.writer.exists(result.name) if self.writer is not None else result.exists()):raise RuntimeError('region exposure unknown; no redraw')
   value=json.loads(self.writer.read(result.name) if self.writer is not None else result.read_bytes());data=bytes.fromhex(value['body_hex'])
   if value['request_sha256']!=digest or value.get('start_sha256')!=hashlib.sha256(self.writer.read(start.name) if self.writer is not None else start.read_bytes()).hexdigest() or value['response_sha256']!=hashlib.sha256(data).hexdigest():raise RuntimeError('damaged checkpoint')
   return httpx.Response(value['status'],headers=value['headers'],content=data,request=request)
  if (self.writer.exists(result.name) if self.writer is not None else result.exists()):raise RuntimeError('orphan response')
  if self.max_new_requests is not None and self.new_requests>=self.max_new_requests:raise TimeoutError('segment request limit before exposure')
  if self.deadline_epoch is not None and time.time()+self.min_remaining_s>=self.deadline_epoch:raise TimeoutError('segment boundary before request exposure')
  if self.writer is not None and self.writer.used+2*len(raw)+4*1024**2+4*16384>self.writer.budget:raise TimeoutError('insufficient checkpoint budget before request')
  stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
  mark=lambda:put(start,{'ordinal':self.ordinal-1,'body_sha256':digest,'body_hex':raw.hex(),'provenance':self.provenance,'originated_at':stamp},self.writer)
  if self.shared_budget is not None:self.shared_budget.begin(mark)
  else:mark()
  self.new_requests+=1
  try:
   response=await self.inner.handle_async_request(request)
   try:data=await response.aread()
   finally:await response.aclose()
  finally:
   if self.shared_budget is not None:self.shared_budget.release()
  if not 200<=response.status_code<300 or len(data)>2*1024**2:raise RuntimeError('response not retainable; exposure remains unknown')
  put(result,{'request_sha256':digest,'start_sha256':hashlib.sha256(self.writer.read(start.name) if self.writer is not None else start.read_bytes()).hexdigest(),'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':response.status_code,'headers':list(response.headers.multi_items()),'body_hex':data.hex(),'response_sha256':hashlib.sha256(data).hexdigest()},self.writer)
  return httpx.Response(response.status_code,headers=response.headers,content=data,request=request)
 async def aclose(self):await self.inner.aclose()

def resume_layout(saved, current, boxes):
 # Keep the first native layout's scores exactly. Scores can vary by a few ULPs
 # across CPU invocations; crop geometry, order, labels and pixels may not vary.
 expected=hashlib.sha256(json.dumps(saved['boxes'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 if saved.get('layout_sha256')!=expected or saved.get('count')!=len(saved['boxes']):raise RuntimeError('damaged native layout checkpoint')
 for key in ('pixel_sha256','pixel_shape','pixel_dtype','count'):
  if current.get(key)!=saved.get(key):raise RuntimeError('native page layout changed: '+key)
 for old,new in zip(saved['boxes'],current['boxes']):
  if {k:v for k,v in old.items() if k!='score'}!={k:v for k,v in new.items() if k!='score'}:raise RuntimeError('native page layout geometry changed')
 for old,new in zip(saved['boxes'],boxes):
  if 'score' in old:new['score']=old['score']
 return saved

def saved_identity_matches(saved, current):
 if not isinstance(saved,dict) or not isinstance(current,dict):return False
 if any(saved.get(k)!=current.get(k) for k in ('campaign_sha256','model_pins')):return False
 sources=saved.get('source_pins')
 if not isinstance(sources,dict) or not sources:return False
 for name,digest in sources.items():
  if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=digest:raise RuntimeError('original replay source changed: '+name)
 return True

def bind_native_pipeline(pipe,directory,endpoint,writer=None,prefix="",provenance=None,deadline_epoch=None,min_remaining_s=0,max_new_requests=None,shared_budget=None):
 """Pin native layout and decoded page pixels before the first model request."""
 directory=pathlib.Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
 wrapper=pipe.paddlex_pipeline
 if getattr(wrapper,'multi_device_inference',False) is not False:raise RuntimeError('unsupported multi-device pipeline')
 pipeline=getattr(wrapper,'_pipeline',None)
 if pipeline is None:raise RuntimeError('native inner pipeline missing')
 original=pipeline.get_layout_parsing_results
 def serial(value):
  if hasattr(value,'tolist'):return value.tolist()
  if hasattr(value,'item'):return value.item()
  raise TypeError('unsupported native layout value: '+type(value).__name__)
 def bound(*args,**kw):
  if args or not isinstance(kw.get('images'),list) or not isinstance(kw.get('layout_det_results'),list):raise RuntimeError('unexpected native layout calling convention')
  if len(kw['images'])!=1 or len(kw['layout_det_results'])!=1:raise RuntimeError('one page required')
  image=kw['images'][0];layout=kw['layout_det_results'][0]
  boxes=layout['boxes']; raw=json.dumps(boxes,sort_keys=True,separators=(',',':'),default=serial,allow_nan=False).encode()
  identity={'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'pixel_shape':list(image.shape),'pixel_dtype':str(image.dtype),'layout_sha256':hashlib.sha256(raw).hexdigest(),'boxes':json.loads(raw),'count':len(boxes)}
  marker=directory/(prefix+'layout.json')
  if (writer.exists(marker.name) if writer is not None else marker.exists()):
   resume_layout(json.loads(writer.read(marker.name) if writer is not None else marker.read_bytes()),identity,boxes)
  else:put(marker,identity,writer)
  return original(*args,**kw)
 pipeline.get_layout_parsing_results=bound
 sdk=pipeline.vl_rec_model.genai_client.openai_client
 if not hasattr(sdk,'max_retries'):raise RuntimeError('cannot disable SDK retries')
 sdk.max_retries=0
 client=sdk._client
 if not isinstance(client._transport,httpx.AsyncBaseTransport):raise RuntimeError('unexpected HTTPX transport')
 client._transport=RegionTransport(client._transport,directory,endpoint,writer,prefix,provenance,deadline_epoch,min_remaining_s,max_new_requests,shared_budget)
