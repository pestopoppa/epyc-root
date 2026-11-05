# Prospective KPF-18 first-token logits capture

The patch targets experimental source `6ec877068936588b6d63dbba5842bbd540b92031`; it is not a production change. With `KPF18_RAW_LOGITS_PATH` set, it records full-vocabulary float32 bits before first-token sampling, with task, slot, position and token IDs, and refuses active speculation. Output is diagnostic only. The caller must pre-create a private regular file, retain and verify its identity, and bind the recorded task to the HTTP response and native trace. Final-component symlinks and non-regular files are refused; same-user mutations and replacement of parent directories are not excluded.

The standalone helper test checks float bits and refusal paths. It does not compile the full server, prove runtime capture or compare placement. The new build and any later GPU observations remain prospective; they cannot establish equivalence to the historical image or close the parent gate.
