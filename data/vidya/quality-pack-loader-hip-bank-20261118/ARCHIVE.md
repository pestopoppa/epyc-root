The native README.md and SOURCE.sha256 retain their original bytes.

Restore base-plan.json, hip-plan.original.json and plan.json from their original-bytes envelopes by base64-decoding bytes_b64 and checking sha256. receipt.json maps original names to envelopes. Restore these three names before checking SOURCE.sha256; that manifest pins original native source bytes. Numeric model/stat fields triggered the account-number heuristic. The published scratch packet and decoded source hashes are unchanged. Publication/ preserves the separate queued-smoke submission disposition.
