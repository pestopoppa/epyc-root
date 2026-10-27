import sys
sys.path.insert(0,'/mnt/raid0/llm/llama.cpp/gguf-py')
from gguf import GGUFReader
p='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
r=GGUFReader(p)
for key, f in r.fields.items():
 if 'attention.head_count' in key or 'attention.key_length' in key or 'attention.value_length' in key:
  print(key, [f.parts[i].tolist() for i in f.data])
