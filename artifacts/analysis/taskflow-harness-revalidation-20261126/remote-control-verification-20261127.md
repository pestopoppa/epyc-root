# Managed Codex Remote verification

The running managed Codex app server reported **connected** for the requested
host in 15 local status observations. CLI and daemon both reported version
0.172.0. The managed daemon continued running throughout the check. The
last managed observation was at 04:41:01 UTC on 2026-11-27.
[Verification receipt](remote-control-verification-20261127.json)

During the same observation window, bare `codex remote-control --json`
returned an error for its foreground startup. The CLI's versioned source sends
the bare JSON command to an ephemeral app server on a new local socket.
`codex remote-control start --json` uses the managed daemon path.
The existing daemon's Unix WebSocket independently reported its state.
[CLI routing](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/cli/src/remote_control_cmd.rs#L79-L132) · [Foreground startup](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/cli/src/remote_control_cmd.rs#L180-L243)

The initial diagnostic treated the bare command as a status check. Its
ephemeral process exited on startup failure. The daemon comparison used the
read-only `remoteControl/status/read` request and its status notifications.
The managed connection required no reconnect at the observed boundary.
The ephemeral error's network cause and phone-client reachability remain
unverified. The receipt omits credentials, pairing codes, and identity field
values.

Next: the operator can select Beelzebub in the ChatGPT app; the managed server remains running.
