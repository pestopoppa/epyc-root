"""Prospective per-arm generated-token reservation; fail closed before dispatch.

Pure policy only: this is not wired to either native engine and cannot yet admit a run.
Reservation is conservative: unused output tokens are not returned.
"""
from threading import Lock

class BudgetExceeded(RuntimeError):
    pass

class Budget:
    def __init__(self, total, per_call):
        if type(total) is not int or type(per_call) is not int or total < 1 or not 1 <= per_call <= total:
            raise ValueError('positive integer limits required')
        self.total, self.per_call, self.reserved = total, per_call, 0
        self.lock = Lock()

    def reserve(self, requested):
        if type(requested) is not int or requested < 1 or requested > self.per_call:
            raise BudgetExceeded('invalid or over-limit request')
        with self.lock:
            if self.reserved + requested > self.total:
                raise BudgetExceeded('aggregate exhausted')
            self.reserved += requested
            return {'requested': requested, 'reserved': self.reserved, 'remaining': self.total-self.reserved}
