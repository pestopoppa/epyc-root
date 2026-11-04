"""Scratch wrapper for the candidate controller's existing per-trial boundary.

The candidate controller calls ``ctx.check_boundary()`` before every g.ORDER
unit. Wrapping that context lets the rowflow STOP/deadline contract govern the
same boundary without editing the candidate or replacing its work functions.
"""
from adapter import rowflow_entry


class EntryRefused(BaseException):
    """Terminal work-boundary refusal; bypasses controller's invalid-attempt catches."""
    pass


class _BoundaryContext:
    def __init__(self, original, env, now_fn):
        self._original = original
        self._env = env
        self._now_fn = now_fn

    def check_boundary(self):
        allowed, reason = rowflow_entry(self._env, now=self._now_fn())
        if not allowed:
            # Do not drain here: the controller's server is still needed by the
            # driver's existing stop and partial-publication steps. The owning
            # supervisor performs owned_drain after the driver exits.
            raise EntryRefused(reason)
        try:
            self._original.check_boundary()
        except Exception as error:
            # guard.ContextBoundary also raises ordinary ValueError/RuntimeError
            # for STOP, resource, and admission failures. Promote them to the
            # same terminal control path so controller retries cannot swallow.
            raise EntryRefused(f"underlying guard refusal: {type(error).__name__}: {error}") from error

    def __getattr__(self, name):
        return getattr(self._original, name)


def run_with_rowflow_boundary(driver_fn, ctx, *args, env, now_fn, **kwargs):
    """Run a driver callable with rowflow policy at its check_boundary calls."""
    wrapped = _BoundaryContext(ctx, env, now_fn)
    return driver_fn(wrapped, *args, **kwargs)
