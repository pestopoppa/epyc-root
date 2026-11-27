Continue the same task in this saved workspace and session under the original accurate Light V2 scope.

An independent controlled check replaced the continuation's selected-recipe receipt with a different valid receipt carrying the same payload. The original runtime journal verification completed successfully. With the replacement in place, both tests passed and the serial child used the replacement.

The baseline test checked that the continuation used the exact runtime reference supplied by its fixture. The current test does not catch the substitution described above. Address this observed regression in the allowlisted test and retain the original private-lock isolation, assertions, and focused checks.
