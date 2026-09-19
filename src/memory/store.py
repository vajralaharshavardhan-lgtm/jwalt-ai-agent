"""Single entry point into the memory layer: one connection, all repositories,
plus the duplicate checker and a convenience method for the most common
write path (create-or-reuse a company, with dedupe applied first).
"""
from __future__ import annotations

import sqlite3

from .db import connect_and_init
from .dedupe import DuplicateChecker
from .models import Company
from .repositories import (
    CompanyRepository,
    ContactRepository,
    LeadRepository,
    OutreachRepository,
    RunLogRepository,
)


class Store:
    def __init__(self, db_path: str):
        self.conn: sqlite3.Connection = connect_and_init(db_path)
        self.companies = CompanyRepository(self.conn)
        self.contacts = ContactRepository(self.conn)
        self.leads = LeadRepository(self.conn)
        self.outreach = OutreachRepository(self.conn)
        self.run_logs = RunLogRepository(self.conn)
        self.dedupe = DuplicateChecker(self.companies, self.contacts)

    def get_or_create_company(
        self, *, name: str, domain: str | None = None, **fields
    ) -> tuple[Company, bool]:
        """Returns (company, created). If a duplicate exists, updates it with
        any newly-provided non-empty fields instead of creating a new row.
        """
        existing = self.dedupe.find_existing_company(domain=domain, name=name)
        if existing:
            updated = self.companies.update(existing.id, name=name, domain=domain, **fields)
            return updated, False
        created = self.companies.create(name=name, domain=domain, **fields)
        return created, True

    def close(self) -> None:
        self.conn.close()
