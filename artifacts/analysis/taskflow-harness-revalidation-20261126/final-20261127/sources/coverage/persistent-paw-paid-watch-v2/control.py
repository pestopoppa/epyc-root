"""Check terminal pre-dispatch evidence without HTTP or launching any child."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import watch

with TemporaryDirectory() as tmp:
    run = Path(tmp)
    row = "fixture-only"
    assert watch.no_dispatch(run, row, 0) is None
    outcome = {"status": "admission_timeout", "stage": "pre_dispatch", "model_started": False,
               "backend": "gpu", "slot": 0, "id": row, "terminal_at": 1}
    path = run / "RESULTS.json"
    path.write_text(json.dumps({"terminal": [outcome]}))
    (run / (row + ".ADMISSION.json")).write_text(json.dumps(dict(outcome, state=outcome["status"])))
    assert watch.no_dispatch(run, row, 0)["pre_dispatch_no_model_submission"]
    (run / (row + ".execution.json")).touch()
    try:
        watch.no_dispatch(run, row, 0)
    except RuntimeError as error:
        assert "conflicts" in str(error)
    else:
        raise AssertionError("contradictory child evidence accepted")
    outcome["status"] = "callback_error"
    path.write_text(json.dumps({"terminal": [outcome]}))
    try:
        watch.no_dispatch(run, row, 0)
    except RuntimeError as error:
        assert "did not prove" in str(error)
    else:
        raise AssertionError("ambiguous callback error accepted")
print('PASS pending, proved no-dispatch, started conflict, ambiguous failure; zero calls')
