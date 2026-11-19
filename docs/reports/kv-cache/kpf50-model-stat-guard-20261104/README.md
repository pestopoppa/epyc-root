# KPF-50 model identity guard preparation

The metadata-only guard checks a resolved model path and recorded device,
inode, size, modification time and change time without reading model weights.
Four model-free tests passed. It does not prove a fresh content digest, and
the KPF-50 runtime sealing, cleanup qualification and publisher smoke remain
open. A future launcher must use the validated resolved path and refuse changed
metadata.
