# LSA code-revision planning context

Before planning a native code change, an operator can inspect an explicitly selected original CI verifier receipt with:

```text
python artifacts/lsa-screen-20261103/code_context.py --repo-label native --checkout /path/to/current/native/checkout --case lsa-runtime-cpu-command-exit --receipt /path/to/receipt.json
```

The reader reopens the original receipt with the existing strict CI verifier and shared grade. It matches the producer-declared repository label and full revision plus the named LSA case; the checkout option obtains the requester's current HEAD only. It does not assert the historical tested checkout's filesystem location, create a new claim, or certify model behavior, performance, device residency, or an entire build. An empty claims list means this receipt does not establish the requested exact code-revision context. Invalid receipts appear under `refused`.
