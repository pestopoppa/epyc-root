# Q38 runtime adapter draft

This offline adapter integrates the existing coordinator's `Runtime` interface with injected supervisor, transport and journal interfaces. It refuses requests until identity is verified and durable pre-request custody is acknowledged, tracks unverified spawn/cleanup, and requires descendant drain from the supervisor. Six fake-only tests, including an actual coordinator-to-adapter exercise, exercise routing, no-send conditions, stop, and unverified failures.

This is not a runnable producer. No concrete supervisor exists: in particular a future implementation must prove atomic identity capture and exclusive child/descendant reaping before executing a server, including pidfd acquisition failure. No concrete transport, durable no-redraw journal, STOP plumbing, recipe verification, rowflow launcher or live process test exists. Do not schedule or interpret fakes as cleanup proof. No compute or processes were launched.
