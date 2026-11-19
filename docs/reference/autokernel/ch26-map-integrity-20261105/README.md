# C5 map binding: in-place mutation guard

The earlier functional map prototype bound the mapped device and inode to a
preflight SHA-256, but did not reject an in-place mutation of that inode after
hashing. This independent reference prototype additionally records size, mtime
and ctime alongside the digest, and checks those values with device and inode
at binding time. Preexisting receipts lack these fields and fail closed; a
fresh preflight is required.

`python3 -m unittest -v test_runtime_linkage` passes eight model-free tests,
including an in-place mutation and the existing inode replacement and process
identity cases. This is a point-in-time metadata check, not proof of continuous
immutability: it does not close the race after the check or protect against
privileged timestamp/filesystem manipulation. It has not been integrated into
a row, executed against a live server, or used for a placement, contention,
overhead or noise-floor conclusion.
