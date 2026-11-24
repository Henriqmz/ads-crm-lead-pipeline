from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedLead:
    lead_id: str
    form_id: str
    campaign_name: str
    full_name: str
    email: str
    phone_e164: str
    company: str
    custom_answers: dict[str, str]


def normalize_phone_br(raw_phone: str) -> str:
    """Normalizes Brazilian or international phone numbers into E.164 format."""
    if not raw_phone:
        return ""
    cleaned = raw_phone.strip()
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return ""
    if cleaned.startswith("+"):
        return f"+{digits}"
    if len(digits) in (10, 11):
        return f"+55{digits}"
    if len(digits) in (12, 13) and digits.startswith("55"):
        return f"+{digits}"
    return f"+{digits}" if len(digits) > 8 else cleaned


def normalize_lead(raw: dict[str, Any]) -> NormalizedLead:
    """Converts a raw Ads API lead payload into a clean NormalizedLead structure."""
    answers = {
        str(k).strip(): str(v).strip()
        for k, v in (raw.get("answers") or {}).items()
        if v is not None and str(v).strip()
    }
    first = str(raw.get("first_name", "")).strip()
    last = str(raw.get("last_name", "")).strip()
    full_name = str(raw.get("full_name", "")).strip() or f"{first} {last}".strip() or "Lead Sem Nome"
    return NormalizedLead(
        lead_id=str(raw["id"]),
        form_id=str(raw.get("form_id", "")),
        campaign_name=str(raw.get("campaign_name", "Campanha Geral")).strip(),
        full_name=full_name,
        email=str(raw.get("email", "")).strip().lower(),
        phone_e164=normalize_phone_br(str(raw.get("phone", ""))),
        company=str(raw.get("company", "")).strip(),
        custom_answers=answers,
    )
