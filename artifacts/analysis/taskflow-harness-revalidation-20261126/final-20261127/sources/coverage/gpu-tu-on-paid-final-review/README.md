# GPU TU ON paid2 final review

This package is bound to the terminal output from the approved
`persistent-callback-admission-v2/runs/tu-on-paid-01` callback. It uses the
qualified TU V4 checker and the same contained evaluator settings. It starts
neither a native model nor a paid review during preparation.

Once the native callback has completed, run `python3 -B grade_saved.py inspect`.
This checks terminal cleanup, the exact saved session and plan, cumulative
generation charge, the patch, and all files in the independent grading lane.
Read the exact patch and relevant source before completing the
`SOURCE-SAFETY-TEMPLATE.json` as `SOURCE-SAFETY.json`. A source-safety approval
allows contained grading and carries no semantic verdict.

Run the following with the main-approved source-safety receipt and exact digest.

```sh
nice -n 19 taskset -c 180-183 /usr/bin/python3 -B grade_saved.py execute \
  --safety SOURCE-SAFETY.json --safety-sha "$safety_digest"
```

A V4 return code of one produces a failing receipt; other return codes are not
accepted as a bounded contract result. Run `python3 -B normalize.py` after the
grade to stage the fresh final semantic review, regardless of the V4 score.
The approval template binds the actual candidate, case, original baseline,
previous deterministic and paid messages, measured paid cost, and V4 receipt.
The reviewer can inspect the neutral baseline and exact patch in the lane at
`.review-evidence/`. Only main's separate launch runs the paid reviewer.
