# KPF-13.1 mapped DSO identity: model-free candidate

`map_identity.py` adds a fail-closed, point-in-time check for a supplied `/proc/<pid>/maps` snapshot. It checks each mapped llama/ggml DSO's mapped device and inode against an opened regular file and its pinned SHA-256, refusing deleted mappings, symlinks, conflicting identities, unpinned files, digest drift and changes observed while hashing. It catches a replacement with identical bytes but a different inode, which pathname hashing alone cannot detect. Eight synthetic tests pass:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s progress/evidence/kpf131-map-identity-20261104 -v
```

This is not integrated into the debugger, validated against a live historical server, or proof of continuous mapped-object custody. In particular it cannot detect mappings introduced and removed between samples, prove original historical DSO hashes, establish that the path has remained unchanged since mapping, or bind observations to a request, batch or physical cache layout. The snapshot must be obtained while the correct inferior is stopped and the debugger must separately enforce lifecycle and mapping-event coverage. No inference, exposed observations, historical verdicts, or readiness markers were changed.
