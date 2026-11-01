# KVU-19a-2 prospective build input binding

This offline helper captures file hashes, sizes and permission modes for every regular source file and declared tool, rejects symlinks, and can compare a later snapshot. It is preparation only: it does not launch a build or qualify a row. Three synthetic tests cover source changes, extra files, tool changes, permissions and symlink refusal.

The traversal and path opens do not provide an adversary-resistant immutable snapshot: directories can change while traversing, files can change after verification, and parent components are not pinned. Tool transitive dependencies, compiler environment, generated sources, subprocess custody, read-only build mounts, ELF identity, actual toolchain/recipe and keeper control remain open. Do not use a passing snapshot as proof of compiler inputs without stronger custody and runtime verification. No source extraction, build or GPU work was performed.
