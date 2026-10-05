"""Gmail helpers shim — same function surface as dt_arena/utils/gmail/helpers.py
(@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458, Apache-2.0), backed by the
in-memory StateStore ("gmail" -> {"messages": [...]}).

Message filtering mirrors upstream semantics: all subject_contains / body_contains
terms must appear in the SAME message; matching is case-insensitive; comma
normalization (normalize_amounts) applies to body terms; the body is always
attached ("body" key) because the upstream proxy fetches full bodies.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ..utils import normalize_amounts

_store: Any = None


def _set_store(store: Any) -> None:
    global _store
    _store = store


def _messages() -> List[Dict[str, Any]]:
    return _store.data["gmail"]["messages"]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(_to_text(v) for v in value if _to_text(v))
    if isinstance(value, dict):
        for k in ("Address", "address", "email", "Email", "Name", "name"):
            if k in value:
                text = _to_text(value.get(k))
                if text:
                    return text
        return str(value)
    return str(value)


def _normalize_message_shape(msg: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(msg)
    out["id"] = _to_text(out.get("id") or out.get("ID") or out.get("Id") or "")
    out["subject"] = _to_text(out.get("subject") or out.get("Subject") or "")
    out["Subject"] = out["subject"]
    to_value = out.get("To") if "To" in out else out.get("to")
    out["To"] = _to_text(to_value)
    if "to" not in out:
        out["to"] = out["To"]
    from_value = out.get("From") if "From" in out else out.get("from")
    out["From"] = _to_text(from_value)
    if "from" not in out:
        out["from"] = out["From"]
    return out


def _body_of(msg: Dict[str, Any]) -> str:
    return _to_text(msg.get("Text") or msg.get("text") or msg.get("body") or msg.get("Body") or "")


def get_message_body(token: str, message_id: str) -> str:
    for msg in _messages():
        if (msg.get("ID") or msg.get("id")) == message_id:
            return _body_of(msg)
    return ""


def get_message_subject(token: str, message_id: str) -> str:
    for msg in _messages():
        if (msg.get("ID") or msg.get("id")) == message_id:
            return _to_text(msg.get("Subject") or msg.get("subject") or "")
    return ""


def _matches(actual: str, expected: Union[str, List[str]], all_terms: bool) -> bool:
    actual_lower = actual.strip().lower()
    if isinstance(expected, str):
        expected = [expected]
    hits = [str(t).strip().lower() in actual_lower for t in expected]
    return all(hits) if all_terms else any(hits)


def search_messages(
    token: str,
    to_address: Optional[str] = None,
    from_address: Optional[str] = None,
    subject_contains: Optional[Union[str, List[str]]] = None,
    body_contains: Optional[Union[str, List[str]]] = None,
    limit: int = 50,
    include_body: bool = False,
) -> List[Dict[str, Any]]:
    """Search messages with upstream filtering semantics (see module docstring)."""
    if to_address is None and from_address is None and subject_contains is None and body_contains is None:
        return [_normalize_message_shape(m) for m in _messages()][:limit]

    subject_terms: List[str] = []
    if subject_contains:
        subject_terms = [subject_contains] if isinstance(subject_contains, str) else list(subject_contains)
    body_terms: List[str] = []
    if body_contains:
        body_terms = [body_contains] if isinstance(body_contains, str) else list(body_contains)

    out: List[Dict[str, Any]] = []
    for raw in _messages():
        msg = _normalize_message_shape(raw)
        if to_address and to_address.strip().lower() not in msg["To"].lower():
            continue
        if from_address and from_address.strip().lower() not in msg["From"].lower():
            continue
        if subject_terms and not _matches(msg["subject"], subject_terms, all_terms=True):
            continue
        body = _body_of(msg)
        if body_terms:
            body_norm = normalize_amounts(body.lower())
            if not all(normalize_amounts(str(t).lower()) in body_norm for t in body_terms):
                continue
        if include_body or body_terms:
            msg["body"] = body
        out.append(msg)
        if len(out) >= limit:
            break
    return out


def search_emails_as(
    email: str,
    password: str,
    *,
    to_address: Optional[str] = None,
    from_address: Optional[str] = None,
    subject_contains: Optional[Union[str, List[str]]] = None,
    body_contains: Optional[Union[str, List[str]]] = None,
    limit: int = 50,
    include_body: bool = True,
) -> List[Dict[str, Any]]:
    """Convenience wrapper kept for surface parity; login is a no-op (state store
    does not model passwords)."""
    return search_messages(
        token=email,
        to_address=to_address,
        from_address=from_address,
        subject_contains=subject_contains,
        body_contains=body_contains,
        limit=limit,
        include_body=include_body,
    )
