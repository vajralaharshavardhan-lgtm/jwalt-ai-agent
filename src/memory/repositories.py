"""CRUD repositories over the SQLite schema. Thin, explicit SQL — no ORM.

Every write method returns the persisted record (with its assigned id) so
callers never have to guess whether a row exists.
"""
from __future__ import annotations

import sqlite3

from .dedupe import normalize_company_name, normalize_domain, normalize_phone
from .models import Company, Contact, Lead, OutreachEvent, RunLogEntry, utc_now_iso


class CompanyRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(
        self,
        *,
        name: str,
        domain: str | None = None,
        industry: str | None = None,
        employee_count: str | None = None,
        city: str | None = None,
        country: str | None = None,
        apollo_org_id: str | None = None,
        source: str = "unknown",
        description: str | None = None,
    ) -> Company:
        now = utc_now_iso()
        norm_domain = normalize_domain(domain)
        norm_name = normalize_company_name(name)
        cur = self._conn.execute(
            """INSERT INTO companies
               (name, normalized_name, domain, industry, employee_count, city,
                country, apollo_org_id, source, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, norm_name, norm_domain, industry, employee_count, city,
             country, apollo_org_id, source, description, now, now),
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def get(self, company_id: int) -> Company | None:
        row = self._conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return Company.from_row(row) if row else None

    def get_by_domain(self, normalized_domain: str) -> Company | None:
        row = self._conn.execute(
            "SELECT * FROM companies WHERE domain = ? LIMIT 1", (normalized_domain,)
        ).fetchone()
        return Company.from_row(row) if row else None

    def get_by_normalized_name(self, normalized_name: str) -> Company | None:
        row = self._conn.execute(
            "SELECT * FROM companies WHERE normalized_name = ? LIMIT 1", (normalized_name,)
        ).fetchone()
        return Company.from_row(row) if row else None

    def update(self, company_id: int, **fields) -> Company | None:
        """Only overwrites fields that are provided AND non-empty, so enrichment
        never clobbers a previously-known value with a blank one.
        """
        allowed = {"name", "domain", "industry", "employee_count", "city",
                   "country", "apollo_org_id", "description"}
        updates = {k: v for k, v in fields.items() if k in allowed and v}
        if not updates:
            return self.get(company_id)
        if "domain" in updates:
            updates["domain"] = normalize_domain(updates["domain"])
        if "name" in updates:
            updates["normalized_name"] = normalize_company_name(updates["name"])
        updates["updated_at"] = utc_now_iso()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self._conn.execute(
            f"UPDATE companies SET {set_clause} WHERE id = ?",
            (*updates.values(), company_id),
        )
        self._conn.commit()
        return self.get(company_id)

    def search(self, *, industry: str | None = None, city: str | None = None) -> list[Company]:
        query = "SELECT * FROM companies WHERE 1=1"
        params: list = []
        if industry:
            query += " AND industry LIKE ?"
            params.append(f"%{industry}%")
        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")
        rows = self._conn.execute(query, params).fetchall()
        return [Company.from_row(r) for r in rows]


class ContactRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(
        self,
        *,
        company_id: int,
        full_name: str,
        title: str | None = None,
        email: str | None = None,
        email_status: str | None = None,
        phone: str | None = None,
        linkedin_url: str | None = None,
        apollo_person_id: str | None = None,
        source: str = "unknown",
    ) -> Contact:
        now = utc_now_iso()
        norm_email = email.strip().lower() if email else None
        cur = self._conn.execute(
            """INSERT INTO contacts
               (company_id, full_name, title, email, email_status, phone,
                linkedin_url, apollo_person_id, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company_id, full_name, title, norm_email, email_status, phone,
             linkedin_url, apollo_person_id, source, now, now),
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def get(self, contact_id: int) -> Contact | None:
        row = self._conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        return Contact.from_row(row) if row else None

    def get_by_email(self, normalized_email: str) -> Contact | None:
        row = self._conn.execute(
            "SELECT * FROM contacts WHERE email = ? LIMIT 1", (normalized_email,)
        ).fetchone()
        return Contact.from_row(row) if row else None

    def get_by_phone(self, normalized_phone: str) -> Contact | None:
        rows = self._conn.execute("SELECT * FROM contacts WHERE phone IS NOT NULL").fetchall()
        for row in rows:
            if normalize_phone(row["phone"]) == normalized_phone:
                return Contact.from_row(row)
        return None

    def list_for_company(self, company_id: int) -> list[Contact]:
        rows = self._conn.execute(
            "SELECT * FROM contacts WHERE company_id = ?", (company_id,)
        ).fetchall()
        return [Contact.from_row(r) for r in rows]


class LeadRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(
        self,
        *,
        company_id: int,
        contact_id: int | None = None,
        status: str = "NEW",
        classification: str | None = None,
        score: int | None = None,
        score_explanation: str | None = None,
    ) -> Lead:
        now = utc_now_iso()
        cur = self._conn.execute(
            """INSERT INTO leads
               (company_id, contact_id, status, classification, score,
                score_explanation, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (company_id, contact_id, status, classification, score,
             score_explanation, now, now),
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def get(self, lead_id: int) -> Lead | None:
        row = self._conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return Lead.from_row(row) if row else None

    def get_for_company(self, company_id: int) -> Lead | None:
        row = self._conn.execute(
            "SELECT * FROM leads WHERE company_id = ? ORDER BY id DESC LIMIT 1", (company_id,)
        ).fetchone()
        return Lead.from_row(row) if row else None

    def update(self, lead_id: int, **fields) -> Lead | None:
        allowed = {"contact_id", "status", "classification", "score", "score_explanation"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get(lead_id)
        updates["updated_at"] = utc_now_iso()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self._conn.execute(
            f"UPDATE leads SET {set_clause} WHERE id = ?", (*updates.values(), lead_id)
        )
        self._conn.commit()
        return self.get(lead_id)

    def search(
        self,
        *,
        classification: str | None = None,
        status: str | None = None,
        min_score: int | None = None,
    ) -> list[Lead]:
        query = "SELECT * FROM leads WHERE 1=1"
        params: list = []
        if classification:
            query += " AND classification = ?"
            params.append(classification)
        if status:
            query += " AND status = ?"
            params.append(status)
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        rows = self._conn.execute(query, params).fetchall()
        return [Lead.from_row(r) for r in rows]


class OutreachRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(
        self,
        *,
        lead_id: int,
        contact_id: int | None,
        event_type: str,
        subject: str | None = None,
        body: str | None = None,
        personalization_evidence: str | None = None,
        status: str = "DRAFT",
    ) -> OutreachEvent:
        now = utc_now_iso()
        cur = self._conn.execute(
            """INSERT INTO outreach_events
               (lead_id, contact_id, event_type, subject, body,
                personalization_evidence, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (lead_id, contact_id, event_type, subject, body,
             personalization_evidence, status, now),
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def get(self, event_id: int) -> OutreachEvent | None:
        row = self._conn.execute(
            "SELECT * FROM outreach_events WHERE id = ?", (event_id,)
        ).fetchone()
        return OutreachEvent.from_row(row) if row else None

    def update_status(self, event_id: int, status: str) -> OutreachEvent | None:
        self._conn.execute(
            "UPDATE outreach_events SET status = ? WHERE id = ?", (status, event_id)
        )
        self._conn.commit()
        return self.get(event_id)

    def list_for_lead(self, lead_id: int) -> list[OutreachEvent]:
        rows = self._conn.execute(
            "SELECT * FROM outreach_events WHERE lead_id = ? ORDER BY id", (lead_id,)
        ).fetchall()
        return [OutreachEvent.from_row(r) for r in rows]

    def list_by_status(self, status: str) -> list[OutreachEvent]:
        rows = self._conn.execute(
            "SELECT * FROM outreach_events WHERE status = ?", (status,)
        ).fetchall()
        return [OutreachEvent.from_row(r) for r in rows]


class RunLogRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def log(
        self,
        *,
        run_id: str,
        agent: str,
        action: str,
        status: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
        error_message: str | None = None,
    ) -> RunLogEntry:
        now = utc_now_iso()
        cur = self._conn.execute(
            """INSERT INTO run_logs
               (run_id, agent, action, input_summary, output_summary, status,
                error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, agent, action, input_summary, output_summary, status,
             error_message, now),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM run_logs WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return RunLogEntry.from_row(row)

    def list_for_run(self, run_id: str) -> list[RunLogEntry]:
        rows = self._conn.execute(
            "SELECT * FROM run_logs WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        return [RunLogEntry.from_row(r) for r in rows]

    def list_since(self, iso_timestamp: str) -> list[RunLogEntry]:
        rows = self._conn.execute(
            "SELECT * FROM run_logs WHERE created_at >= ? ORDER BY id", (iso_timestamp,)
        ).fetchall()
        return [RunLogEntry.from_row(r) for r in rows]
