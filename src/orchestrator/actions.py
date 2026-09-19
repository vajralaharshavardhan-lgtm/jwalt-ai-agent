"""Canonical action names written to run_logs. Reporting (src/reporting/report.py)
tallies by these names, so every tool/handler that writes a log entry should
use a constant from here rather than a free-form string.
"""

RESEARCH_COMPANIES = "research_companies"
DUPLICATE_DETECTED = "duplicate_detected"
COMPANY_STORED = "company_stored"
CONTACT_FOUND = "contact_found"
NO_CONTACT_FOUND = "no_contact_found"
LEAD_QUALIFIED = "lead_qualified"
DRAFT_CREATED = "draft_created"
APPROVAL_REQUESTED = "approval_requested"
APPROVAL_DECISION = "approval_decision"
REPORT_GENERATED = "report_generated"
ORCHESTRATOR_STEP = "orchestrator_step"
ORCHESTRATOR_FINISHED = "orchestrator_finished"
