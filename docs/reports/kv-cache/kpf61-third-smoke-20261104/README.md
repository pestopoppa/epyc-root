# KPF-61 third publisher smoke

The 0.8B public-control smoke completed its native work with job rc 0 and native status FAIL. The engine ended rc 75 (`partial-native-incomplete`) because its smoke completion predicate required PASS. The 32 generated token IDs matched; parsed probability rows differed starting at index 0. The planner reported a reusable prefix of 224 tokens versus a baseline of 32. `SUMMARY.json` records the counts and hashes of the original attempt files.

This is qualification evidence on one tiny-model pair, not a 35B result, full-logit comparison, performance result or KPF-61 gate verdict. The first two same-lineage publisher attempts also failed; the three-failure rule parks this lineage. The preserved native result describes the original attempt; scratch paths in it are locators and may not remain available.
