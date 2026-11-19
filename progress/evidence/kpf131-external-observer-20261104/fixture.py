import ctypes, os, signal
lib=ctypes.CDLL('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/libllama.so')
os.kill(os.getpid(), signal.SIGSTOP)
lib.llama_max_devices()
