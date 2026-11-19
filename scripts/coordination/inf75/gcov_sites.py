#!/usr/bin/env python3
"""Extract *partial* line/site data from GCC's text ``gcov -b -c`` report.

This does not verify source or profile provenance, completeness of a request's
shape envelope, loaded libraries, knob effective values or HIP routes. Its
output must not set ``verified`` or establish an INERT classification.
"""
import re

_LINE = re.compile(r"^\s*([^:]+):\s*(\d+):(.*)$")
_BRANCH = re.compile(r"^branch\s+(\d+)\s+(?:taken\s+(\d+)|never executed)(?:\s+\([^)]*\))*\s*$")


class CaptureError(ValueError):
    pass


def extract_sites(text: str, *, expected_source: str, sites: dict) -> dict:
    """Return observed numeric line/branch counts; reject absent or ambiguous sites.

    ``sites`` maps site id to {line: positive integer, predicate: bool}. A
    predicate requires at least two numbered count-form branch records. A site
    on a non-instrumented ``-`` line is unknown, not evidence of nonexecution.
    """
    if not isinstance(text, str) or not isinstance(expected_source, str) or not expected_source:
        raise CaptureError("source or report missing")
    if not isinstance(sites, dict) or not sites:
        raise CaptureError("sites missing")
    lines, current, source = {}, None, None
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if m:
            count, number, body = m.group(1).strip(), int(m.group(2)), m.group(3)
            current = None
            if number == 0 and body.startswith("Source:"):
                if source is not None:
                    raise CaptureError("duplicate source header")
                source = body[len("Source:"):]
            if number == 0:
                continue
            if number in lines:
                raise CaptureError("duplicate source line")
            if count == "-":
                value = None
            elif count in ("#####", "====="):
                value = 0
            elif re.fullmatch(r"[0-9]+\*?", count):
                value = int(count.rstrip("*"))
            else:
                raise CaptureError("unsupported line count")
            lines[number] = {"count": value, "branches": {}}
            current = number
        elif raw.startswith("branch"):
            b = _BRANCH.match(raw)
            if b is None or current is None:
                raise CaptureError("unsupported or orphan branch record")
            index = int(b.group(1))
            if index in lines[current]["branches"]:
                raise CaptureError("duplicate branch index")
            lines[current]["branches"][index] = int(b.group(2) or 0)
    if source != expected_source:
        raise CaptureError("source identity mismatch")
    out = {}
    for key, spec in sites.items():
        if (not isinstance(key, str) or not key or not isinstance(spec, dict)
                or type(spec.get("line")) is not int or spec["line"] <= 0
                or type(spec.get("predicate")) is not bool):
            raise CaptureError("invalid site")
        item = lines.get(spec["line"])
        if item is None or item["count"] is None:
            raise CaptureError("site missing or uninstrumented")
        branches = item["branches"]
        if spec["predicate"] and (len(branches) < 2 or sorted(branches) != list(range(len(branches)))):
            raise CaptureError("branch vector missing or incomplete")
        out[key] = {"line_count": item["count"], "branches": [branches[i] for i in sorted(branches)]}
    return {"status": "PARTIAL_UNVERIFIED", "source": source, "sites": out}
