# Repeat evidence archive

Archived members preserve exact supplied source bytes. Selected frozen case baseline maps include read-only inputs. Native and review evidence includes wire bodies, request ledgers, exported terminal sessions and recorded usage. Container filesystems, unfiltered work directories, session databases, weights, and dependency trees are excluded. Native readiness receipts, later metadata rechecks, checker outcomes, and owner acceptance retain distinct provenance. Slot lock files preserve path custody alongside owner receipts; file bytes do not encode held flock state.

The compressed layout maps numbered archive members to original paths and raw file digests. Original gzip wire bodies remain byte-for-byte inside the outer archives.

Use `gzip -dc ARCHIVE-LAYOUT.json.gz` to find an original path, then `tar -xOzf SHARD MEMBER` to write the selected source bytes to standard output.

Run `python3 package.py verify --archive .` to check the stored and decoded hashes.
