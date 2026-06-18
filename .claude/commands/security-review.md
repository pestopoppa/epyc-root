# Security Review

Audit the specified scope for exploitable security issues using the `security-review` skill.

**Target scope:** $ARGUMENTS

## Your Task

1. If `$ARGUMENTS` is empty, inspect the current diff first.
2. Run the `security-review` skill against the specified scope.
3. Report only findings that satisfy the exploit-path gates.
4. If no finding passes the gates, say so explicitly and include residual risk plus checks run.
