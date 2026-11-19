"""Scratch wrapper for the candidate controller's existing per-trial boundary.

The candidate controller calls ``ctx.check_boundary()`` before every g.ORDER
unit. Wrapping that context lets the rowflow STOP/deadline contract govern the
same boundary without editing the candidate or replacing its work functions.
"""
from adapter import rowflow_entry


class EntryRefused(BaseException):
    """Terminal work-boundary refusal; bypasses controller's invalid-attempt catches."""
    pass


def abort_terminal_refusal(context, error, record, ledger, abort_type):
    """Persist refusal when possible, then always raise the gate abort type.

    `error` may be the original EntryRefused or an ordinary exception raised
    while controller finally-path ledger persistence replaced that exception.
    """
    reason = context.terminal_refusal
    if reason is None:
        raise ValueError("no latched terminal boundary refusal")
    if isinstance(error, EntryRefused):
        message = f"{type(error).__name__}: {error}"
    else:
        message = f"rowflow/guard boundary refusal: {reason}; unwind error: {type(error).__name__}: {error}"
    record["diagnostic_error"] = message
    try:
        ledger.json("DIAGNOSTIC-REFUSAL.json", message)
    except Exception as ledger_error:
        raise abort_type(message + "; refusal ledger write failed: " + str(ledger_error)) from ledger_error
    raise abort_type(message) from error


class RowflowContext:
    def __init__(self, original, env, now_fn):
        self._original = original
        self._env = env
        self._now_fn = now_fn
        self.terminal_refusal = None

    def _refuse(self, reason, cause=None):
        self.terminal_refusal = str(reason)
        if cause is not None:
            raise EntryRefused(self.terminal_refusal) from cause
        raise EntryRefused(self.terminal_refusal)

    def check_boundary(self):
        allowed, reason = rowflow_entry(self._env, now=self._now_fn())
        if not allowed:
            # Do not drain here: the controller's server is still needed by the
            # driver's existing stop and partial-publication steps. The owning
            # supervisor performs owned_drain after the driver exits.
            self._refuse(reason)
        try:
            self._original.check_boundary()
        except Exception as error:
            # guard.ContextBoundary also raises ordinary ValueError/RuntimeError
            # for STOP, resource, and admission failures. Promote them to the
            # same terminal control path so controller retries cannot swallow.
            self._refuse(f"underlying guard refusal: {type(error).__name__}: {error}", error)

    def __getattr__(self, name):
        return getattr(self._original, name)


def run_with_rowflow_boundary(driver_fn, ctx, *args, env, now_fn, **kwargs):
    """Run a driver callable with rowflow policy at its check_boundary calls."""
    wrapped = ctx if isinstance(ctx, RowflowContext) else RowflowContext(ctx, env, now_fn)
    return driver_fn(wrapped, *args, **kwargs)
