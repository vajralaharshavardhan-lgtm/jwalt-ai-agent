"""Duplicate-detection helpers: name/domain normalization and lookups.

Order of truth, most reliable first (Phase 6 of the spec):
  1. domain (exact, normalized)
  2. normalized company name (fuzzy-ish: strips legal suffixes/punctuation)
  3. contact email (exact)
  4. contact phone (normalized to digits only)
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_LEGAL_SUFFIXES = [
    "llc", "l.l.c", "fze", "fzc", "fzco", "dmcc", "ltd", "ltd.", "limited",
    "llp", "plc", "inc", "inc.", "incorporated", "corp", "corp.",
    "corporation", "co", "co.", "company", "group", "holding", "holdings",
    "trading", "general trading", "est", "establishment",
]

_SUFFIX_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in sorted(_LEGAL_SUFFIXES, key=len, reverse=True)) + r")\b\.?",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str:
    """Lowercase, strip legal suffixes and punctuation, collapse whitespace.

    e.g. "ABC Hotels Group LLC" and "abc hotels" both normalize to "abc hotels".
    """
    if not name:
        return ""
    n = name.lower()
    n = _SUFFIX_PATTERN.sub("", n)
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def normalize_domain(domain_or_url: str | None) -> str | None:
    """Extract a bare, lowercase, www-stripped domain from a URL or raw domain."""
    if not domain_or_url:
        return None
    value = domain_or_url.strip().lower()
    if "://" not in value:
        value = f"//{value}"
    netloc = urlparse(value).netloc or urlparse(value).path
    netloc = netloc.split("/")[0].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None


def normalize_phone(phone: str | None) -> str | None:
    """Digits only, with a leading '00' international-dialing prefix collapsed
    the same way '+' already is (both mean "international"), so '+971...'
    and '00971...' compare as equal. No libphonenumber dependency in the
    MVP -- this is a straightforward equality check, not full E.164 parsing.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00"):
        digits = digits[2:]
    return digits or None


class DuplicateChecker:
    """Wraps repository lookups in the priority order the spec requires."""

    def __init__(self, companies_repo, contacts_repo):
        self._companies = companies_repo
        self._contacts = contacts_repo

    def find_existing_company(self, *, domain: str | None, name: str):
        norm_domain = normalize_domain(domain)
        if norm_domain:
            existing = self._companies.get_by_domain(norm_domain)
            if existing:
                return existing
        norm_name = normalize_company_name(name)
        if norm_name:
            existing = self._companies.get_by_normalized_name(norm_name)
            if existing:
                return existing
        return None

    def find_existing_contact(self, *, email: str | None, phone: str | None):
        if email:
            existing = self._contacts.get_by_email(email.strip().lower())
            if existing:
                return existing
        norm_phone = normalize_phone(phone)
        if norm_phone:
            existing = self._contacts.get_by_phone(norm_phone)
            if existing:
                return existing
        return None
