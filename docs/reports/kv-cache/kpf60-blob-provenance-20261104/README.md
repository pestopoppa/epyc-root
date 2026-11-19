# KPF-60 fixture blob provenance binding candidate

`verify_bound.py` extends the fixed 152-byte fixture comparison with a
caller-supplied, independently pinned SHA-256 of a canonical JSON contract.
It hashes a declared patch, executable and build receipt, requires that receipt
to name the same commit and content hashes, and requires two distinct capture
receipts to name the same executable, fixed selection, individual blob hashes,
and zero process exit. It refuses missing/extra fields, malformed identifiers,
wrong selection, altered or aliased artifacts, symlinks, model-weight filenames,
and nonzero or noninteger exit status. It reuses the existing separate-capture
and fixed-oracle checks. Seven model-free tests passed.

The SHA-256 argument must be supplied from an independently trusted prospective
declaration; the program cannot authenticate its origin. Build and capture
receipts are producer assertions: their internal consistency does not prove
that the claimed commit was built, a process ran, mappings or device residency
were valid, cleanup succeeded, or artifacts were not swapped by a same-UID
actor. The program cannot create a measurement warrant or retrofit one onto a
past run. It is not wired to a real producer and has not compared native blobs.
The fixed selection applies only to the declared F16 fixture. HIGH-impact native
cache source was not edited.
