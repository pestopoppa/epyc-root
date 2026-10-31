def _press_key_with_wake(target: str, key: str) -> tuple[int, str]:
    """Wake character, settle, then ``key``. (rc, detail-on-failure).

    Returns the FIRST non-zero rc with a message naming which of the two
    send-keys calls failed, so a caller can report it without guessing.
    """
    rc, out = _tmux("send-keys", "-t", target, " ")
    if rc != 0:
        return rc, f"send-keys wake-character failed: {out}"
    time.sleep(_WAKE_SETTLE_S)
    rc, out = _tmux("send-keys", "-t", target, key)
    if rc != 0:
        return rc, f"send-keys {key} failed: {out}"
    return 0, ""
