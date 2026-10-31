#!/usr/bin/env python3
import argparse, hashlib, json, pathlib
import numpy as np
import soundfile as sf
import torch, transformers
from transformers import AutoProcessor, ParakeetForTDT, GenerationConfig

p=argparse.ArgumentParser();p.add_argument('audio');p.add_argument('out');a=p.parse_args()
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
model_path='/mnt/raid0/llm/models/moondream-parakeet-ultra-73175eb'
processor_path='/mnt/raid0/llm/models/nvidia-parakeet-v3-processor-541d1f'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
assert sha(model_path+'/model.safetensors')=='c9608f36d0ab956c14bfcc525479b0746b3b42a56f6949ec85c14eb7466717dc'
audio,rate=sf.read(a.audio,dtype='float32'); assert rate==16000 and audio.ndim==1
pcm_sha=hashlib.sha256(audio.astype('<f4').tobytes()).hexdigest()
torch.set_num_threads(1); torch.set_num_interop_threads(1)
processor=AutoProcessor.from_pretrained(processor_path,local_files_only=True)
inputs=processor(audio,sampling_rate=rate,return_tensors='pt')
np.save(out/'frontend.npy',inputs['input_features'].numpy());np.save(out/'attention_mask.npy',inputs['attention_mask'].numpy())
model=ParakeetForTDT.from_pretrained(model_path,torch_dtype=torch.float32,local_files_only=True).eval()
logits=[]
def enc_hook(_m,_i,o): np.save(out/'encoder.npy',o.last_hidden_state.detach().cpu().numpy())
def joint_hook(_m,_i,o): logits.append(o.detach().cpu().numpy())
model.encoder.register_forward_hook(enc_hook);model.joint.register_forward_hook(joint_hook)
generation_config=GenerationConfig.from_pretrained(processor_path,local_files_only=True)
with torch.inference_mode(): result=model.generate(**inputs,generation_config=generation_config)
np.save(out/'joint_logits.npy',np.concatenate(logits,axis=1)); ids=result.sequences.tolist();durations=result.durations.tolist()
record={'schema':'ultra-torch-control/v1','audio':a.audio,'audio_file_sha256':sha(a.audio),'pcm_format':'mono float32 LE decoded by soundfile','pcm_sha256':pcm_sha,'sample_rate':rate,'samples':len(audio),'model_revision':'73175eb7aeb0d82f1e2a6b53b3aabc10a90bcd0b','model_sha256':sha(model_path+'/model.safetensors'),'processor_revision':'541d1f99c6b0c3cd0b11a95167540bb8edefd82b','processor_config_sha256':sha(processor_path+'/processor_config.json'),'generation_config_sha256':sha(processor_path+'/generation_config.json'),'tokenizer_sha256':sha(processor_path+'/tokenizer.json'),'transformers_version':transformers.__version__,'torch_version':torch.__version__,'dtype':'float32','token_ids_including_blanks':ids,'durations':durations,'transcription':processor.batch_decode(result.sequences,skip_special_tokens=True)}
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
