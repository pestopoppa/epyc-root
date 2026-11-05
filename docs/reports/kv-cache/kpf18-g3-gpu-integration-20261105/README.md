# KPF-18 group-3 GPU hook preparation

`prepare_gpu.py` produced a disabled scratch successor at `/mnt/raid0/llm/tmp/kvu/g3-gpu-integrated-20261105`, installing the pinned dynamic GPU residency hook and resealing the retained predecessor's inventories. The preparer uses a custody-verified scratch predecessor because its original preparer source pins have drifted. The generated successor's custody check verified 201 entries and its normal entry refused with rc 78; three existing model-free sampler tests passed.

This is preparation only. The patched driver has not run and no live GPU, rowflow admission, model load, output writer or inference has been qualified. The predecessor and its historical results remain unchanged. The scratch predecessor is a dependency, and its later absence or drift makes this preparation refuse rather than reconstructing its provenance.
