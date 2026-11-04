# KPF-50 atomic output proposal

This unapplied Linux/POSIX proposal creates a private temporary file in the destination directory and publishes it using an atomic no-replace hard link. It refuses every existing destination, including an unrelated file; callers must choose a new output name. In a scratch copy, `python3 -m unittest -v test_child_evidence.py` passed all eight tests, including source-path, symlink and hard-link aliases, and preservation of an existing unrelated destination. The required exact-source upstream impact is still unknown, so do not apply the patch yet.

The mechanism does not guarantee integrity in a destination directory writable by an adversary who can replace the temporary name. If directory `fsync` fails after the link succeeds, the call reports failure although the destination may already exist. These limits and the changed overwrite behavior need review before adoption. No native profile or GPU claim follows.
