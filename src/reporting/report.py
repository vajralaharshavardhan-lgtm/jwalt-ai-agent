"""Reporting: builds a daily/run summary from the run_logs audit trail plus
current lead/outreach state. Reads only -- reporting never mutates data.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.memory.store import Store
from src.orchestrator import actions as A


@dataclass
class RunReport:
    run_id: str
    leads_researched: int = 0
    duplicates_skipped: int = 0
    contacts_found: int = 0
    qualified_by_classification: dict[str, int] = field(default_factory=dict)
    drafts_created: int = 0
    approvals_approved: int = 0
    approvals_rejected: int = 0
    approvals_edited: int = 0
    actions_awaiting_approval: int = 0
    errors: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            f"J-WALT BD Agent -- Run Report ({self.run_id})",
            "=" * 60,
            f"Companies researched:      {self.leads_researched}",
            f"Duplicates skipped:        {self.duplicates_skipped}",
            f"Contacts found:            {self.contacts_found}",
            "",
            "Qualification breakdown:",
        ]
        for classification in ("HOT", "WARM", "COLD", "UNQUALIFIED"):
            lines.append(f"  {classification:<12} {self.qualified_by_classification.get(classification, 0)}")
        lines += [
            "",
            f"Outreach drafts created:   {self.drafts_created}",
            f"  Approved:                {self.approvals_approved}",
            f"  Rejected:                {self.approvals_rejected}",
            f"  Edited:                  {self.approvals_edited}",
            f"  Awaiting approval:       {self.actions_awaiting_approval}",
            "",
            f"Errors ({len(self.errors)}):",
        ]
        lines += [f"  - {e}" for e in self.errors] if self.errors else ["  (none)"]
        return "\n".join(lines)


class ReportGenerator:
    def __init__(self, store: Store):
        self._store = store

    def generate(self, run_id: str) -> RunReport:
        entries = self._store.run_logs.list_for_run(run_id)
        report = RunReport(run_id=run_id)

        for entry in entries:
            if entry.action == A.RESEARCH_COMPANIES and entry.status == "SUCCESS":
                report.leads_researched += int(entry.output_summary or 0) if str(entry.output_summary).isdigit() else 0
            elif entry.action == A.DUPLICATE_DETECTED:
                report.duplicates_skipped += 1
            elif entry.action == A.CONTACT_FOUND:
                report.contacts_found += 1
            elif entry.action == A.LEAD_QUALIFIED and entry.output_summary:
                report.qualified_by_classification[entry.output_summary] = (
                    report.qualified_by_classification.get(entry.output_summary, 0) + 1
                )
            elif entry.action == A.DRAFT_CREATED:
                report.drafts_created += 1
                report.actions_awaiting_approval += 1
            elif entry.action == A.APPROVAL_DECISION:
                report.actions_awaiting_approval = max(0, report.actions_awaiting_approval - 1)
                if entry.output_summary == "APPROVED":
                    report.approvals_approved += 1
                elif entry.output_summary == "REJECTED":
                    report.approvals_rejected += 1
                elif entry.output_summary == "EDITED":
                    report.approvals_edited += 1

            if entry.status == "ERROR":
                report.errors.append(f"[{entry.agent}/{entry.action}] {entry.error_message}")

        return report
