"""Pure functions that map raw Apollo API payloads to the plain dicts the
rest of the app works with. Kept separate from apollo_client.py so parsing
can be unit-tested with fixture JSON and no network access at all.

Every field defaults to None (never a guessed value) when Apollo doesn't
provide it — callers (Research/Contact agents) are responsible for turning
None into the literal string "UNKNOWN" at the point data is presented,
per the "never invent data" requirement.
"""
from __future__ import annotations

from typing import Any


def parse_organization(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": raw.get("name"),
        "domain": raw.get("primary_domain") or raw.get("domain"),
        "website_url": raw.get("website_url"),
        "industry": raw.get("industry"),
        "keywords": raw.get("keywords") or [],
        "employee_count": raw.get("estimated_num_employees"),
        "city": raw.get("city"),
        "state": raw.get("state"),
        "country": raw.get("country"),
        "apollo_org_id": raw.get("id"),
        "description": raw.get("short_description"),
        "founded_year": raw.get("founded_year"),
        "linkedin_url": raw.get("linkedin_url"),
        "phone": raw.get("primary_phone", {}).get("number") if isinstance(raw.get("primary_phone"), dict) else raw.get("phone"),
        "raw": raw,
    }


def parse_person(raw: dict[str, Any]) -> dict[str, Any]:
    org = raw.get("organization") or {}
    full_name = raw.get("name") or " ".join(
        p for p in [raw.get("first_name"), raw.get("last_name")] if p
    ).strip() or None
    phone = None
    phone_numbers = raw.get("phone_numbers") or []
    if phone_numbers and isinstance(phone_numbers, list):
        first = phone_numbers[0]
        phone = first.get("sanitized_number") or first.get("raw_number") if isinstance(first, dict) else None
    return {
        "full_name": full_name,
        "title": raw.get("title"),
        "email": raw.get("email"),
        "email_status": raw.get("email_status"),
        "phone": phone,
        "linkedin_url": raw.get("linkedin_url"),
        "apollo_person_id": raw.get("id"),
        "organization_name": org.get("name") if isinstance(org, dict) else None,
        "organization_domain": org.get("primary_domain") if isinstance(org, dict) else None,
        "raw": raw,
    }
