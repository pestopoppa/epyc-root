# KPF-60 captured fixture-blob comparison

`verify_pair.py` compares two separately captured native fixture data-section
blobs with one another and with the existing fixed 152-byte F16 oracle. A
manifest supplies each blob's relative filename and original SHA-256; the
verifier refuses missing or extra fields, digest mismatch, file aliasing,
symlinks, nonregular files, and blobs that change during the read. A mismatch
is distinct from missing or invalid evidence.

The manifest format is `kpf60.fixture-blob-pair.v1` with exactly `baseline`
and `observed` objects, each containing `file` and `sha256`. The paths must be
single filenames beneath the canonical absolute root supplied on the command
line. Run `python3 verify_pair.py /absolute/blob/root manifest.json`. Exit 0
means both blobs match the fixed oracle, 1 means mismatch, and 2 means invalid
or unavailable evidence. The caller must preserve the capture manifest and
raw blobs independently.

Five model-free tests passed for matching captures, unequal blobs, identical
but wrong blobs, digest tampering, hardlink and symlink aliasing, unsafe paths,
and malformed manifests. These are synthetic checks only: no actual native
blob has been produced or compared. The tool does not prove source identity,
capture provenance, GPU residency, race freedom against same-UID mutation,
or a measurement warrant. A MATCH is not a general writer-parity verdict.
