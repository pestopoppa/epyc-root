"""Salesforce helpers shim — same function surface as
dt_arena/utils/salesforce/helpers.py (@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458,
Apache-2.0), backed by the in-memory StateStore.

The store keeps JSON:API-shaped records per module under "salesforce":
  Leads/Accounts/Cases/Notes/Tasks/Opportunities -> [{"id", "type",
  "attributes": {...}}]

`_api_request` mirrors the upstream JSON:API contract for the read paths the
imported subset uses:
  GET  /Api/V8/module/<Module>          -> {"data": [records]}  (page[number]/page[size])
  GET  /Api/V8/module/<Module>/<id>     -> the single record dict
Write paths (POST/PATCH) apply the body to the module list so future subsets
with write-inspecting judges behave sensibly.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_store: Any = None


def _set_store(store: Any) -> None:
    global _store
    _store = store


def _salesforce() -> Dict[str, Any]:
    return _store.data["salesforce"]


MODULE_RE = re.compile(r"^/Api/V8/module/([A-Za-z]+)(?:/([^/?]+))?")


def configure_salesforce(
    base_url: Optional[str] = None,
    grant_type: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """No-op in the in-memory runner: there is no remote Salesforce to configure."""
    return None


def _api_request(
    method: str,
    path: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    _retried: bool = False,
) -> Dict[str, Any]:
    """In-memory JSON:API request (see module docstring)."""
    m = MODULE_RE.match(path.split("?")[0])
    if not m:
        return {"error": "unsupported path", "status_code": 400, "text": path}
    module, record_id = m.group(1), m.group(2)
    records = _salesforce().get(module, [])

    if method.upper() == "GET":
        if record_id:
            for rec in records:
                if str(rec.get("id")) == record_id:
                    return dict(rec)
            return {"error": f"not found: {module}/{record_id}", "status_code": 404, "text": ""}
        page = int((params or {}).get("page[number]", 1))
        size = int((params or {}).get("page[size]", 50))
        start, end = (page - 1) * size, page * size
        return {"data": [dict(r) for r in records[start:end]]}

    if method.upper() in ("POST", "PATCH", "PUT"):
        if method.upper() == "POST":
            rec = dict(body or {})
            rec.setdefault("id", f"rec-{len(records) + 1}")
            records.append(rec)
            return {"ok": True, "data": rec}
        for i, rec in enumerate(records):
            if str(rec.get("id")) == record_id:
                merged = dict(rec)
                merged.update(body or {})
                records[i] = merged
                return {"ok": True, "data": merged}
        return {"error": f"not found: {module}/{record_id}", "status_code": 404, "text": ""}

    return {"error": f"method {method} unsupported", "status_code": 405, "text": ""}


def _module_list(module: str) -> List[Dict[str, Any]]:
    return list(_salesforce().get(module, []))


def _attrs(rec: Dict[str, Any]) -> Dict[str, Any]:
    return rec.get("attributes") or {}


def list_leads(page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
    return _module_list("Leads")

def get_lead_by_id(lead_id: str) -> Optional[Dict[str, Any]]:
    result = _api_request("GET", f"/Api/V8/module/Leads/{lead_id}")
    if "error" in result:
        return None
    return result


def search_leads_by_name(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    account_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Case-insensitive in-memory filter over Leads (mirrors upstream filter params)."""
    out = []
    for rec in _module_list("Leads"):
        a = _attrs(rec)
        if first_name and str(a.get("first_name", "")).strip().lower() != str(first_name).strip().lower():
            continue
        if last_name and str(a.get("last_name", "")).strip().lower() != str(last_name).strip().lower():
            continue
        if account_name:
            haystack = " ".join(
                str(a.get(k, "")).lower() for k in ("account_name", "company", "company_name")
            )
            if str(account_name).strip().lower() not in haystack:
                continue
        out.append(dict(rec))
    return out


def find_lead_by_email(email: str) -> Optional[Dict[str, Any]]:
    for rec in _module_list("Leads"):
        a = _attrs(rec)
        for key in ("email1", "email", "email_address"):
            if str(a.get(key, "")).strip().lower() == str(email).strip().lower():
                return dict(rec)
    return None


def list_accounts(page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
    return _module_list("Accounts")

def list_accounts_by_industry(industry: str) -> List[Dict[str, Any]]:
    out = []
    for rec in _module_list("Accounts"):
        if str(_attrs(rec).get("industry", "")).strip().lower() == str(industry).strip().lower():
            out.append(dict(rec))
    return out


def list_opportunities(page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
    return _module_list("Opportunities")
