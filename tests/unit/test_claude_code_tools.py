import pytest

from src.agents.qualification_agent import QualificationAgent
from src.orchestrator.claude_code_tools import (
    cc_extract_evidence,
    cc_record_approval_decision,
    cc_request_approval,
    cc_submit_outreach_draft,
)
from src.orchestrator.context import OrchestratorContext

SCORING_CONFIG = {
    "fit_out_signal_keywords": ["new opening", "expansion", "new hotel"],
    "target_industries": [], "target_locations": [], "ideal_employee_ranges": [],
    "weights": {}, "thresholds": {"hot": 75, "warm": 50, "cold": 25},
}


@pytest.fixture()
def ctx(store):
    return OrchestratorContext(
        run_id="test-run", store=store, apollo_client=None, research_agent=None,
        qualification_agent=QualificationAgent(SCORING_CONFIG),
        contact_agent=None, outreach_agent=None, approval_gate=None,
    )


class TestCcExtractEvidence:
    def test_matches_real_keyword(self, ctx, monkeypatch):
        monkeypatch.setattr(
            "src.orchestrator.claude_code_tools.get_settings",
            lambda: type("S", (), {"raw_scoring": SCORING_CONFIG})(),
        )
        result = cc_extract_evidence(
            {"description": "Hotel group planning a new hotel in Dubai Marina.", "keywords": []}, ctx
        )
        assert result["evidence"] == ["new hotel"]

    def test_no_match_returns_unknown(self, ctx, monkeypatch):
        monkeypatch.setattr(
            "src.orchestrator.claude_code_tools.get_settings",
            lambda: type("S", (), {"raw_scoring": SCORING_CONFIG})(),
        )
        result = cc_extract_evidence({"description": "A boring logistics company.", "keywords": []}, ctx)
        assert result["evidence"] == ["UNKNOWN"]


class TestCcSubmitOutreachDraft:
    def test_creates_draft_for_lead_with_contact(self, ctx):
        company = ctx.store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        contact = ctx.store.contacts.create(company_id=company.id, full_name="John Smith", source="test")
        lead = ctx.store.leads.create(company_id=company.id, contact_id=contact.id, classification="HOT", score=90)

        result = cc_submit_outreach_draft(
            {"lead_id": lead.id, "subject": "Hi", "body": "...", "personalization_evidence": ["company_name: ABC Hotels"]},
            ctx,
        )
        assert result["subject"] == "Hi"
        event = ctx.store.outreach.get(result["outreach_event_id"])
        assert event.status == "PENDING_APPROVAL"
        assert event.contact_id == contact.id

    def test_raises_for_lead_without_contact(self, ctx):
        company = ctx.store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        lead = ctx.store.leads.create(company_id=company.id)
        with pytest.raises(ValueError, match="no contact"):
            cc_submit_outreach_draft({"lead_id": lead.id, "subject": "Hi", "body": "..."}, ctx)

    def test_raises_for_missing_lead(self, ctx):
        with pytest.raises(ValueError, match="No lead"):
            cc_submit_outreach_draft({"lead_id": 999, "subject": "Hi", "body": "..."}, ctx)


class TestCcApprovalFlow:
    def _make_draft_event(self, ctx):
        company = ctx.store.companies.create(name="ABC Hotels", domain="abchotels.com", source="test")
        contact = ctx.store.contacts.create(company_id=company.id, full_name="John Smith", source="test")
        lead = ctx.store.leads.create(company_id=company.id, contact_id=contact.id)
        return ctx.store.outreach.create(lead_id=lead.id, contact_id=contact.id, event_type="DRAFT_CREATED", subject="Hi", body="...")

    def test_request_approval_logs_and_returns_content(self, ctx):
        event = self._make_draft_event(ctx)
        result = cc_request_approval({"outreach_event_id": event.id}, ctx)
        assert result["subject"] == "Hi"
        logs = ctx.store.run_logs.list_for_run("test-run")
        assert any(l.action == "approval_requested" for l in logs)

    def test_request_approval_raises_for_missing_event(self, ctx):
        with pytest.raises(ValueError, match="No outreach event"):
            cc_request_approval({"outreach_event_id": 999}, ctx)

    def test_record_decision_updates_status_and_logs(self, ctx):
        event = self._make_draft_event(ctx)
        result = cc_record_approval_decision({"outreach_event_id": event.id, "decision": "APPROVED"}, ctx)
        assert result["decision"] == "APPROVED"
        assert ctx.store.outreach.get(event.id).status == "APPROVED"
        logs = ctx.store.run_logs.list_for_run("test-run")
        assert any(l.action == "approval_decision" and l.output_summary == "APPROVED" for l in logs)

    def test_record_decision_rejects_invalid_decision(self, ctx):
        event = self._make_draft_event(ctx)
        with pytest.raises(ValueError, match="APPROVED"):
            cc_record_approval_decision({"outreach_event_id": event.id, "decision": "MAYBE"}, ctx)
