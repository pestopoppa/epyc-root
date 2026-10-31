#!/usr/bin/env python3
"""Private residual-text projection, not an infra classifier or quality grade.

The historical synthetic API defaults to explicit legacy semantics. The CLI
defaults to native compact rows and requires the canonical APP era registry.
Native shape compatibility never establishes that an input is a genuine run.
"""
import argparse,collections,datetime,hashlib,json,pathlib
import math
import os
CUT=datetime.datetime.fromisoformat('2026-09-23T21:37:09+00:00');KNOWN={'task_failed','infra_failed','scoring_failed','scored'}
def _project_legacy(inputs):
 hist=collections.Counter();classes=collections.Counter();missing=collections.Counter();refusals=collections.Counter();files=[]
 for path in inputs:
  sha=hashlib.sha256();count=0
  with path.open('rb') as f:
   for line in f:
    sha.update(line)
    if not line.strip():continue
    count+=1
    try:top=json.loads(line)
    except (ValueError,UnicodeError):refusals['malformed_json']+=1;continue
    if not isinstance(top,dict):refusals['non_object_row']+=1;continue
    era=None;dt=None
    if 'eval_details' in top:
     detail=top['eval_details']
     if not isinstance(detail,dict):refusals['malformed_eval_details']+=1;continue
     details=detail.get('details',{})
     if not isinstance(details,dict):refusals['malformed_result_details']+=1;continue
     era=details.get('eval_quality_era');rows=detail.get('question_results');stamp=top.get('timestamp')
     if stamp is None:missing['timestamp_missing']+=1
     else:
      try:
       dt=datetime.datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
       if dt.tzinfo is None:raise ValueError('timezone missing')
      except (ValueError,TypeError):dt=None;missing['timestamp_unparseable']+=1
    elif top.get('row_type')=='question_result':
     rows=[top.get('result')];stamp=top.get('ended_at_s')
     if stamp is None:missing['timestamp_missing']+=1
     else:
      try:
       if isinstance(stamp,bool) or not isinstance(stamp,(float,int)):raise ValueError('native epoch must be numeric')
       dt=datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc)
      except (ValueError,TypeError,OverflowError,OSError):missing['timestamp_unparseable']+=1
    elif top.get('row_type') in ('batch_start','batch_complete'):
     refusals['non_question_sidecar_marker']+=1;continue
    else:refusals['unsupported_native_shape']+=1;continue
    if era is not None and era!='E17':refusals['historical_or_unknown_era']+=1;continue
    if era=='E17' and dt is not None and dt<CUT:refusals['era_timestamp_conflict']+=1;continue
    if era is None:missing['era_missing']+=1
    if era!='E17' and (dt is None or dt<CUT):refusals['unbound_cohort']+=1;continue
    if not isinstance(rows,list):refusals['malformed_question_rows']+=1;continue
    for r in rows:
     if not isinstance(r,dict):refusals['malformed_question_row']+=1;continue
     # APP QuestionResult has no native per-question cohort timestamp/era fields.
     if any(k in r for k in ('era','measurement_era','eval_quality_era','timestamp','created_at','ended_at_s')):refusals['unsupported_child_cohort_fields']+=1;continue
     category=r.get('disposition')
     if category not in KNOWN:refusals['unknown_or_missing_category']+=1;continue
     classes[category]+=1
     if category!='task_failed':continue
     err=r.get('error')
     if not isinstance(err,str):missing['error_missing_or_nontext']+=1;err='<missing native error>'
     hist[err]+=1
  files.append({'path':str(path),'sha256':sha.hexdigest(),'nonblank_rows':count})
 return {'schema':'ni08.postE17.native-residual-error-histogram.v3','cutover':CUT.isoformat(),'inputs':files,'class_counts':dict(classes),'residual_count':classes['task_failed'],'error_histogram':dict(hist),'missingness':dict(missing),'refusals':dict(refusals),'scope':'APP journal eval_details/details/eval_quality_era + timestamp; native question_result/result + ended_at_s; explicit E17 contradictions and unsupported child cohort overrides refused; no taxonomy/grade'}


E17_ID = "E17-eval-task-failed-scores-zero-quality"
E17_POLICY = "task_failed_scores_zero_v1"
_COMPACT_TEXT_FIELDS = ("qid", "suite", "partition", "fence")
_COMPACT_COUNT_FIELDS = ("latency_ms", "tokens_generated", "tools_used")


def _aware_stamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        result.astimezone(datetime.timezone.utc)
        if result.utcoffset() is not None
        else None
    )


def _registry(path):
    # Reuse the project's ordinary YAML decoder; never interpret era numbers.
    import yaml

    path = pathlib.Path(path)
    raw = path.read_bytes()
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or not isinstance(data.get("eras"), list):
        raise ValueError("canonical registry must contain an eras list")
    eras = {}
    for row in data["eras"]:
        if not isinstance(row, dict) or row.get("scope") != "eval_quality":
            continue
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in eras:
            raise ValueError("invalid or duplicate eval_quality era identity")
        start = _aware_stamp(row.get("from"))
        if start is None:
            raise ValueError("eval_quality era lacks an aware native from timestamp")
        eras[identity] = start
    if E17_ID not in eras:
        raise ValueError("canonical registry lacks the ETR-1 boundary")
    return eras, {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "boundary_id": E17_ID,
        "boundary_from": eras[E17_ID].isoformat(),
        "policy": E17_POLICY,
    }


def _compact_category(row, missing, refusals):
    """Read the compact writer's omissions, without reclassifying error text."""
    if not isinstance(row, dict):
        refusals["malformed_question_row"] += 1
        return None
    if any(
        k in row
        for k in (
            "era",
            "measurement_era",
            "eval_quality_era",
            "timestamp",
            "created_at",
            "ended_at_s",
        )
    ):
        refusals["unsupported_child_cohort_fields"] += 1
        return None
    if (
        any(not isinstance(row.get(k), str) for k in _COMPACT_TEXT_FIELDS)
        or type(row.get("correct")) is not bool
        or any(type(row.get(k)) is not int or row[k] < 0 for k in _COMPACT_COUNT_FIELDS)
    ):
        refusals["unsupported_native_compact_shape"] += 1
        return None
    category = row.get("disposition")
    if category is None and "disposition" not in row:
        # _compact_question_result omits ALL four keys on a clean scored row.
        # Missing error status on arbitrary or partially damaged rows is UNKNOWN.
        if any(
            k in row
            for k in ("error", "error_detail", "infra_reason", "failure_provenance")
        ):
            refusals["missing_failure_disposition"] += 1
            return None
        return "scored"
    if not isinstance(category, str) or category not in KNOWN:
        refusals["unknown_category"] += 1
        return None
    if category == "scored":
        if any(
            k in row
            for k in ("error", "error_detail", "infra_reason", "failure_provenance")
        ):
            refusals["scored_failure_status_conflict"] += 1
            return None
        return category
    if row.get("error") is not True:
        refusals["missing_or_nonboolean_error_status"] += 1
        return None
    detail = row.get("error_detail")
    if not isinstance(detail, str) or not detail:
        missing["native_error_detail_missing_or_nontext"] += 1
    elif len(detail) > 200 or "\n" in detail:
        refusals["unsupported_native_error_detail_shape"] += 1
        return None
    return category


def _project_native(inputs, registry_path):
    eras, registry = _registry(registry_path)
    cutover = eras[E17_ID]
    hist = collections.Counter()
    classes = collections.Counter()
    shapes = collections.Counter()
    missing = collections.Counter()
    refusals = collections.Counter()
    timing = {}
    files = []
    unknown_question_rows = 0
    observed_question_rows = 0
    truncated_possible = 0

    def observe_time(key, value, epoch=False):
        if epoch:
            parsed = None
            if type(value) in (int, float) and math.isfinite(value):
                try:
                    parsed = datetime.datetime.fromtimestamp(
                        value, datetime.timezone.utc
                    )
                except (ValueError, OverflowError, OSError):
                    pass
        else:
            parsed = _aware_stamp(value)
        if parsed is None:
            missing[key + ("_missing" if value is None else "_unparseable")] += 1
            return None
        observed = timing.setdefault(
            key, {"count": 0, "min": parsed.isoformat(), "max": parsed.isoformat()}
        )
        observed["count"] += 1
        observed["min"] = min(observed["min"], parsed.isoformat())
        observed["max"] = max(observed["max"], parsed.isoformat())
        return parsed

    for path in inputs:
        sha = hashlib.sha256()
        count = 0
        row_refs = []
        before = path.stat()
        with path.open("rb") as handle:
            for line_no, line in enumerate(handle, 1):
                sha.update(line)
                if not line.strip():
                    continue
                count += 1
                try:
                    top = json.loads(line)
                except (ValueError, UnicodeError):
                    refusals["malformed_json"] += 1
                    continue
                if not isinstance(top, dict):
                    refusals["non_object_row"] += 1
                    continue
                eligible = False
                if "eval_details" in top:
                    detail = top["eval_details"]
                    if not isinstance(detail, dict) or not isinstance(
                        detail.get("details"), dict
                    ):
                        refusals["malformed_eval_details"] += 1
                        continue
                    details = detail["details"]
                    rows = detail.get("question_results")
                    stamp = observe_time("journal_timestamp", top.get("timestamp"))
                    policy = details.get("quality_denominator_policy")
                    era = details.get("eval_quality_era")
                    era_status = details.get("eval_quality_era_status")
                    if policy != E17_POLICY:
                        refusals["quality_policy_missing_or_unknown"] += 1
                    elif era_status is not None and era_status != "active":
                        refusals["eval_quality_era_status_unresolved"] += 1
                    elif era is not None and (
                        not isinstance(era, str) or era not in eras
                    ):
                        refusals["unregistered_eval_quality_era"] += 1
                    elif era is not None and eras[era] < cutover:
                        refusals["historical_era_policy_conflict"] += 1
                    else:
                        # Registry E17 note: policy key is authoritative when
                        # present; timestamp is the fallback for old rows. Do
                        # not turn GENERATION time into quality-policy time.
                        eligible = True
                        if era is None:
                            missing["eval_quality_era_missing"] += 1
                        if stamp is not None and stamp < cutover:
                            missing[
                                "policy_authoritative_journal_timestamp_preboundary"
                            ] += 1
                elif top.get("row_type") == "question_result":
                    rows = [top.get("result")]
                    observe_time(
                        "generation_ended_at_s", top.get("ended_at_s"), epoch=True
                    )
                    if "scored_at_s" in top:
                        observe_time("scored_at_s", top["scored_at_s"], epoch=True)
                    # The native sidecar has no quality-policy binding. Even
                    # post-cutover generation/scoring times cannot invent one.
                    refusals["sidecar_quality_policy_unbound"] += 1
                elif top.get("row_type") in ("batch_start", "batch_complete"):
                    refusals["non_question_sidecar_marker"] += 1
                    continue
                else:
                    refusals["unsupported_native_shape"] += 1
                    continue
                if not isinstance(rows, list):
                    refusals["malformed_question_rows"] += 1
                    continue
                for ordinal, row in enumerate(rows):
                    observed_question_rows += 1
                    category = _compact_category(row, missing, refusals)
                    if category is not None:
                        shapes[category] += 1
                    if not eligible or category is None:
                        unknown_question_rows += 1
                        continue
                    classes[category] += 1
                    row_refs.append(
                        {
                            "line": line_no,
                            "child_ordinal": ordinal,
                            "source_line_sha256": hashlib.sha256(line).hexdigest(),
                        }
                    )
                    if category == "task_failed":
                        error = row.get("error_detail")
                        if isinstance(error, str) and error:
                            hist[error] += 1
                            truncated_possible += len(error) == 200
                        else:
                            missing["residual_error_text_unknown"] += 1
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("input changed during projection")
        files.append(
            {
                "path": str(path),
                "sha256": sha.hexdigest(),
                "nonblank_rows": count,
                "admitted_row_refs": row_refs,
            }
        )
    return {
        "schema": "ni08.postE17.native-residual-error-histogram.v4",
        "mode": "native_compact",
        "registry": registry,
        "inputs": files,
        "observed_question_rows": observed_question_rows,
        "count_basis": "physical projected question rows, not deduplicated or a unique-attempt census",
        "admitted_question_rows": sum(classes.values()),
        "unknown_or_unbound_question_rows": unknown_question_rows,
        "full_attempt_denominator": None,
        "full_attempt_denominator_reason": "projection does not establish run custody, complete native batches or omitted attempts",
        "native_shape_counts": dict(shapes),
        "class_counts": dict(classes),
        "residual_count": classes["task_failed"],
        "error_histogram": dict(hist),
        "residual_text_at_native_cap_count": truncated_possible,
        "error_text_scope": "native error_detail only: newline-normalized and capped at 200 characters by APP; at-cap text may be truncated; original error text is unknown",
        "timing": timing,
        "missingness": dict(missing),
        "refusals": dict(refusals),
        "scope": "syntactic native projection only; no genuine-run custody, infra classification, grade, historical regrade or missing-attempt inference",
    }


def project(inputs, *, mode="legacy", registry_path=None):
    """Project native compact rows explicitly; preserve the old synthetic API.

    ``legacy`` is backward compatibility for the original seven synthetic
    controls, not a native producer or cohort qualification.
    """
    if mode == "legacy":
        result = _project_legacy(inputs)
        result["mode"] = "legacy_synthetic_compatibility"
        return result
    if mode != "native" or registry_path is None:
        raise ValueError("native mode requires an explicit canonical APP registry path")
    return _project_native([pathlib.Path(p) for p in inputs], registry_path)


def public_summary(result):
    """Allow only aggregate classes, source references and text hashes out."""
    safe = dict(result)
    hist = safe.pop("error_histogram")
    safe["error_text_sha256_counts"] = {
        hashlib.sha256(text.encode("utf-8")).hexdigest(): count
        for text, count in hist.items()
    }
    return safe


def _write_new_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=pathlib.Path)
    parser.add_argument(
        "--output",
        required=True,
        type=pathlib.Path,
        help="private raw-text histogram (created 0600)",
    )
    parser.add_argument("--mode", choices=("native", "legacy"), default="native")
    parser.add_argument("--era-registry", type=pathlib.Path)
    parser.add_argument(
        "--public-output",
        type=pathlib.Path,
        help="optional aggregates and hashes; no raw error texts",
    )
    args = parser.parse_args()
    if args.mode == "native" and args.era_registry is None:
        parser.error("--era-registry is required in native mode")
    result = project(args.input, mode=args.mode, registry_path=args.era_registry)
    _write_new_private(args.output, result)
    if args.public_output is not None:
        _write_new_private(args.public_output, public_summary(result))


if __name__ == "__main__":
    main()
