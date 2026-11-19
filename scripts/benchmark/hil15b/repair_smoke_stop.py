"""Preserve a censored attempt when an explicit stop interrupts its driver."""
OLD = "            if status != 'terminal': raise Refusal('incomplete attempt; retain and reconcile')\n"
NEW = (
    "            if status == 'censored' and stop():\n"
    "                return {'status':'partial','partial':True,'reason':'stopped during attempt; retain and reconcile',\n"
    "                        'exposed_attempt':str(a.relative_to(self.unit)),\n"
    "                        'completed_slots':sum(r is not None for r in slots)}\n"
    + OLD
)


def repair_source(source):
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError("expected original terminal-status check")
    return source.replace(OLD, NEW, 1)
