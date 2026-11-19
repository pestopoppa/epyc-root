# C6 q4_K n=4 residual-shape diagnostic preparation

This standalone analysis groups retained candidate-minus-CPU-sibling output differences by column for captured cases 7686 and 7699. It checks result and capture digests, matching float32 byte lengths, shapes, strides, finiteness and complete contiguous representation before pairing values. Synthetic tests exercise these checks.

This is preparation only: publisher refused the proposed row because its estimate was under five minutes, and the analysis has not been run on retained captures. `analyze.py` pins the retained result SHA-256 `05739394acb9d6d9cbf544eef31935f9ec88c1802cc3bc646909462acabaa7cc` and confines capture reads under the retained runs directory. It expects a row runner to supply a result path; its dry-run and full paths are separate. A later approved invocation must bind the source and input pins and retain the result. Descriptive differences cannot alone establish the cause of the failures, qualify the candidate, establish performance, or support promotion.

Run synthetic tests from this directory with `python3 -m unittest -v test_analyze`.
