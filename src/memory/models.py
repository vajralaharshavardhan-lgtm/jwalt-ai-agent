"""Typed domain records returned by the repository layer.

These mirror the SQLite schema in db.py. Plain dataclasses on purpose (no
ORM) — the schema is small and stable enough that hand-written SQL in
repositories.py stays easy to audit, which matters for an agent that writes
data about real companies autonomously.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Company:
    id: int | None
    name: str
    normalized_name: str
    domain: str | None
    industry: str | None
    employee_count: str | None
    city: str | None
    country: str | None
    apollo_org_id: str | None
    source: str
    description: str | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Company":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class Contact:
    id: int | None
    company_id: int
    full_name: str
    title: str | None
    email: str | None
    email_status: str | None
    phone: str | None
    linkedin_url: str | None
    apollo_person_id: str | None
    source: str
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Contact":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class Lead:
    id: int | None
    company_id: int
    contact_id: int | None
    status: str
    classification: str | None
    score: int | None
    score_explanation: str | None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Lead":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class OutreachEvent:
    id: int | None
    lead_id: int
    contact_id: int | None
    event_type: str
    subject: str | None
    body: str | None
    personalization_evidence: str | None
    status: str
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "OutreachEvent":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class RunLogEntry:
    id: int | None
    run_id: str
    agent: str
    action: str
    input_summary: str | None
    output_summary: str | None
    status: str
    error_message: str | None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RunLogEntry":
        return cls(**{k: row[k] for k in row.keys()})


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
