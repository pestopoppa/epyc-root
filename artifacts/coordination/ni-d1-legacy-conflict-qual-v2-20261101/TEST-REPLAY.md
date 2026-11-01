# Host-scoped test replay

The recorded tests use Linux /proc and the installed immutable qual-v1 helper. From this packet directory on the EPYC host, create the missing test-only import link if absent:

```bash
ln -s /mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py qual-v2/qualify_launcher.py
python3 -m unittest -v test_legacy
```

Use the standing model-free prep mutex and resource limits. This creates no grant, qualification nonce or receipt. Installation itself creates the corresponding runtime link and remains ws58-owned. The original 29 regression test outputs are preserved separately.
