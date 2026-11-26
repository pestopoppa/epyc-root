"""Drive a stock OpenCode session without disabling interactive questions."""
import time


QUESTION_DEFAULT = "No additional information. Use your judgment based on the supplied task."


class RunInterrupted(TimeoutError):
    """Cancellation receipt attributed to the case even when the API refused it."""

    def __init__(self, receipt, answers):
        super().__init__("approved case wall exhausted or owned run cancelled")
        self.receipt = receipt
        self.answers = answers


def run(box, limits, rows, prompt, *, session=None, stop=None, answer=None):
    session = session or box.new_session()
    before = len(rows)
    box.prompt(session, prompt)
    answers = []
    idle_checks = 0
    replied = set()
    while limits.seconds_left() > 0 and not (stop and stop.is_set()):
        status = box.poll()
        for form in status["forms"]:
            if form["id"] in replied:
                continue
            if answer is None:
                box.decline(form, QUESTION_DEFAULT)
                answers.append({"form": form, "status": "no-operator-guidance", "reason": QUESTION_DEFAULT})
            else:
                details = box.api(f"/api/session/{form['sessionID']}/form/{form['id']}")
                reply = answer(details)
                box.reply(form, reply)
                answers.append({"form": form, "answer": reply})
            replied.add(form["id"])
        running = status["active"]
        if not running:
            idle_checks += 1
            if idle_checks >= 2:
                transcript = box.export(session)
                terminal = transcript["messages"][-1] if transcript["messages"] else {}
                if len(rows) > before or terminal.get("error"):
                    return session, transcript, answers
        else:
            idle_checks = 0
        time.sleep(1)
    try:
        receipt = {"response": box.api(f"/api/session/{session}/interrupt", {})}
    except RuntimeError as error:
        receipt = {"api_error": str(error)}
    raise RunInterrupted(receipt, answers)
