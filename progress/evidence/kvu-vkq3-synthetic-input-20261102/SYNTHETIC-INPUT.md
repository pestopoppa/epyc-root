# Synthetic tokenizer diagnostic input v1

This generator produces synthetic structured records, not conversation text. It is a draft input component only: no tokenizer or model has been run, and no diagnostic row is ready. Its token count and runtime cannot establish either enrolled prompt's properties or feasibility. The original prompt remains subject to no-redraw; the calibration prompt requires its own exposure/custody audit before reuse.

Run `python3 -B synthetic_input.py > INPUT` to write the input, and verify the byte count and SHA-256 before use. The generator writes exactly 70,000 ASCII records with LF endings; for zero-based `i` from 0 through 69,999, each record is `sample={i:05d} value={(i * 7919 + 104729) % 1000003:06d} category={i % 17:02d} synthetic diagnostic text.\n`. No external data, randomness, locale or clock enters the output.

- Byte length: `4550000`
- SHA-256: `e354df7f35d62a98716b1d0c37ddf1dbedc3ce69f9722286d8f8f19c865d5417`
- Test: `python3 -B test_synthetic_input.py`

Before scheduling, commit and pin the generator, this identity and exact parameters together with the eventual worker, launcher and plan. The separate qualification control, tokenizer/model/library identity binding, grant and deadline enforcement, custody, receipts and rowflow integration remain outstanding under `DESIGN.md`.
